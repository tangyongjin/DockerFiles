#!/usr/bin/env python
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
import pexpect
import re
import sys
import string
import hashlib

import defaults

import ulgmodel
import ulggraph

# module globals
STRING_EXPECT_SSH_NEWKEY='Are you sure you want to continue connecting'
STRING_EXPECT_PASSWORD='(P|p)assword:'
STRING_EXPECT_SHELL_PROMPT_REGEXP = '\n[a-zA-Z0-9\._-]+(>|#)'
BGP_IPV6_SUM_TABLE_SPLITLINE_REGEXP='^\s*[0-9a-fA-F:]+\s*$'
IPV46_ADDR_REGEXP = '^[0-9a-fA-F:\.]+$'

BGP_IPV6_TABLE_HEADER_REGEXP='^\s*(Neighbor)\s+(V)\s+(AS)\s+(MsgRcvd)\s+(MsgSent)\s+(TblVer)\s+(InQ)\s+(OutQ)\s+(Up/Down)\s+(State/PfxRcd)\s*$'
BGP_IPV46_TABLE_LINE_REGEXP='^\s*([0-9a-fA-F:\.]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([a-zA-Z0-9:]+)\s+([a-zA-Z0-9\(\)]+|[a-zA-Z0-9]+\s\(Admin\))\s*$'
#BGP_IPV6_TABLE_LINE_REGEXP='^\s*([0-9a-fA-F:]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([a-zA-Z0-9:]+)\s+([a-zA-Z0-9\(\)]+|[a-zA-Z0-9]+\s\(Admin\))\s*$'
BGP_IPV4_TABLE_HEADER_REGEXP='^\s*(Neighbor)\s+(V)\s+(AS)\s+(MsgRcvd)\s+(MsgSent)\s+(TblVer)\s+(InQ)\s+(OutQ)\s+(Up/Down)\s+(State/PfxRcd)\s*$'
#BGP_IPV4_TABLE_LINE_REGEXP='^\s*([0-9\.]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([a-zA-Z0-9:]+)\s+([a-zA-Z0-9\(\)]+|[a-zA-Z0-9]+\s\(Admin\))\s*$'

BGP_PREFIX_TABLE_HEADER='^(\s)\s+(Network)\s+(Next Hop)\s+(Metric)\s+(LocPrf)\s+(Weight)\s+(Path)\s*$'

RESCAN_BGP_IPv4_COMMAND='show bgp ipv4 unicast summary'
RESCAN_BGP_IPv6_COMMAND='show bgp ipv6 unicast summary'

MAC_ADDRESS_REGEXP = '^[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}$'

BGP_RED_STATES = ['Idle', 'Active', '(NoNeg)']
BGP_YELLOW_STATES = ['Idle (Admin)',]

REGEX_SH_BGP_UNI_ASLINE = '^(\s*)([0-9\s]+|Local)(|,.*)\s*$'
regex_sh_bgp_uni_asline = re.compile(REGEX_SH_BGP_UNI_ASLINE)

REGEX_SH_BGP_UNI_AGGR = '\s*\(aggregated by ([0-9]+) [0-9a-fA-F:\.]+\).*'
regex_sh_bgp_uni_aggr = re.compile(REGEX_SH_BGP_UNI_AGGR)

REGEX_SH_BGP_UNI_RECUSE = '\s*\(received & used\).*'
regex_sh_bgp_uni_recuse = re.compile(REGEX_SH_BGP_UNI_RECUSE)

REGEX_SH_BGP_UNI_RECONLY = '\s*\(received-only\).*'
regex_sh_bgp_uni_reconly = re.compile(REGEX_SH_BGP_UNI_RECONLY)

REGEX_SH_BGP_UNI_TABLE_START = '\s*(Advertised\s+to\s+update-groups|Not\s+advertised\s+to\s+any\s+peer).*'
regex_sh_bgp_uni_table_start = re.compile(REGEX_SH_BGP_UNI_TABLE_START)

REGEX_SH_BGP_UNI_PEERLINE = '\s*([0-9a-fA-F:\.]+)\s.*from\s.*'
regex_sh_bgp_uni_peerline = re.compile(REGEX_SH_BGP_UNI_PEERLINE)

REGEX_SH_BGP_UNI_ORIGLINE_BEST = '\s*Origin\s.*\sbest.*'
regex_sh_bgp_uni_origline_best = re.compile(REGEX_SH_BGP_UNI_ORIGLINE_BEST)

COMMAND_NAME_GRAPH4 = 'Graph - show bgp ipv4 unicast <IP subnet>'
COMMAND_NAME_GRAPH6 = 'Graph - show bgp ipv6 unicast <IP subnet>'

STRING_COMMAND_LOGOUT = 'logout'

