FROM ubuntu:14.04

RUN apt-get update && apt-get install -y locales && rm -rf /var/lib/apt/lists/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG en_US.utf8
ENV TERM  vt100

RUN apt-get update && apt-get install -y  software-properties-common
RUN add-apt-repository ppa:ondrej/php
RUN apt-get update  &&   apt-get install -y  php5.6 \
    php5.6-mbstring  \
    php5.6-mcrypt \
    php5.6-mysql \
    php5.6-xml \
    php5.6-curl \ 
    php5.6-gd  \
    php5.6-cli \ 
    php5.6-zip 




RUN add-apt-repository -y ppa:ondrej/apache2
RUN apt-get update  &&   apt-get -y install apache2 &&   a2enmod rewrite 

ADD php.ini /etc/php/5.6/apache2/php.ini
ADD 000-default.conf /etc/apache2/sites-enabled/000-default.conf


RUN php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
RUN php composer-setup.php
RUN php -r "unlink('composer-setup.php');"
RUN mv composer.phar /usr/local/bin/composer


ENTRYPOINT service apache2 start && bash
