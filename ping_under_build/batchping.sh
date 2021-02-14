#!/bin/bash


#step0:  delete *.log


rm -fr /opt/batchjob/*.log
rm -fr /opt/batchjob/*.lst
touch  /opt/batchjob/bgpsummary.log
touch  /opt/batchjob/bgpips.lst
touch bat.log


#step1: get all  ip address

/usr/local/bin/getip.exp


/usr/local/bin/getip.sh



#step2: ping all ips in file    bgpips.lst
/usr/local/bin/batping.exp

#step3: process all ping logs 
/usr/local/bin/db.sh