def cisco_parse_sh_bgp_uni(lines,prependas):
	def split_ases(ases):
		if ases == 'Local':
			return []
		else:
			return str.split(ases)

	def get_info(info):
		res = {'recuse':False, 'reconly':False, 'aggr':None}

		for g in info.split(','):
#			if(regex_sh_bgp_uni_recuse.match(g)):
#				res['recuse'] = True
			if(regex_sh_bgp_uni_reconly.match(g)):
				res['reconly'] = True

			m = regex_sh_bgp_uni_aggr.match(g)
			if(m):
				res['aggr'] = m.group(1)

		return res

	paths = []
	table_prestarted = False
	table_started = False
	for l in str.splitlines(lines):
		if not table_started:
			if table_prestarted:
				# if prestarted and a line not containing only numbers of
				# update groups, start immediately
				if not re.match('^[0-9\s]+$',l):
					table_started = True

			# if not prestarted and match occures, wait for next line
			if(regex_sh_bgp_uni_table_start.match(l)):
				table_prestarted = True


		if table_started:
			m = regex_sh_bgp_uni_asline.match(l)
			if(m):
				ases = [ulgmodel.annotateAS("AS"+str(asn)) for asn in [prependas] + split_ases(m.group(2))]
				infotext = m.group(3)
				if(infotext):
					paths.append((ases,get_info(infotext)))
				else:
					paths.append((ases,{'recuse':False, 'reconly':False, 'aggr':None}))
				continue

			m = regex_sh_bgp_uni_peerline.match(l)
			if(m):
				paths[-1][1]['peer'] = m.group(1)
				continue

			m = regex_sh_bgp_uni_origline_best.match(l)
			if(m):
				paths[-1][1]['recuse'] = True

	return paths


def reduce_bgp_paths(paths):
	def has_valid(paths,onepath):
		for p in paths:
			if((onepath[0] == p[0]) and (not p[1]['reconly'])):
				return True
		return False

	def has_used(paths,onepath):
		for p in paths:
			if((onepath[0] == p[0]) and (p[1]['recuse'])):
				return True
		return False

	def assign_value(path):
		if(path[1]['recuse']):
			return 1
		elif(path[1]['reconly']):
			return 100
		else:
			return 10

	newpaths = []
	for p in paths:
		if((p[1]['reconly']) and has_valid(paths,p)):
			pass
		elif(not (p[1]['recuse']) and has_used(paths,p)):
			pass
		else:
			newpaths.append(p)
	return sorted(newpaths,key=assign_value)

def matchCiscoBGPLines(header,lines):
    # Match cisco lines formatted to be aligned to columns. Like:
    #    Network          Next Hop            Metric LocPrf Weight Path
    # *  79.170.248.0/21  91.210.16.6            300             0 20723 i
    # *>i91.199.207.0/24  217.31.48.123            0   1024      0 44672 i
    # 0  1                2                   3      4      5      6
    #
    #    Network          Next Hop            Metric LocPrf Weight Path
    # *>i2001:67C:278::/48
    #                     2001:1AB0:B0F4:FFFF::2
    #                                         0        1024      0 51278 i
    # *> 2001:1AB0::/32   ::                  0              32768 i
    # 0  1                2                   3      4      5      6
    #
    # First find boundaries, second section text (if it overflow next boundary
    # line wrap is expected) and then remove white spaces and return sections.
    #
    # ?1 hat happens when last element is line-wrapped? It looks like it does
    # not happen in my settings.

    def divideGroups(line,max_index_start=sys.maxint,table_line=False,first_group_length=3):
        # divide groups starting before max_index_start
        result = []

        # when parsing table_line (not the header and not the continuation line)
        # cut off first N charactes and use them as the first group (flags) when there is
        # some non-blank characters in the first two groups (therefore the line is the leading)
        if(table_line):
            if(re.match('[^\s]+',line[0:(first_group_length+2)])):
                result.append([0,first_group_length])
	        line = ' '*first_group_length + line[first_group_length:]
	else:
            # parsing header, add virtual Status group to the header
	    line = 'S'+line[1:]

        last_group = False
        for r in re.compile('[^\s]+').finditer(line):
            if(not last_group):
                result.append([r.start(),r.end()])

            if(r.start() >= max_index_start):
                last_group = True

        # shortcut for empty lines / no results
        if(len(result)==0):
            return None

        # add tail to last groups
        result[-1][1] = len(line)

	# in header force the first group to spann till the end of the next group
	if(not table_line):
            result[0][1] = result[1][0]-1

        return result


    def matchGroup(header_groups_indexes,line_group_indexes,last_element):
        ulgmodel.debug('matchGroup header_group_indexes='+str(header_groups_indexes)+' line_group_indexes='+str(line_group_indexes))

        if(len(header_groups_indexes) == 1):
            return 0

        # beginning of the second group is right of the beginning of the tested
        if((len(header_groups_indexes) > 1) and
           (header_groups_indexes[1][0] > line_group_indexes[0])):
            return 0

        # beginning of the last (and the only possible) group is left
        # the beginning of the tested
        if(header_groups_indexes[-1][0] <= line_group_indexes[0]):
            return (len(header_groups_indexes)-1)

        # linear algorithm !!!
        # rewrite to tree(?)
        for hgipos,hgi in enumerate(header_groups_indexes):

            if((hgipos >= 1) and
               (hgipos < (len(header_groups_indexes)-1)) and
               (header_groups_indexes[hgipos-1][1] <= line_group_indexes[0]) and
               (header_groups_indexes[hgipos+1][0] >= line_group_indexes[1])):
                return hgipos

            if((last_element) and
               (hgipos >= 1) and
               (hgi[0] <= line_group_indexes[0]) and
               (len(header_groups_indexes)-1 > hgipos) and
               (header_groups_indexes[hgipos+1][0] > line_group_indexes[0])):
                return hgipos

        return None


    def normalize(instr):
        return instr.strip()


    hgidxs = divideGroups(header)
    result = [[]]

    for l in lines:
        # divide groups (leave the last group in one part)
        # define boundary of the first group by the first letter of the second group beginning
        lgps = divideGroups(l,hgidxs[-1][0],True,hgidxs[1][0]-1)
        if(lgps==None):
            continue

        for lgpidx,lgp in enumerate(lgps):
            gidx = matchGroup(hgidxs,lgp,(lgpidx == (len(lgps)-1)))
            if(gidx == None):
                raise Exception("No group matched for line indexes. line="+l+" header_group_indexes="+
                                str(hgidxs)+" line_group_index="+str(lgp))


            if(gidx < len(result[-1])):
                result.append([])

            while(gidx > len(result[-1])):
                result[-1].append('')


            result[-1].append(normalize(l[lgp[0]:lgp[1]]))

    ulgmodel.debug('bgpmatchlines:'+str(result))

    return result

