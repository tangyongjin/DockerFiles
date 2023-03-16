#!/bin/bash
#Content=$2
curl 'https://oapi.dingtalk.com/robot/send?access_token=5e401200959ff772720eceac0afeccb8eb29cf215c0465ecb13e8a14260e14f6' -H 'Content-Type: application/json' -d '
  {"msgtype":"text",
    "text":{
"content":"'$2'  "
}}
'
