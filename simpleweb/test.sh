docker kill proxy
sleep 2
 docker run -it -d  --rm  -v /root/dockers/proxy:/var/www/html -p 8000:80 --name  proxy    xnet.base