def normalizeBGPIPv6SumSplitLines(lines):
    """This function concatenates lines with longer IPv6 addresses that
router splits on the header boundary."""
    result = []
    slr = re.compile(BGP_IPV6_SUM_TABLE_SPLITLINE_REGEXP)
    b = None
    
    for l in lines:
        if(b):
            result.append(b + l)
            b = None
        elif(slr.match(l)):
            b = l
        else:
            result.append(l)
            
    return result

# classes

class CiscoCommandBgpIPv46Sum(ulgmodel.TextCommand):
    """ Abstract class, baseline for IPv4 and IPv6 versions. """

    RED_STATES = BGP_RED_STATES
    YELLOW_STATES = BGP_YELLOW_STATES

    def __init__(self,name=None,peer_address_command=None,peer_received_command=None):
        self.command=self.COMMAND_TEXT
        self.param_specs=[]
        self.peer_address_command = peer_address_command
        self.peer_received_command = peer_received_command

        if(name==None):
            if(self.param_specs):
                self.name=self.command % tuple([('<'+str(c.getName())+'>') for c in self.param_specs])
            else:
                self.name=self.command
        else:
            self.name = name


    def _getPeerURL(self,decorator_helper,router,peer_address):
        if decorator_helper and self.peer_address_command:
            return decorator_helper.getRuncommandURL({'routerid':str(decorator_helper.getRouterID(router)),
                                                      'commandid':str(decorator_helper.getCommandID(router,self.peer_address_command)),
                                                      'param0':peer_address})
        else:
            return None


    def _getPeerReceivedURL(self,decorator_helper,router,peer_address):
        if decorator_helper and self.peer_received_command:
            return decorator_helper.getRuncommandURL({'routerid':str(decorator_helper.getRouterID(router)),
                                                      'commandid':str(decorator_helper.getCommandID(router,self.peer_received_command)),
                                                      'param0':peer_address})
        else:
            return None


    def _getPeerTableCell(self,decorator_helper,router,peer):
        url = self._getPeerURL(decorator_helper,router,peer)
        if url:
            return decorator_helper.ahref(url,peer)
        else:
            return peer


    def _getReceivedTableCell(self,decorator_helper,router,peer,received):
        if re.compile('[0-9]+').match(received):
            url = self._getPeerReceivedURL(decorator_helper,router,peer)
            if url:
                return decorator_helper.ahref(url,received)
            else:
                return received
        else:
            return received

    def _decorateTableLine(self,line,decorator_helper,router):
        lrm = re.compile(self.TABLE_LINE_REGEXP).match(line)
        if(lrm):
            # color selection
            if(lrm.group(10) in self.YELLOW_STATES):
                color = ulgmodel.TableDecorator.YELLOW
            elif(lrm.group(10) in self.RED_STATES):
                color = ulgmodel.TableDecorator.RED
            else:
                color = ulgmodel.TableDecorator.GREEN

            # generate table content
            return [
                (self._getPeerTableCell(decorator_helper,router,lrm.group(1)),color),
                (lrm.group(2),color),
                (decorator_helper.decorateASN(lrm.group(3),prefix=''),color),
                (lrm.group(4),color),
                (lrm.group(5),color),
                (lrm.group(6),color),
                (lrm.group(7),color),
                (lrm.group(8),color),
                (lrm.group(9),color),
                (self._getReceivedTableCell(decorator_helper,router,lrm.group(1),lrm.group(10)),color),
                ]
        else:
            raise Exception("Can not parse line: "+line)

    def decorateResult(self,session,decorator_helper=None):
        if(not session):
            raise Exception('Can not decorate result without valid session.')

	if(session.getResult() == None):
            return (decorator_helper.pre(defaults.STRING_EMPTY), 1)
        
        if((not session.getRouter()) or (not decorator_helper)):
            return "<pre>\n%s\n</pre>" % session.getResult()

	lines=[]
        res=''
        for l in normalizeBGPIPv6SumSplitLines(str.splitlines(session.getResult())):
            lines.append(l)

        before=''
        after=''
        table=[]
        table_header=[]

        tb = False
        header_regexp = re.compile(self.TABLE_HEADER_REGEXP)
        line_regexp = re.compile(self.TABLE_LINE_REGEXP)
        for l in lines:
            if(tb):
                # inside table body
                table.append(self._decorateTableLine(l,decorator_helper,session.getRouter()))

            else:
                # should we switch to table body?
                thrm = header_regexp.match(l)
                if(thrm):
                    tb = True
                    table_header = [g for g in thrm.groups()]
                else:
                    # not yet in the table body, append before-table section
                    before = before + l + '\n'

        result_len = len(table)
        table = table[session.getRange():session.getRange()+defaults.range_step]

        return (ulgmodel.TableDecorator(table,table_header,before=decorator_helper.pre(before)).decorate(),result_len)


