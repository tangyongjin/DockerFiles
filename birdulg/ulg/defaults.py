#!/usr/bin/env python
#coding=utf-8
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

# Router config file
config_file = '/etc/ulg/config.py'

# HTML presentation settings
header = 'Looking Glass'
refresh_interval = 5                             # interval of html refresh
usage_limit = 5                                    # maximum concurrently processed requests
range_step = 10000                           # number of table lines in the decorated output per page

# Default settings
always_start_thread = True # True is highly recommended
debug = False
rescan_on_display = False
persistent_storage_file = '/tmp/ulg.data'
session_dir = '/tmp'
usage_counter_file = '/tmp/ulg.lock'
log_file = '/tmp/ulg.log'
default_bird_sock = '/var/run/bird.ctl'
default_bird_sock_timeout = 30
default_bin_birdc = '/usr/sbin/birdc'
bin_whois = '/usr/bin/whois'
timeout = 20

# Template dir relative to the index.py script
template_dir = 'templates'
index_template_file = 'index.html'
whois_template_file = 'whois.html'
table_decorator_template_file = 'tabledecorator.html'

# Paths to external programs
bin_ssh = '/usr/bin/ssh'
bin_telnet = '/usr/bin/telnet'

# Output (localized) strings
STRING_ANY='any'
STRING_PARAMETER='Parameter'
STRING_COMMAND='Command'
STRING_ERROR_COMMANDRUN='Error encountered while preparing or running command'
STRING_BAD_PARAMS='Verification of command or parameters failed.'
STRING_SESSION_OVERLIMIT = "<em>Limit of maximum concurrently running sessions and/or queries has been reached. The command can not be executed now. Please try again later.</em>"
STRING_SESSION_ACCESSDENIED = "<em>Access denied. The command can not be executed. Please contact the administrator.</em>"
STRING_ARBITRARY_ERROR = "Error encountered. Operation aborted. See log for further details."
STRING_IPADDRESS = "IP address"
STRING_IPSUBNET = "IP subnet"
STRING_MACADDRESS = "MAC address"
STRING_NONEORINTORIPADDRESS = "None or Interface or IP address"
STRING_INTERFACE = "Interface"
STRING_SOCKET_TIMEOUT = "Socket communication timed out. See log."
STRING_PEERID = "Peer ID"
STRING_RTABLE = "Routing Table"
STRING_DETAILS = "Details of"
STRING_UNKNOWN = "(unknown)"
STRING_BGP_GRAPH='BGP graph'
STRING_BGP_GRAPH_ERROR='Error: Can not produce image out of the received output.'
STRING_EMPTY=' '

# URL generator functions
def getASNURL(asn):
    return 'https://apps.db.ripe.net/search/query.html?searchtext=%s&flags=C&sources=&grssources=RIPE;AFRINIC;APNIC;ARIN;LACNIC;JPIRR;RADB&inverse=&types=AUT_NUM' % asn

def getIPPrefixURL(prefix):
    return 'https://apps.db.ripe.net/search/query.html?searchtext=%s&flags=C&sources=&grssources=RIPE;AFRINIC;APNIC;ARIN;LACNIC;JPIRR;RADB&inverse=&types=INET6NUM;INETNUM' % prefix
