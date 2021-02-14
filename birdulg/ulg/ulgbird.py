#!/usr/bin/env python
#coding:utf-8
#
# ULG - Universal Looking Glass
# (C) 2012 CZ.NIC, z.s.p.o.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# Imports
import os
import sys
import socket
import re
from subprocess import STDOUT
import hashlib
import subprocess
import defaults
import commands
import ulgmodel
import ulggraph
import pexpect


IPV46_SUBNET_REGEXP = '^[0-9a-fA-F:\.]+(/[0-9]{1,2}){0,1}$'
RTNAME_REGEXP = '^[a-zA-Z0-9]+$'
STRING_SYMBOL_ROUTING_TABLE = 'routing table'

STRING_EXPECT_SSH_NEWKEY='Are you sure you want to continue connecting'
STRING_EXPECT_PASSWORD='(P|p)assword:'
STRING_EXPECT_SHELL_PROMPT_REGEXP = '\n[a-zA-Z0-9\._-]+>'
STRING_EXPECT_REPLY_START = 'BIRD\s+[^\s]+\s+ready\.'
STRING_LOGOUT_COMMAND = 'exit'

BIRD_SOCK_HEADER_REGEXP='^([0-9]+)[-\s](.+)$'
BIRD_SOCK_REPLY_END_REGEXP='^([0-9]+)\s*(\s.*)?$'

BIRD_CONSOLE_PROMPT_REGEXP='[^>]+>\s*'


BIRD_SHOW_PROTO_LINE_REGEXP='^\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)(\s+([^\s].+)){0,1}\s*$'
BIRD_SHOW_PROTO_HEADER_REGEXP='^\s*(name)\s+(proto)\s+(table)\s+(state)\s+(since)\s+(info)\s*$'

BIRD_RT_LINE_REGEXP = '^([^\s]+)\s+via\s+([^\s]+)\s+on\s+([^\s]+)\s+(\[[^\]]+\])\s+(\*?)\s*([^\s]+)\s+([^\s]+)'
BIRD_ASFIELD_REGEXP = '^\s*\[AS([0-9]+)(i|\?)\]\s*$'

BIRD_SHOW_SYMBOLS_LINE_REGEXP = '^([^\s]+)\s+(.+)\s*'

BIRD_GRAPH_SH_ROUTE_ALL = "Graph show route table <RT> for <IP subnet>"

bird_sock_header_regexp = re.compile(BIRD_SOCK_HEADER_REGEXP)
bird_sock_reply_end_regexp = re.compile(BIRD_SOCK_REPLY_END_REGEXP)
bird_rt_line_regexp = re.compile(BIRD_RT_LINE_REGEXP)
bird_asfield_regexp = re.compile(BIRD_ASFIELD_REGEXP)
bird_show_symbols_line_regexp = re.compile(BIRD_SHOW_SYMBOLS_LINE_REGEXP)
bird_show_proto_line_regexp = re.compile(BIRD_SHOW_PROTO_LINE_REGEXP)

BIRD_SH_ROUTE_ALL_ASES_REGEXP = "^(\s*BGP\.as_path:\s+)([0-9\s]+)\s*$"
bird_sh_route_all_ases_regexp = re.compile(BIRD_SH_ROUTE_ALL_ASES_REGEXP)

BIRD_SH_ROUTE_ALL_NEXTHOP_REGEXP = ".*\s+via\s+([0-9a-fA-F:\.]+)\s+on\s+[^\s]+\s+\[([^\s]+)\s+.*"
bird_sh_route_all_nexthop_regexp = re.compile(BIRD_SH_ROUTE_ALL_NEXTHOP_REGEXP)

BIRD_SH_ROUTE_ALL_USED_REGEXP = ".*\]\s+\*\s+\(.*"
bird_sh_route_all_used_regexp = re.compile(BIRD_SH_ROUTE_ALL_USED_REGEXP)