class CiscoCommandBgpIPv4Sum(CiscoCommandBgpIPv46Sum):
    COMMAND_TEXT='show bgp ipv4 unicast summary'
    TABLE_LINE_REGEXP=BGP_IPV46_TABLE_LINE_REGEXP
    TABLE_HEADER_REGEXP=BGP_IPV4_TABLE_HEADER_REGEXP

    def __init__(self,name=None,peer_address_command=None,peer_received_command=None):
        return CiscoCommandBgpIPv46Sum.__init__(self,name,peer_address_command,peer_received_command)


class CiscoCommandBgpIPv6Sum(CiscoCommandBgpIPv46Sum):
    COMMAND_TEXT='show bgp ipv6 unicast summary'
    TABLE_LINE_REGEXP=BGP_IPV46_TABLE_LINE_REGEXP
    TABLE_HEADER_REGEXP=BGP_IPV6_TABLE_HEADER_REGEXP

    def __init__(self,name=None,peer_address_command=None,peer_received_command=None):
        return CiscoCommandBgpIPv46Sum.__init__(self,name,peer_address_command,peer_received_command)


class CiscoCommandShowBgpIPv4Neigh(ulgmodel.TextCommand):
    COMMAND_TEXT='show bgp ipv4 unicast neighbor %s'

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[router.getBGPIPv4Select()],name=name)

class CiscoCommandShowBgpIPv6Neigh(ulgmodel.TextCommand):
    COMMAND_TEXT='show bgp ipv6 unicast neighbor %s'

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[router.getBGPIPv6Select()],name=name)

