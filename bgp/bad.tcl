#!/usr/bin/expect  --
## 按照ping 模式.
##rs telnet 103.216.40.1 -l  view-only cnix@63602
#show route receive-protocol bgp 
#不能直接运行infinity.sh, 必须在container起来后运行, 原因未知

package require mysqltcl 
package require md5


log_user 1
exp_internal 0
set timeout -1
set match_max 90000000000

set rs  103.216.40.1
set username view-only
set password cnix@63602
set dbuser root
set dbpasswd cnix@1234
set dbhost 172.18.0.2 
#set dbhost mysql

set conn [mysqlconnect -host  $dbhost -user $dbuser  -password  $dbpasswd]
mysqluse $conn ixp2



 
set summary2  "ABCD114.11.111.111"

set status [catch {exec  echo $summary2  | awk "/Peer/{flag=1;next}/master/{flag=0}flag"   | grep -oE {[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+}} result]

 if {$status == 0} {
    # The command succeeded, and wrote nothing to stderr.
    # $result contains what it wrote to stdout, unless you
    # redirected it
} elseif {[string equal $::errorCode NONE]} {
    # The command exited with a normal status, but wrote something
    # to stderr, which is included in $result.
} else {
    switch -exact -- [lindex $::errorCode 0] {
        CHILDKILLED {
            foreach {- pid sigName msg} $::errorCode break

            # A child process, whose process ID was $pid,
            # died on a signal named $sigName.  A human-
            # readable message appears in $msg.

        }
        CHILDSTATUS {
            foreach {- pid code} $::errorCode break

            # A child process, whose process ID was $pid,
            # exited with a non-zero exit status, $code.

        }

        CHILDSUSP {

            foreach {- pid sigName msg} $::errorCode break

            # A child process, whose process ID was $pid,
            # has been suspended because of a signal named
            # $sigName.  A human-readable description of the
            # signal appears in $msg.

        }

        POSIX {

            foreach {- errName msg} $::errorCode break

            # One of the kernel calls to launch the command
            # failed.  The error code is in $errName, and a
            # human-readable message is in $msg.

        }

    }
}