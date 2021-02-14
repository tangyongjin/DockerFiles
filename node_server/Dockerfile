FROM ubuntu:14.04

ADD sources.list  /etc/apt/sources.list


RUN rm /bin/sh && ln -s /bin/bash /bin/sh

RUN apt-get update \
    && apt-get install -y curl \
    && apt-get -y autoclean

ENV NVM_DIR /usr/local/nvm
ENV NODE_VERSION  8.9.4

RUN curl --silent -o- https://raw.githubusercontent.com/creationix/nvm/v0.31.2/install.sh | bash

RUN source $NVM_DIR/nvm.sh \
    && NVM_NODEJS_ORG_MIRROR=https://npm.taobao.org/mirrors/node nvm install 8.9.4 \
    && nvm alias default $NODE_VERSION \
    && nvm use default

ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH


############# install apache2 #################
RUN echo "Asia/Chongqing" > /etc/timezone
RUN sudo dpkg-reconfigure -f noninteractive tzdata


RUN mkdir -p /var/lock/apache2 /var/run/apache2

RUN apt-get -qq update && apt-get install -y \
  apache2 \
  vim  \
  unzip \
  php5  \
  php5-mysql \
  php5-dev \
  php5-mcrypt \
  php5-curl \
  mcrypt \
  php5-gd \
  php5-memcache \
  php5-pspell \
  php5-snmp \
  snmp \
  php5-xmlrpc \
  libapache2-mod-php5 \
  php5-cli  \
  fontconfig


RUN sudo php5enmod mcrypt
RUN a2enmod rewrite
RUN a2enmod proxy_http






#### set chinese font ####
RUN mkdir -p /usr/local/share/fonts/truetype/simhei  && mkdir -p /var/www/.ssh
COPY chinese.simhei.ttf  /usr/local/share/fonts/truetype/simhei/chinese.simhei.ttf
RUN  chown root  /usr/local/share/fonts/truetype/simhei/chinese.simhei.ttf &&  fc-cache -f -v


############# setup  two hosts for apache ######
RUN sed -i  '/<Directory \/var\/www\/>/,/<\/Directory>/ s/AllowOverride None/AllowOverride all/' /etc/apache2/apache2.conf
ADD 000-default.conf  /etc/apache2/sites-available/
ADD 001-default.conf  /etc/apache2/sites-available/
ADD ports.conf  /etc/apache2/
COPY lamp/php.ini /etc/php5/apache2/php.ini
WORKDIR  /site


RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list


RUN apt-get install  -y apt-transport-https
RUN sudo apt-get update && sudo apt-get install -y  yarn
EXPOSE 2200

ENTRYPOINT  a2ensite 001-default && service apache2 start &&    npm run dev &&  bash

