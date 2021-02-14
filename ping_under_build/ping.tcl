#!/usr/bin/expect -f
package require mysqltcl 


log_user 0
exp_internal 0
set timeout -1
set match_max 90000

set rs  103.216.40.1
set username view-only
set password cnix@63602
set dbuser root
set dbpasswd cnix@1234

set conn [mysqlconnect -host  mysql -user $dbuser  -password  $dbpasswd]

proc retieve {text } {

    set match []
    foreach line $text {
      set isMatch [string match {*rt-destination*\>*\<\/rt-destination\>} $line]
      if { $isMatch != 0 } {

         regsub -all (rt-destination|<|>|/rt-destination) $line  {} result 
         lappend  match  $result
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


proc  oneip_process {conn ip info} {

    set  ip \'$ip\'
    set info [retieve $info]

    mysqluse $conn ixp2

    set oldmd5 nothing
    set total [llength  $info ]
    set md5sum [ exec   echo $info | md5sum | awk "{print \$1}" ] 
    set old_dst_ip ''
    set oldrows  -1
    set oldmd5    nothing
    set firstmd5  nothing

    set sql "select dst_ip,rows,md5summary from  rtdst where  sub_ip=$ip limit 1"
    mysql::sel $conn $sql
      
    while {[llength [set row [mysql::fetch $conn]]]>0} {
      set old_dst_ip [lindex $row 0]
      set oldrows [lindex $row 1]
      set oldmd5 [lindex $row 2]
   }
    
    if { $oldmd5  eq  $firstmd5} {

       set sql "insert into rtdst (querydate,sub_ip,dst_ip, rows,md5summary) values( now(),$ip, \'$info\', $total,\'$md5sum\') "
       mysqlexec $conn  $sql

    } else {

        set sql "update rtdst set  rows=$total  , querydate=now(),md5summary=\'$md5sum\' where sub_ip=$ip  "
        mysqlexec $conn  $sql
        if { $oldmd5  eq  $md5sum} {
        } else {
        set  rt_diff [ListComp $info $old_dst_ip]
        set sql "insert into  ticket(sub_ip,msg,reason,memo,issuedate,fixed,fixedby,raisedby,custrelate,custnamerelate,rt_diff) values 
         ( $ip,'route-changed', 'route-changed from $oldrows -> $total', \'$old_dst_ip\',now(), 'n',null,'batch-container',null,null,
         \'$rt_diff\' )"
         mysqlexec $conn  $sql
        
        }
    }
}


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

                            -re "re0>" {
                                append summary $expect_out(buffer)

                           }
                           default {

                           }
                        }
            }
        }

unset expect_out(buffer)
set iplist [ exec  echo $summary  | awk "/Peer/{flag=1;next}/master/{flag=0}flag"   | grep -oE {[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+} ] 
 
foreach  ip $iplist {
      set oneipreport ''
      send -i $session_id "show route receive-protocol bgp $ip|dis xml \r"
      expect {
                          
                           -re "more" {
                                    append oneipreport $expect_out(buffer)
                                    send "\r"
                                    exp_continue
                           }

                           -re "re0>" {
                                    append oneipreport $expect_out(buffer)
                           }
                }
            unset expect_out(buffer)
            oneip_process $conn $ip  $oneipreport
}



exp_close -i $session_id
::mysql::close $conn
exit