class CiscoCommandShowBgpIPv46Select(ulgmodel.TextCommand):
    TABLE_HEADER_REGEXP=BGP_PREFIX_TABLE_HEADER
    LASTLINE_REGEXP='^\s*Total number of prefixes [0-9]+\s*$'

    def __init__(self,peer_select_param,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,param_specs=[peer_select_param],name=name)

    def _decorateASPath(self,path,decorator_helper):
        result = ''
        for asnm in re.compile('[^\s]+').finditer(path):
            asn = asnm.group(0)
            if(asn.isdigit()):
                result = result + ' ' + decorator_helper.decorateASN(asn,prefix='')
            else:
                if(re.match('^\s*\{[0-9,]+\}\s*', asn)):
                    result = result + '{'
                    isnext = False
                    for sasnm in re.compile('([0-9]+)(,|\})').finditer(asn):
                        sasn = sasnm.group(0)
                        if(sasn.isdigit()):
                            if(isnext):
                                result = result + ',' + decorator_helper.decorateASN(sasn,prefix='')
                            else:
                                isnext = True
                                result = result + decorator_helper.decorateASN(sasn,prefix='')
                    result = result + '}'
                else:
                    result = result + ' ' +asn

        return result

    def _genTable(self,table_lines,decorator_helper,router):
        mls = matchCiscoBGPLines(self.table_header,table_lines)

        result = []
        for ml in mls:
		# generate table content
		result.append([
				(ml[0],),
				(decorator_helper.decoratePrefix(ml[1]),),
				(ml[2],),
				(ml[3],),
				(ml[4],),
				(ml[5],),
				(self._decorateASPath(ml[6],decorator_helper),),
				])
	return result

    def decorateResult(self,session,decorator_helper=None):
	def restrict(lines,start,count):
            res=[]
            s=start
	    r = re.compile("^\s{6,}.*")
	    
            while(r.match(lines[s]) and s > 0):
                s=s-1

	    e=s+count
	    if(e >= len(lines)):
		    e=len(lines)-1
	    while(r.match(lines[e]) and e < (len(lines)-1)):
                e=e+1

	    return lines[s:e]

        if(not session):
            raise Exception("Can not decorate result without valid session passed.")

	if(session.getResult() == None):
            return (decorator_helper.pre(defaults.STRING_EMPTY), 1)

        if((not session.getRouter()) or (not decorator_helper)):
            return "<pre>\n%s\n</pre>" % session.getResult()

        lines = str.splitlines(session.getResult())

        before=''
        after=None
        table=[]
        table_header_descr=[]

        tb = False
        header_regexp = re.compile(self.TABLE_HEADER_REGEXP)
        lastline_regexp = re.compile(self.LASTLINE_REGEXP)
        table_lines = []
        for l in lines:
            if(tb):
                # inside table body
                if(lastline_regexp.match(l)):
                    after = l
                else:
                    table_lines.append(l)

            else:
                # should we switch to table body?
                thrm = header_regexp.match(l)
                if(thrm):
                    # set header accoring to the local router alignment
                    # include (unnamed) states (=S)
                    self.table_header = 'S'+(l[1:].replace('Next Hop','Next_Hop',1))
                    tb = True
                    table_header_descr = [g for g in thrm.groups()]
                else:
                    # not yet in the table body, append before-table section
                    before = before + l + '\n'

        result_len = len(table_lines)
        if(table_lines):
            table = self._genTable(restrict(table_lines,session.getRange(),defaults.range_step),
                                   decorator_helper,session.getRouter())

        if(after):
            after=decorator_helper.pre(after)

        return (ulgmodel.TableDecorator(table,table_header_descr,before=decorator_helper.pre(before),
                                       after=after).decorate(),result_len)

        
class CiscoCommandShowBgpIPv4NeighAdv(CiscoCommandShowBgpIPv46Select):
    COMMAND_TEXT='show bgp ipv4 unicast neighbor %s advertised'

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,[router.getBGPIPv4Select()],name=name)

class CiscoCommandShowBgpIPv6NeighAdv(CiscoCommandShowBgpIPv46Select):
    COMMAND_TEXT='show bgp ipv6 unicast neighbor %s advertised'

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,[router.getBGPIPv6Select()],name=name)

class CiscoCommandShowBgpIPv4NeighRecv(CiscoCommandShowBgpIPv46Select):
    COMMAND_TEXT='show bgp ipv4 unicast neighbor %s received-routes'

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,[router.getBGPIPv4Select()],name=name)

class CiscoCommandShowBgpIPv6NeighRecv(CiscoCommandShowBgpIPv46Select):
    COMMAND_TEXT='show bgp ipv6 unicast neighbor %s received-routes'

    def __init__(self,router,name=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,[router.getBGPIPv6Select()],name=name)

class CiscoCommandGraphShowBgpIPv46Uni(ulgmodel.TextCommand):
    TABLE_HEADER_REGEXP=BGP_PREFIX_TABLE_HEADER

    def __init__(self,name=None,param=None):
        ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,
				      param_specs=[param],
				      name=name)

    def decorateResult(self,session,decorator_helper=None):
        if(session.isFinished()):
		if(session.getData() != None) and (session.getData() != []):
			return (decorator_helper.img(decorator_helper.getSpecialContentURL(session.getSessionId()),defaults.STRING_BGP_GRAPH),1)
		else:
			return (decorator_helper.pre(defaults.STRING_BGP_GRAPH_ERROR), 1)
	else:
		return ('',0)

    def finishHook(self,session):
	    session.setData(cisco_parse_sh_bgp_uni(session.getResult(),str(session.getRouter().getASN())))

    def getSpecialContent(self,session,**params):
        paths = session.getData()
        print "Content-type: image/png\n"
        ulggraph.bgp_graph_gen(reduce_bgp_paths(paths),start=session.getRouter().getName(),
			       end=session.getParameters()[0])

    def showRange(self):
        return False