def bird_parse_sh_route_all(text,prependas):
    def split_ases(ases):
		return str.split(ases)

    DEFAULT_PARAMS = {'recuse':False, 'reconly':False, 'aggr':None}

    res = []
    params = dict(DEFAULT_PARAMS)
    for l in str.splitlines(text):
        m = bird_sh_route_all_nexthop_regexp.match(l)
        if(m):
            params['peer'] = m.group(2)
            if(bird_sh_route_all_used_regexp.match(l)):
                params['recuse'] = True

        m = bird_sh_route_all_ases_regexp.match(l)
        if(m):
            ases = [ulgmodel.annotateAS("AS"+str(asn)) for asn in [prependas] + split_ases(m.group(2))]
            res.append((ases,params))
            params = dict(DEFAULT_PARAMS)
            continue

    return res

def bird_reduce_paths(paths):
    def assign_value(path):
        if(path[1]['recuse']):
            return 1
        elif(path[1]['reconly']):
            return 100
        else:
            return 10

    return sorted(paths,key=assign_value)

def parseBirdShowProtocols(text):
    def parseShowProtocolsLine(line):
        m = bird_show_proto_line_regexp.match(line)
        if(m):
            res = list(m.groups()[0:5])
            if(m.group(6)):
                res.append(m.group(6))

            return res
        else:
#            skip silently the bgp log
#            ulgmodel.log("WARN: bird.parseShowProtocolsLine failed to match line: "+line)
            return None


    header = []
    table = []

    for l in str.splitlines(text):
        if(re.match('^\s*$',l)):
            continue
        
        hm = re.match(BIRD_SHOW_PROTO_HEADER_REGEXP,l)
        if(hm):
            header = hm.groups()
        else:
            pl = parseShowProtocolsLine(l)
            if(pl):
                table.append(pl)
#            else:
#                ulgmodel.log("ulgbird.parseBirdShowProtocols skipping unparsable line: "+l)

    return (header,table,len(table))

# classes

class BirdShowProtocolsCommand(ulgmodel.TextCommand):
    COMMAND_TEXT = 'show protocols'

    def __init__(self,name=None,show_proto_all_command=None,proto_filter=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[],name=name)
        self.show_proto_all_command = show_proto_all_command
        self.fltr = proto_filter

    def _getPeerURL(self,decorator_helper,router,peer_id):
        if decorator_helper and self.show_proto_all_command:
            return decorator_helper.getRuncommandURL({'routerid':str(decorator_helper.getRouterID(router)),
                                                      'commandid':str(decorator_helper.getCommandID(router,self.show_proto_all_command)),
                                                      'param0':peer_id})
        else:
            return None

    def _getPeerTableCell(self,decorator_helper,router,peer_id):
        url = self._getPeerURL(decorator_helper,router,peer_id)
        if(url):
            return decorator_helper.ahref(url,peer_id)
        else:
            return peer_id

    def _decorateTableLine(self,table_line,router,decorator_helper):
        def _getTableLineColor(state):
            if(state == 'up'):
                return ulgmodel.TableDecorator.GREEN
            elif(state == 'start'):
                return ulgmodel.TableDecorator.YELLOW
            else:
                return ulgmodel.TableDecorator.RED

        color = _getTableLineColor(table_line[3])
        tl = [(self._getPeerTableCell(decorator_helper,router,table_line[0]),color),
              (table_line[1],color),
              (table_line[2],color),
              (table_line[3],color),
              (table_line[4],color),
              ]
        if(len(table_line)>5):
            tl.append((table_line[5],color))

        return tl


    def decorateResult(self,session,decorator_helper=None):
        if(not session):
            raise Exception("Can not decorate result without valid session.")

	if(session.getResult() == None):
            return (decorator_helper.pre(defaults.STRING_EMPTY), 1)

        if((not session.getRouter()) or (not decorator_helper)):
            return "<pre>\n%s\n</pre>" % session.getResult()
        else:
            pr = parseBirdShowProtocols(session.getResult())
            table_header = pr[0]
            table = []

            for tl in pr[1][session.getRange():session.getRange()+defaults.range_step]:
                # skip when there is a filter and it does not match the protocol type
                if(self.fltr) and (not re.match(self.fltr,tl[1])):
                    continue
                table.append(self._decorateTableLine(tl,session.getRouter(),decorator_helper))

            return (ulgmodel.TableDecorator(table,table_header).decorate(),pr[2])


