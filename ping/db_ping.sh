process_one(){
log=$1
#log='ping_103.216.40.3.log'
packetloss=100;
packet=$(grep -F "loss" $log |awk  '{print $7}')
tinfo=$(grep -F "stddev" $log |awk  '{print $4}')
ipinfo=$(grep -F "statistics" $log |awk  '{print $2}')


LEN=$(echo ${#tinfo})
if [ $LEN -lt 20 ]; then
 min_t=10000
 max_t=10000
 avg_t=10000
 mdev=10000
else
 IFS='/' read -r -a ping_time <<< "$tinfo"
 min_t="${ping_time[0]}"
 max_t="${ping_time[1]}"
 avg_t="${ping_time[2]}"
 mdev="${ping_time[3]}"
fi

packetloss="${packet/\%/}"
sql="insert into batchping(sub_ip,packetloss,min_t,max_t,avg_t,mdev,pingdate) values ( '$ipinfo',$packetloss,$min_t,$max_t,$avg_t,$mdev,now()) "
echo $sql
mysql -D ixp2 -uroot -pcnix@1234 -h mysql -e "$sql"
mv $log /opt/batchjob/done/
}

for file in /opt/batchjob/log/ping_*
do
    #whatever you need with "$file"
    echo $file
    process_one  $file
done
