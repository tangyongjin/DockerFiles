FROM ubuntu:14.04
MAINTAINER Nicholas Istre <nicholas.istre@e-hps.com>

# Setup environment
ENV DEBIAN_FRONTEND noninteractive

# Update sources


ADD sources.list  /etc/apt/sources.list
RUN apt-get update -y


#insatall base
RUN apt-get install -y php5 php5-mysql php5-dev php5-gd php5-memcache php5-pspell php5-snmp snmp php5-xmlrpc libapache2-mod-php5 php5-cli
RUN apt-get install -y apache2 vim bash-completion unzip openssh-server openssh-client passwd memcached
RUN apt-get install -y libconfig-general-perl libdaemon-control-perl libnetaddr-ip-perl libnetpacket-perl libnet-snmp-perl mrtg librrds-perl libtemplate-perl
RUN apt-get install -y mysql-client mysql-server cron  rsyslog supervisor libcurl3-gnutls liberror-perl rsync git rrdtool


# install http
RUN mkdir -p /var/lock/apache2 /var/run/apache2 /var/log/supervisor /var/run/sshd /software /software/sflowtool /data/log/mysql /opt/logs /data/mrtg /data/mrtg/members /etc/mrtg

COPY apache2.conf /etc/apache2/apache2.conf



RUN sed -ri 's/PermitRootLogin without-password/PermitRootLogin yes/g' /etc/ssh/sshd_config
RUN echo 'root:changeme' | chpasswd
RUN mkdir -p /root/.ssh && touch /root/.ssh/authorized_keys && chmod 700 /root/.ssh



############## For ixp ###########

WORKDIR /software 
RUN git clone  https://github.com/sflow/sflowtool.git /software/sflowtool
WORKDIR /software/sflowtool
RUN ./boot.sh && ./configure && make && make install

ADD ixp.tar /opt
ADD ixp2.sql /software
ADD mysqlremotelogin.sql /software
ADD fix.sql /software
ADD my.cnf /etc/mysql/my.cnf
ADD php.ini /etc/php5/apache2/php.ini  
ADD 000-default.conf  /etc/apache2/sites-enabled/000-default.conf
COPY apache2.conf /etc/apache2/apache2.conf
RUN a2enmod rewrite && mkdir -p ~/.cpan/CPAN
ADD MyConfig.pm /root/.cpan/CPAN/MyConfig.pm
ADD composer.phar /usr/bin/
ADD ixpmanager.conf /usr/local/etc
RUN cpan Crypt::DES Crypt::Rijndael Digest::SHA1 &&  cd /opt/ixpmanager && /usr/bin/composer.phar  config  repo.packagist composer https://packagist.phpcomposer.com   


WORKDIR /opt/ixpmanager
RUN  /usr/bin/composer.phar update -vvv && chown -R www-data:www-data  /opt/ixpmanager/var
ADD application.ini  /opt/ixpmanager/application/configs/application.ini
ADD  ixpmanager.conf /etc
WORKDIR /opt/ixpmanager/tools/perl-lib/IXPManager
RUN perl Makefile.PL && make install

EXPOSE 22  443 3306  6343 11211

### set mrtg ###

ADD htaccess /opt/ixpmanager/public/.htaccess
ADD ubuntu-mrtg-initd /etc/init.d/mrtg
ADD ixp-periodic-update.sh /usr/local/bin/ixp-periodic-update.sh
ADD update-l2database.pl /opt/ixpmanager/tools/runtime/l2database/update-l2database.pl

### ixp contab ###

RUN service rsyslog restart
ADD ixp-cron /etc/cron.d/ixp-cron
RUN chmod 0644 /etc/cron.d/ixp-cron &&  touch /var/log/cron.log 

RUN service mysql start  && mysql -uroot --password=''</software/ixp2.sql  && mysql -uroot --password=''</software/mysqlremotelogin.sql &&   mysql -uroot --password=''</software/fix.sql
RUN service apache2 start && service memcached start && service mysql start && /opt/ixpmanager/bin/ixptool.php -a statistics-cli.gen-mrtg-conf 
RUN service apache2 stop && echo 'export PS1="[\u@ixp] \W#"' >> /root/.bashrc
COPY supervisord.conf /etc/supervisord.conf
CMD ["/usr/bin/supervisord"]
