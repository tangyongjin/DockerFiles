
##    - "/ixpdata/webapp/opt/docker/sflow.dongxi/dongxi.php:/dongxi.php"
   

FROM ixp.sflowruntime
ENV DEBIAN_FRONTEND noninteractive


RUN apt-get -qq update && apt-get install -y \
  vim  \
  php5  \
  php5-mysql \
  php5-dev \
  php5-gd \
  php5-memcache \
  php5-pspell \
  php5-snmp \
  snmp \
  php5-xmlrpc \
  libapache2-mod-php5 \
  php5-cli  \
  php5-rrd


EXPOSE 5501
COPY supervisord.conf.sflowdongxi /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord","-c","/etc/supervisor/conf.d/supervisord.conf"]