class CiscoCommandGraphShowBgpIPv4Uni(CiscoCommandGraphShowBgpIPv46Uni):
    COMMAND_TEXT='show bgp ipv4 unicast %s'

    def __init__(self,router,name=None):
        CiscoCommandGraphShowBgpIPv46Uni.__init__(self,name,param=ulgmodel.IPv4SubnetParameter())


class CiscoCommandGraphShowBgpIPv6Uni(CiscoCommandGraphShowBgpIPv46Uni):
    COMMAND_TEXT='show bgp ipv6 unicast %s'

    def __init__(self,router,name=None):
        CiscoCommandGraphShowBgpIPv46Uni.__init__(self,name,param=ulgmodel.IPv6SubnetParameter())



class CiscoShowBgpIPv46Uni(ulgmodel.TextCommand):
	def __init__(self,param):
		ulgmodel.TextCommand.__init__(self,self.COMMAND_TEXT,[param]),

	def decorateResult(self,session,decorator_helper=None):
		def decorateLine(l):			
			m = regex_sh_bgp_uni_asline.match(l)
			if(m):
				r = m.group(1)
				ases = str.split(m.group(2))
				for asn in ases:
					r = r + ' ' + decorator_helper.decorateASN(asn,prefix='')
				r = r + m.group(3)
				return decorator_helper.annotateIPs(r)
			else:
				return decorator_helper.annotateIPs(l)


		s = str.splitlines(session.getResult())
		lbeg = 0
		lend = len(s)
		if(session.getRange() != None and self.showRange()):
			lbeg = session.getRange()
			lend = session.getRange()+defaults.range_step+1

		r=''
		table_started=False
		table_prestarted = False
		for sl in s[lbeg:lend]:
			if(table_started):
				r += decorateLine(sl) + "\n"
			else:
				r += sl + "\n"
				if(table_prestarted):
					table_started = True
				if(regex_sh_bgp_uni_table_start.match(sl)):
					table_prestarted = True

		return ("<pre>\n%s\n</pre>" % r, len(s))


class CiscoShowBgpIPv4Uni(CiscoShowBgpIPv46Uni):
	COMMAND_TEXT = 'show bgp ipv4 unicast %s'

	def __init__(self,name=None):
		CiscoShowBgpIPv46Uni.__init__(self,param=ulgmodel.IPv4SubnetParameter())


class CiscoShowBgpIPv6Uni(CiscoShowBgpIPv46Uni):
	COMMAND_TEXT = 'show bgp ipv6 unicast %s'

	def __init__(self,name=None):
		CiscoShowBgpIPv46Uni.__init__(self,param=ulgmodel.IPv6SubnetParameter())


