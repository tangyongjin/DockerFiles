#!/usr/bin/expect  --
## 按照ping 模式.
##rs telnet 103.216.40.1 -l  view-only cnix@63602
#show route receive-protocol bgp 
#不能直接运行infinity.sh, 必须在container起来后运行, 原因未知
#  no xml
#  丢数据,在show route receive-protocol





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


proc retrieve { text } {

  set match {}
  set data [split $text "\n"]
  foreach line $data {
          puts ONELINE:
          puts $line
          set var0 [lindex $line 0]
          if { $var0  == "*" }  {
           set var1 [lindex $line 1]
           lappend  match  $var1
          } 

  }

 set sorted [lsort $match]
 return $sorted
 

 
}



 
  
proc ListComp { List1 List2 } {
   
   set DiffList {}
   set Diffadd {}
   set Diffdel {}


   foreach Item $List1 {
      if { [ lsearch -exact $List2 $Item ] == -1 } {
         lappend Diffdel $Item
      }
   }
   
   foreach Item $List2 {
      if { [ lsearch -exact $List1 $Item ] == -1 } {
         if { [ lsearch -exact $DiffList $Item ] == -1 } {
            lappend Diffadd $Item
         }
      }
   }

   set  total1 [llength  $Diffadd ]
   set  total2 [llength  $Diffdel ]
   return "Added($total1):$Diffadd/ Deleted($total2):$Diffdel"
}


# proc  oneip_process2 {ip info conn} {
#     set  ip \'$ip\'
#     set newinfo [retrieve  $info]
#     puts $newinfo 


# }

proc  oneip_process {ip info conn} {

    # puts "infoget:"
    # puts $info
    # puts "++++++++"
    


    set  ip \'$ip\'
    set newinfo [retrieve  $info]

      

    set total [llength  $newinfo ]
    puts "total:$total"
    puts "detail:$newinfo" 

    set md5sum [md5::md5 -hex  $newinfo ]

    set old_dst_ip  RPT_
    set oldrows  -1
    set oldmd5    firsttime
    set firstmd5  firsttime


    #save tcl log
    set sql "insert into rtdst_log2 (querydate,sub_ip,info) values( now(),$ip, \'$newinfo\' ) "
    mysqlexec $conn  $sql


    set sql "update rtdst2 set  dst_ip_history=dst_ip where sub_ip=$ip  "
    mysqlexec $conn  $sql
      


    set sql "select dst_ip,rows,md5summary,dst_ip_history from  rtdst2 where  sub_ip=$ip limit 1"
    mysql::sel $conn $sql

    while {[llength [set row [mysql::fetch $conn]]]>0} {
      set old_dst_ip [lindex $row 0]
      set oldrows [lindex $row 1]
      set oldmd5 [lindex $row 2]
      set dst_ip_history [lindex $row 3]
   }
    
    if { $oldmd5  eq  $firstmd5} {

       #First time,only insert.
       set sql "insert into rtdst2 (querydate,sub_ip,dst_ip, rows,md5summary) values( now(),$ip, \'$newinfo\',$total,\'$md5sum\') "
       mysqlexec $conn  $sql

    } else {

        set sql "update rtdst2 set  rows=$total, querydate=now(), dst_ip=\'$newinfo\',md5summary=\'$md5sum\' where sub_ip=$ip  "
        mysqlexec $conn  $sql

        if { $oldmd5  eq  $md5sum} {
        } else {
        set rt_diff [ListComp $dst_ip_history  $newinfo  ]

        # set sql "insert into  ticket(sub_ip,msg,reason,memo,issuedate,fixed,fixedby,raisedby,custrelate,custnamerelate,rt_diff) values 
        #  ( $ip,'route-changed', 'route-changed from $oldrows -> $total', \'$old_dst_ip\',now(), 'n','y','batch-container',-1,'--',
        #  \'$rt_diff\' )"
        #  mysqlexec $conn  $sql
       
          ### send waring msg to dingding
          # exec curl  http://web/ixp/ajax.php?action=warn
          #exec /bin/bash -c "curl http://web/ixp/ajax.php?action=warn  2>@1 > /dev/null"

        }
    }
}


puts "Begin telnet to route server"
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
          set oneipreport IP_RPT


          send -i $session_id "show route receive-protocol bgp $Xip  \r"
          
          while { 1 } {
              expect {
                          -re "more" {
                                  send "\t"
                                  #append oneipreport $expect_out(buffer)
                                  exp_continue
                           }
                        

                          "\n"   {
                                 append oneipreport $expect_out(buffer)
                                 exp_continue
                              }

                          # Wait for prompt and then break out of the while loop to continue the script
                          -re "re0>" {
                                  append oneipreport $expect_out(buffer)
                                  break
                          }

                          # If nothing matches then timeout
                          timeout {puts "Timeout error. Is host down or unreachable? ssh_expect";exit}
                }
          }



          oneip_process  $Xip  $oneipreport $conn
           
}

::mysql::close $conn
exit