class AbstractBGPPeerSelectCommand(ulgmodel.TextCommand):
    """ Abstract class for all BIRD BGP peer-specific commands """

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[router.getBGPPeerSelect()],name=name)


class BirdShowProtocolsAllCommand(AbstractBGPPeerSelectCommand):
    COMMAND_TEXT = 'show protocols all %s'


class BirdPingCommand(AbstractBGPPeerSelectCommand):
  
    COMMAND_TEXT = '/bin/ping  %s   -I enp31s0 -c 4 '
    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[ulgmodel.TextParameter(pattern=IPV46_SUBNET_REGEXP,name=defaults.STRING_IPSUBNET)],name="Ping")




class BirdTracerouteCommand(AbstractBGPPeerSelectCommand):
  
    COMMAND_TEXT = 'sudo traceroute %s -4 -n -w 2 -i enp31s0'
    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[ulgmodel.TextParameter(pattern=IPV46_SUBNET_REGEXP,name=defaults.STRING_IPSUBNET)],name="Traceroute")



class AbstractRouteTableCommand(ulgmodel.TextCommand):

    def _decorateOriginAS(self,asfield,decorator_helper):
        # expected input is "[AS28171i]"
        m = bird_asfield_regexp.match(asfield)
        if(m):
            return '['+decorator_helper.decorateASN(m.group(1))+m.group(2)+']'
        else:
            return asfield

    def _genTable(self,table_lines,decorator_helper,router):
        def matchBIRDBGPRTLine(line):
            m = bird_rt_line_regexp.match(line)
            if(m):
                return m.groups()
            else:
                ulgmodel.debug("BirdShowRouteProtocolCommand: Can not parse line: "+line)
                return None

        result = []
        for tl in table_lines:
            ml=matchBIRDBGPRTLine(tl)
            if(ml):
                # generate table content
                result.append([
                        (decorator_helper.decoratePrefix(ml[0]),),
                        (ml[1],),
                        (ml[2],),
                        (ml[3],),
                        (ml[4],),
                        (ml[5],),
                        (self._decorateOriginAS(ml[6],decorator_helper),),
                        ])
        return result


    def decorateResult(self,session,decorator_helper=None):
        if(not session):
            raise Exception("Can not decorate result without valid session.")

	if(session.getResult() == None):
            return (decorator_helper.pre(defaults.STRING_EMPTY), 1)

        if((not session.getRouter()) or (not decorator_helper)):
            return "<pre>\n%s\n</pre>" % session.getResult()

        table=[]
        table_header=['Prefix',
                      'Next-hop',
                      'Interface',
                      'Since',
                      'Status',
                      'Metric',
                      'Info',]

        lines = str.splitlines(session.getResult())
        result_len = len(lines)
        lines = lines[session.getRange():session.getRange()+defaults.range_step]
        table = self._genTable(lines,decorator_helper,session.getRouter())

        return (ulgmodel.TableDecorator(table,table_header).decorate(),result_len)




class BirdShowRouteExportCommand(AbstractBGPPeerSelectCommand,AbstractRouteTableCommand):
    COMMAND_TEXT = 'show route export %s'



class BirdShowRouteCommand(AbstractRouteTableCommand):
    COMMAND_TEXT = 'show route table %s for %s'

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[
                router.getRoutingTableSelect(),
                ulgmodel.TextParameter(pattern=IPV46_SUBNET_REGEXP,name=defaults.STRING_IPSUBNET),
                ],name=name)


class BirdShowRouteProtocolCommand(BirdShowRouteCommand):
    COMMAND_TEXT = 'show route table %s protocol %s'

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[router.getRoutingTableSelect(),router.getBGPPeerSelect()],name=name)



class BirdShowRouteAllCommand(ulgmodel.TextCommand):
    COMMAND_TEXT = 'show route table %s all for %s'

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[
                router.getRoutingTableSelect(),
                ulgmodel.TextParameter(pattern=IPV46_SUBNET_REGEXP,name=defaults.STRING_IPSUBNET),
                ],
                                      name=name)

    def decorateResult(self,session,decorator_helper=None):
        def decorateLine(l):			
            m = bird_sh_route_all_ases_regexp.match(l)
            if(m):
                r = m.group(1)
                ases = str.split(m.group(2))
                for asn in ases:
                    r = r + decorator_helper.decorateASN(asn,prefix='')
                    r = r + ' '
                return decorator_helper.annotateIPs(r)
            else:
                return decorator_helper.annotateIPs(l)

	if(session.getResult() == None):
            return (decorator_helper.pre(defaults.STRING_EMPTY), 1)

        s = str.splitlines(session.getResult())
        r=''
        for sl in s:
            r += decorateLine(sl) + "\n"
            
        return ("<pre>\n%s\n</pre>" % r, len(s))


