#!/bin/bash



awk '/Peer/{flag=1;next}/master/{flag=0}flag' /opt/batchjob/bgpsummary.log|grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'|
while IFS='\n' read URL
do
  echo $URL| awk '{print $1}'  >> /opt/batchjob/bgpips.lst
done


