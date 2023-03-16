#!/usr/bin/expect  --

log_user 1
exp_internal 0
set timeout -1
set match_max 90000000000

set rs  103.216.40.1
set username view-only
set password cnix@63602

spawn    telnet  $rs  -l  $username
set session_id $spawn_id
set summary  'result::'

expect {
            -re ".*assword:" {
                send "$password\r"
                exp_continue
             }


             -re "re0>" {

                send  "show bgp summary \n"
                expect {

                            -re "more" {
                                    append summary $expect_out(buffer)
                                    send "\r"
                                    exp_continue
                           }


                             "\n"   {
                                    append summary $expect_out(buffer)
                                    exp_continue
                              }

                            -re "re0>" {
                                    append summary $expect_out(buffer)
                           }

                        }
            }
        }


puts ++++++++++++++++++++++++++++++
puts $summary

set iplist [ exec  echo $summary  | awk "/Peer/{flag=1;next}/master/{flag=0}flag"   | grep -oE {[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+} ] 

          
foreach  Xip $iplist {
          puts "query ip: $Xip "
}