class CiscoRouter(ulgmodel.RemoteRouter):
    PS_KEY_BGPV4 = '-bgpipv4'
    PS_KEY_BGPV6 = '-bgpipv6'

    def _getDefaultCommands(self):
        return self._getBGPCommands()

    def _getAllCommands(self):
        _show_bgp_ipv4_uni_neigh = CiscoCommandShowBgpIPv4Neigh(self)
        _show_bgp_ipv4_uni_neigh_advertised = CiscoCommandShowBgpIPv4NeighAdv(self)
        _show_bgp_ipv4_uni_neigh_received_routes = CiscoCommandShowBgpIPv4NeighRecv(self)
        _show_bgp_ipv6_uni_neigh = CiscoCommandShowBgpIPv6Neigh(self)
        _show_bgp_ipv6_uni_neigh_advertised = CiscoCommandShowBgpIPv6NeighAdv(self)
        _show_bgp_ipv6_uni_neigh_received_routes = CiscoCommandShowBgpIPv6NeighRecv(self)
        _graph_show_bgp_ipv4_uni = CiscoCommandGraphShowBgpIPv4Uni(self,COMMAND_NAME_GRAPH4)
	_graph_show_bgp_ipv6_uni = CiscoCommandGraphShowBgpIPv6Uni(self,COMMAND_NAME_GRAPH6)

        return [ulgmodel.TextCommand('show version'),
                ulgmodel.TextCommand('show interfaces status'),
                CiscoCommandBgpIPv4Sum('show bgp ipv4 unicast summary',
                                        peer_address_command=_show_bgp_ipv4_uni_neigh,
                                       peer_received_command=_show_bgp_ipv4_uni_neigh_received_routes),
                CiscoCommandBgpIPv6Sum('show bgp ipv6 unicast summary',
                                       peer_address_command=_show_bgp_ipv6_uni_neigh,
                                       peer_received_command=_show_bgp_ipv6_uni_neigh_received_routes),
                _show_bgp_ipv4_uni_neigh,
                _show_bgp_ipv6_uni_neigh,
                _show_bgp_ipv4_uni_neigh_received_routes,
                _show_bgp_ipv6_uni_neigh_received_routes,
                _show_bgp_ipv4_uni_neigh_advertised,
                _show_bgp_ipv6_uni_neigh_advertised,
                CiscoShowBgpIPv4Uni(),
		CiscoShowBgpIPv6Uni(),
                ulgmodel.TextCommand('show ip route %s',[ulgmodel.IPv4AddressParameter()]),
                ulgmodel.TextCommand('show ipv6 route %s',[ulgmodel.IPv6AddressParameter()]),
                ulgmodel.TextCommand('show ip arp %s',[ulgmodel.TextParameter('.*',name=defaults.STRING_NONEORINTORIPADDRESS)]),
                ulgmodel.TextCommand('show ipv6 neighbors %s',[ulgmodel.TextParameter('.*',name=defaults.STRING_NONEORINTORIPADDRESS)]),
                ulgmodel.TextCommand('show mac-address-table address %s',[ulgmodel.TextParameter(MAC_ADDRESS_REGEXP,name=defaults.STRING_MACADDRESS)]),
                ulgmodel.TextCommand('show mac-address-table interface %s',[ulgmodel.TextParameter('.*',name=defaults.STRING_INTERFACE)]),
                _graph_show_bgp_ipv4_uni,
		_graph_show_bgp_ipv6_uni,
		ulgmodel.TextCommand('ping %s',[ulgmodel.IPv64AddressParameter()]),
		ulgmodel.TextCommand('traceroute %s',[ulgmodel.IPv64AddressParameter()]),
                ]

    def _getBGPCommands(self):
        _show_bgp_ipv4_uni_neigh = CiscoCommandShowBgpIPv4Neigh(self)
        _show_bgp_ipv4_uni_neigh_advertised = CiscoCommandShowBgpIPv4NeighAdv(self)
        _show_bgp_ipv4_uni_neigh_received_routes = CiscoCommandShowBgpIPv4NeighRecv(self)
        _show_bgp_ipv6_uni_neigh = CiscoCommandShowBgpIPv6Neigh(self)
        _show_bgp_ipv6_uni_neigh_advertised = CiscoCommandShowBgpIPv6NeighAdv(self)
        _show_bgp_ipv6_uni_neigh_received_routes = CiscoCommandShowBgpIPv6NeighRecv(self)
        _graph_show_bgp_ipv4_uni = CiscoCommandGraphShowBgpIPv4Uni(self,COMMAND_NAME_GRAPH4)
	_graph_show_bgp_ipv6_uni = CiscoCommandGraphShowBgpIPv6Uni(self,COMMAND_NAME_GRAPH6)

        return [
		CiscoCommandBgpIPv4Sum('show bgp ipv4 unicast summary',
                                        peer_address_command=_show_bgp_ipv4_uni_neigh,
                                       peer_received_command=_show_bgp_ipv4_uni_neigh_received_routes),
                CiscoCommandBgpIPv6Sum('show bgp ipv6 unicast summary',
                                       peer_address_command=_show_bgp_ipv6_uni_neigh,
                                       peer_received_command=_show_bgp_ipv6_uni_neigh_received_routes),
                _show_bgp_ipv4_uni_neigh,
                _show_bgp_ipv6_uni_neigh,
                _show_bgp_ipv4_uni_neigh_received_routes,
                _show_bgp_ipv6_uni_neigh_received_routes,
                _show_bgp_ipv4_uni_neigh_advertised,
                _show_bgp_ipv6_uni_neigh_advertised,
                CiscoShowBgpIPv4Uni(),
		CiscoShowBgpIPv6Uni(),
                _graph_show_bgp_ipv4_uni,
		_graph_show_bgp_ipv6_uni,
		ulgmodel.TextCommand('ping %s',[ulgmodel.IPv64AddressParameter()]),
		ulgmodel.TextCommand('traceroute %s',[ulgmodel.IPv64AddressParameter()]),
                ]


    def __init__(self, host, user, password, port=22, commands=None, enable_bgp=True, asn='My ASN', name=None, acl=None):
        ulgmodel.RemoteRouter.__init__(self,acl=acl)

        self.setHost(host)
        self.setPort(port)
        self.setUser(user)
        self.setPassword(password)
        self.bgp_ipv4_peers = []
        self.bgp_ipv6_peers = []
        if(name):
            self.setName(name)
        else:
            self.setName(host)
	self.setASN(asn)

        if enable_bgp:
            if(defaults.rescan_on_display):
                self.rescanHook()
            else:
                self.loadBGPPeers()

	    rid = hashlib.md5(self.getName()).hexdigest()

	    self.bgp4select = ulgmodel.CommonSelectionParameter(rid+"bgp4",[tuple((p,p,)) for p in self.getBGPIPv4Peers()],
                                                 name=defaults.STRING_IPADDRESS)
	    self.bgp6select = ulgmodel.CommonSelectionParameter(rid+"bgp6",[tuple((p,p,)) for p in self.getBGPIPv6Peers()],
                                                 name=defaults.STRING_IPADDRESS)

        if(commands):
            self.setCommands(commands)
        else:
            self.setCommands(self._getDefaultCommands())


    def getForkNeeded(self):
        return True

    def rescanBGPPeers(self,command,regexp):
        table = self.runRawSyncCommand(command)

        peers = []
        rlr = re.compile(regexp)
	lines = normalizeBGPIPv6SumSplitLines(str.splitlines(table))

        for tl in lines:
            rlrm = rlr.match(tl)
            if(rlrm):
                peers.append(rlrm.group(1))

        return peers

    def rescanBGPIPv4Peers(self):
        self.bgp_ipv4_peers = self.rescanBGPPeers(RESCAN_BGP_IPv4_COMMAND,BGP_IPV46_TABLE_LINE_REGEXP)

    def rescanBGPIPv6Peers(self):
        self.bgp_ipv6_peers = self.rescanBGPPeers(RESCAN_BGP_IPv6_COMMAND,BGP_IPV46_TABLE_LINE_REGEXP)
        
    def rescanHook(self):
        self.rescanBGPIPv4Peers()
        self.rescanBGPIPv6Peers()
        self.saveBGPPeers()

    def getBGPIPv4Peers(self):
        return self.bgp_ipv4_peers

    def getBGPIPv6Peers(self):
        return self.bgp_ipv6_peers

    def getBGPIPv4Select(self):
        return self.bgp4select

    def getBGPIPv6Select(self):
        return self.bgp6select

    def saveBGPPeers(self):
        key4 = self.getHost() + self.PS_KEY_BGPV4
        key6 = self.getHost() + self.PS_KEY_BGPV6

        ps = ulgmodel.loadPersistentStorage()
        ps.set(key4,self.getBGPIPv4Peers())
        ps.set(key6,self.getBGPIPv6Peers())
        ps.save()

    def loadBGPPeers(self):
        key4 = self.getHost() + self.PS_KEY_BGPV4
        key6 = self.getHost() + self.PS_KEY_BGPV6

        ps = ulgmodel.loadPersistentStorage()
        self.bgp_ipv4_peers = ps.get(key4)
        self.bgp_ipv6_peers = ps.get(key6)

        if(not self.getBGPIPv4Peers()) or (not self.getBGPIPv6Peers()):
            self.rescanHook()

    def runRawCommand(self,command,outfile):
        skiplines=1

	# connect
        c=defaults.bin_ssh+' -p'+str(self.getPort())+' '+str(self.getUser())+'@'+self.getHost()
        s=pexpect.spawn(c,timeout=defaults.timeout)