class BirdGraphShowRouteAll(ulgmodel.TextCommand):
    COMMAND_TEXT = 'show route table %s all for %s'

    def __init__(self,router,name=BIRD_GRAPH_SH_ROUTE_ALL):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[
                router.getRoutingTableSelect(),
                ulgmodel.TextParameter(pattern=IPV46_SUBNET_REGEXP,name=defaults.STRING_IPSUBNET),
                ],
                                      name=name)

    def finishHook(self,session):
        session.setData(bird_parse_sh_route_all(session.getResult(),str(session.getRouter().getASN())))

    def decorateResult(self,session,decorator_helper=None):
        if(session.isFinished()):
            if(session.getData() != None) and (session.getData() != []):
                return (decorator_helper.img(decorator_helper.getSpecialContentURL(session.getSessionId()),defaults.STRING_BGP_GRAPH),1)
            else:
                return (decorator_helper.pre(defaults.STRING_BGP_GRAPH_ERROR), 1)
        else:
            return ('',0)

    def getSpecialContent(self,session,**params):
        paths = session.getData()
        print "Content-type: image/png\n"
        ulggraph.bgp_graph_gen(bird_reduce_paths(paths),start=session.getRouter().getName(),
			       end=session.getParameters()[1])

    def showRange(self):
        return False

class BirdRouter(ulgmodel.Router):
    """ Abstract class representing common base for BIRD router objects. """
    RESCAN_PEERS_COMMAND = 'show protocols'
    RESCAN_TABLES_COMMAND = 'show symbols'
    DEFAULT_PROTOCOL_FLTR = '^BGP.*$'

    def __init__(self):
        self.bgp_peers = None
        self.routing_tables = None
        self.bgp_peer_select = None
        self.rt_select = None

    def _getDefaultCommands(self):
        sh_proto_all = BirdShowProtocolsAllCommand(self)
        sh_proto_route = BirdShowRouteProtocolCommand(self)
        sh_proto_export = BirdShowRouteExportCommand(self)
        return [BirdShowProtocolsCommand(show_proto_all_command=sh_proto_all, proto_filter = self.proto_fltr),
                BirdShowRouteCommand(self),
                sh_proto_all,
                sh_proto_route,
                sh_proto_export,
                BirdShowRouteAllCommand(self),
                # BirdShowPingCommand(self)
                BirdGraphShowRouteAll(self),
                BirdPingCommand(self),
                BirdTracerouteCommand(self),
              
#                ulgmodel.TextCommand('show status'),
#                ulgmodel.TextCommand('show memory')
                ]

    def rescanPeers(self):
        res = self.runRawSyncCommand(self.RESCAN_PEERS_COMMAND)
        psp = parseBirdShowProtocols(res)

        peers = []
        for pspl in psp[1]:
            if(re.match(self.proto_fltr,pspl[1])):
                peers.append(pspl[0])

        self.bgp_peers = sorted(peers)

    def rescanRoutingTables(self):
        res = self.runRawSyncCommand(self.RESCAN_TABLES_COMMAND)

        tables = []
        for l in str.splitlines(res):
            m = bird_show_symbols_line_regexp.match(l)
            if(m and m.group(2).lstrip().rstrip() == STRING_SYMBOL_ROUTING_TABLE):
                tables.append(m.group(1))

        self.routing_tables = sorted(tables)

    def getBGPPeers(self):
        if(not self.bgp_peers):
            self.rescanPeers()

        return self.bgp_peers

    def getRoutingTables(self):
        if(not self.routing_tables):
            self.rescanRoutingTables()

        return self.routing_tables

    def initBGPPeerSelect(self,peers):
        rid = hashlib.md5(self.getName()).hexdigest()
        self.bgp_peer_select = ulgmodel.CommonSelectionParameter(rid+"bgp",[tuple((p,p,)) for p in peers],
                                                                  name=defaults.STRING_PEERID)

    def initRoutingTableSelect(self,rt):
        rid = hashlib.md5(self.getName()).hexdigest()
        self.rt_select = ulgmodel.CommonSelectionParameter(rid+"rt",[tuple((p,p,)) for p in rt],
                                                                  name=defaults.STRING_RTABLE)

    def getBGPPeerSelect(self):
        if(not self.bgp_peer_select):
            self.initBGPPeerSelect(self.getBGPPeers())

        return self.bgp_peer_select

    def getRoutingTableSelect(self):
        if(not self.rt_select):
            self.initRoutingTableSelect(self.getRoutingTables())

        return self.rt_select



