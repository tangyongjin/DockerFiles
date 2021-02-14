docker run -d -it --name bird --net=host --privileged -p 80:80 -p 103.216.41.1:179:179 \
 -v /home/birdulg/birdcfg/:/usr/local/etc/ \
 -v /home/birdulg/ulg:/var/www/html \
 -v /home/birdulg/ulg/config.py:/etc/ulg/config.py \
--rm ixp.bird_and_ulg