##      Debug logging
#	s.logfile = open('/tmp/ulgcisco.log', 'w')

	y=0
	p=0
        # handle ssh
	while True:
		i=s.expect([STRING_EXPECT_SSH_NEWKEY,STRING_EXPECT_PASSWORD,
			    STRING_EXPECT_SHELL_PROMPT_REGEXP,pexpect.EOF,pexpect.TIMEOUT])
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
		elif(i==2): # prompt
			break
		elif(i==3):
			raise Exception("pexpect session failed: Remote server disconnected.")
		elif(i==4):
			raise Exception("pexpect session failed: Connection timeout.")
		else:
			raise Exception("pexpect session failed: Unknown error. last output: "+s.before)

	s.sendline('terminal length 0')
	s.expect(['\n',pexpect.EOF,pexpect.TIMEOUT])

	s.sendline('terminal width 0')
	s.expect(['\n',pexpect.EOF,pexpect.TIMEOUT])

	l=0
	s.sendline(command)
	while True:
		i=s.expect([STRING_EXPECT_SHELL_PROMPT_REGEXP,'\n',pexpect.EOF,pexpect.TIMEOUT])
		if(i==0): # prompt
			s.sendline(STRING_COMMAND_LOGOUT)
			s.expect(['\n',pexpect.EOF,pexpect.TIMEOUT])
			break
		elif(i==1): # anything to capture
			if(l>=skiplines):
				outfile.write(s.before + "\n")
			l+=1
		elif(i==2):
			raise Exception("pexpect session failed: Remote server disconnected.")
		elif(i==3):
			raise Exception("pexpect session failed: Connection timeout.")
		else:
			raise Exception("pexpect session failed: Unknown error. last output: "+s.before)
