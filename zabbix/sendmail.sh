#!/bin/sh
# 解决中文乱码问题
export LANG=zh_CN.UTF-8
to=$1
subject=$2
body=$3

# 方法1, 创建一个临时文件
FILE=/tmp/mailtmp.txt
if [ ! -f $FILE ];then 
touch $FILE
chown zabbix.zabbix $FILE
fi

echo "$body" > $FILE
dos2unix -k $FILE
mailx  -s "$subject" $to <$FILE

