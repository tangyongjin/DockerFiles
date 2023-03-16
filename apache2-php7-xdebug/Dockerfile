FROM ubuntu:16.04
MAINTAINER Alexander Schenkel <alex@alexi.ch>

RUN sed -i s@/archive.ubuntu.com/@/mirrors.aliyun.com/@g /etc/apt/sources.list
RUN apt-get clean
WORKDIR /var/www/html


RUN apt-get update  &&  apt-get install -y axel aria2 
RUN  apt  install -y software-properties-common  &&  apt-add-repository ppa:apt-fast/stable
RUN  apt-get update  &&  apt-get install -y  apt-fast

RUN apt-fast update && apt  install -y software-properties-common  && export LANG=C.UTF-8 && add-apt-repository ppa:ondrej/php 

RUN apt-fast update && \
    apt-fast dist-upgrade -y && \
    apt-fast install -y \
      apache2 \
      php7.3 \
      php7.3-cli \
      libapache2-mod-php7.3 \
      php-apcu \
      php7.3-curl \
      php-xdebug \
      php7.3-gd \
      php7.3-json \
      php7.3-ldap \
      php7.3-mbstring \
      php7.3-mysql \
      php7.3-pgsql \
      php7.3-sqlite3 \
      php7.3-xml \
      php7.3-xsl \
      php7.3-zip \
      php7.3-soap \
      php7.3-imap \
      php7.3-opcache \  
      php7.3-bcmath \ 
      vim \
      wget \
      composer \
      inotify-tools
      
RUN   apt-get install  -y php7.3-dev libmcrypt-dev php-pear
RUN   pecl channel-update pecl.php.net
RUN   printf "\n" | pecl install mcrypt-1.0.2

COPY php.ini /etc/php/7.3/apache2/

ADD 000-default.conf /etc/apache2/sites-enabled/000-default.conf
#RUN  bash -c "echo extension=mcrypt.so > /etc/php/7.3/apache2/php.ini"
#RUN  bash -c "echo extension=mcrypt.so > /etc/php/7.3/cli/php.ini"



RUN a2enmod rewrite  ssl
RUN wget https://getcomposer.org/download/1.8.0/composer.phar -O /usr/local/bin/composer &&  chmod 755 /usr/local/bin/composer


### 如果ssl 出问题,进容器,并手工执行. a2ensite
RUN cd /etc/apache2/sites-available &&  a2ensite *
RUN touch /tmp/php_error.log && chmod 777 /tmp/php_error.log
RUN echo "Asia/Shanghai" > /etc/timezone 
RUN rm -f /etc/localtime
RUN dpkg-reconfigure -f noninteractive tzdata
COPY init.sh  /usr/local/bin/
EXPOSE 80 443
ENTRYPOINT ["init.sh"]

 