class BirdRouterLocal(ulgmodel.LocalRouter,BirdRouter):
    def __init__(self,sock=defaults.default_bird_sock,commands=None,proto_fltr=None,asn='My ASN',name='localhost',acl=None):
        ulgmodel.LocalRouter.__init__(self,acl=acl)
        BirdRouter.__init__(self)

        self.sock = sock
        self.setName(name)
        self.setASN(asn)
        if(proto_fltr):
            self.proto_fltr = proto_fltr
        else:
            self.proto_fltr = self.DEFAULT_PROTOCOL_FLTR

        self.rescanPeers()
        self.rescanRoutingTables()

        # command autoconfiguration might run only after other parameters are set
        if(commands):
            self.setCommands(commands)
        else:
            self.setCommands(self._getDefaultCommands())


    def runRawCommand(self,command,outfile):
        def parseBirdSockLine(line):
            hm = bird_sock_header_regexp.match(line)
            if(hm):
                # first line of the reply
                return (int(hm.group(1)),hm.group(2))

            em = bird_sock_reply_end_regexp.match(line)
            if(em):
                # most likely the last line of the reply
                return (int(em.group(1)),None)

            if(line[0] == '+'):
                # ignore async reply
                return (None,None)

            if(line[0] == ' '):
                # return reply line as it is (remove padding)
                return (None,line[1:])

            raise Exception("Can not parse BIRD output line: "+line)

        def isBirdSockReplyEnd(code):
            if(code==None):
                return False

            if(code == 0):
                # end of reply
                return True
            elif(code == 13):
                # show status last line
                return True
            elif(code == 8001):
                # network not in table end
                return True
            elif(code >= 9000):
                # probably error
                return True
            else:
                return False

#        try:
        

        #记录具体命令到日志文件
        ulgmodel.debug("command_to_bird_c_is:"+command)

        if ("traceroute" in command or "/bin/ping" in command):

            status, os_result = commands.getstatusoutput(command)

            # 182.50.118.1
            # os_result=os.popen(command).read()
            outfile.write(command+"\n")
            outfile.write("______________________________________________________________\n")
            outfile.write(os_result)
            return os_result+"\n"



             


        # open socket to BIRD
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(defaults.default_bird_sock_timeout)
        s.connect(self.sock)

        # cretate FD for the socket
        sf=s.makefile()

        # wait for initial header
        l = sf.readline()



        

        # result = subprocess.run(['ls', '-l'], stdout=subprocess.PIPE)
        # send the command string
        sf.write(command+"\n")
        sf.flush()

        # read and capture lines until the output delimiter string is hit
        while(True):
            l = sf.readline()

            ulgmodel.debug("Raw line read: " + l)

            # process line according to rules take out from the C code
            lp = parseBirdSockLine(l)
            if(isBirdSockReplyEnd(lp[0])):
                # End of reply (0000 or similar code)
                ulgmodel.debug("End of reply. Code="+str(lp[0]))

                if(lp[1]):
                    ulgmodel.debug("Last read line after normalize: " + lp[1])
                    outfile.write(lp[1].rstrip()+"\n")
                break
            else:
                if(lp[1]):
                    ulgmodel.debug("Read line after normalize: " + lp[1])
                    outfile.write(lp[1].rstrip()+"\n")
                else:
                    ulgmodel.debug("Read line was empty after normalize.")

        # close the socket and return captured result
        s.close()

