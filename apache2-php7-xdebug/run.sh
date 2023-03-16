docker kill debug 
docker rm debug
docker run  -itd --rm    -p 8888:80  --name  debug  -v /tmp/html/:/var/www/html  apache2-php7-x
