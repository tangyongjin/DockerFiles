#!/bin/bash


#step0:  delete *.log


rm -fr /opt/batchjob/*.log
rm -fr /opt/batchjob/*.lst
touch  /opt/batchjob/bgpsummary.log
touch  /opt/batchjob/bgpips.lst
touch bat.log


#step1: get all  bgp-summary  ips

/usr/local/bin/getip.exp

awk '/Peer/{flag=1;next}/master/{flag=0}flag' /opt/batchjob/bgpsummary.log|grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'|
while IFS='\n' read URL
do
  echo $URL| awk '{print $1}'  >> /opt/batchjob/bgpips.lst
done


#step2: ping all ips in file    bgpips.lst
/usr/local/bin/batping.exp

#step3: process all ping logs 
/usr/local/bin/db_ping.sh