#        except socket.timeout as e:
#            # catch only timeout exception, while letting other exceptions pass
#            outfile.result(defaults.STRING_SOCKET_TIMEOUT)

    def getForkNeeded(self):
        return False


class BirdRouterRemote(ulgmodel.RemoteRouter,BirdRouter):
    PS_KEY_BGP = '-bgppeers'
    PS_KEY_RT = '-routetab'

    def __init__(self,host,user,password='',port=22,commands=None,proto_fltr=None,asn='My ASN',name=None,bin_birdc=None,bin_ssh=None,acl=None):
        ulgmodel.RemoteRouter.__init__(self,acl=acl)
        BirdRouter.__init__(self)

        self.setHost(host)
        self.setUser(user)
        self.setPassword(password)
        self.setPort(port)
        if(name):
            self.setName(name)
        else:
            self.setName(host)
        self.setASN(asn)
        if(proto_fltr):
            self.proto_fltr = proto_fltr
        else:
            self.proto_fltr = self.DEFAULT_PROTOCOL_FLTR
        if(bin_birdc):
            self.bin_birdc = bin_birdc
        else:
            self.bin_birdc = defaults.default_bin_birdc

        if(bin_ssh):
            self.bin_ssh = bin_ssh
        else:
            self.bin_ssh = defaults.bin_ssh

        if(defaults.rescan_on_display):
            self.rescanHook()
        else:
            self.loadPersistentInfo()

        # command autoconfiguration might run only after other parameters are set
        if(commands):
            self.setCommands(commands)
        else:
            self.setCommands(self._getDefaultCommands())


    def getForkNeeded(self):
        return True

    def runRawCommand(self,command,outfile):
        c = '/bin/bash -c \'echo "'+command+'" | '+self.bin_ssh+' -p'+str(self.getPort())+' '+str(self.getUser())+'@'+self.getHost()+' '+self.bin_birdc+'\''
        skiplines = 2
        s=pexpect.spawn(c,timeout=defaults.timeout)

#        s.logfile = open('/tmp/ulgbird.log', 'w')

        # handle ssh
        y=0
        p=0
        l=0
        capture=False
        while True:
            i=s.expect([STRING_EXPECT_SSH_NEWKEY,STRING_EXPECT_PASSWORD,STRING_EXPECT_REPLY_START,'\n',pexpect.EOF,pexpect.TIMEOUT])
            if(i==0):
                if(y>1):
                    raise Exception("pexpect session failed: Can not save SSH key.")

                s.sendline('yes')
                y+=1
            elif(i==1):
                if(p>1):
                    raise Exception("pexpect session failed: Password not accepted.")

                s.sendline(self.password)
                p+=1
            elif(i==2):
                capture=True
            elif(i==3):
                if(capture):
                    if(l>=skiplines):
                        outfile.write(re.sub(BIRD_CONSOLE_PROMPT_REGEXP,'',s.before))
                    l+=1
            elif(i==4): # EOF -> process output
                break
            elif(i==5):
                raise Exception("pexpect session timed out. last output: "+s.before)
            else:
                raise Exception("pexpect session failed: Unknown error. last output: "+s.before)


    def savePersistentInfo(self):
        key_bgp = self.getHost() + self.getName() + self.PS_KEY_BGP
        key_rt = self.getHost() + self.getName() + self.PS_KEY_RT

        
        ps = ulgmodel.loadPersistentStorage()
        ps.set(key_bgp,self.getBGPPeers())
        ps.set(key_rt,self.getRoutingTables())
        ps.save()
               
    def loadPersistentInfo(self):
        key_bgp = self.getHost() + self.getName() + self.PS_KEY_BGP
        key_rt = self.getHost() + self.getName() + self.PS_KEY_RT

        ps = ulgmodel.loadPersistentStorage()
        self.bgp_peers = ps.get(key_bgp)
        self.routing_tables = ps.get(key_rt)

        if(not self.getBGPPeers()) or (not self.getRoutingTables()):
            self.rescanHook()


    def rescanHook(self):
        self.rescanPeers()
        self.rescanRoutingTables()
        self.savePersistentInfo()
