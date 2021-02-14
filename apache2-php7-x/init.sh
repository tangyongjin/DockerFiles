#!/bin/bash
rm -r /var/run/apache2/apache2.pid
cd /etc/apache2/sites-available &&  a2ensite * && service apache2 restart &&   bash
