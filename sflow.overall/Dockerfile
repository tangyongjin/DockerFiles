FROM ixp.sflowruntime
ENV DEBIAN_FRONTEND noninteractive

ADD sflow-to-rrd-handler  /usr/local/bin/
EXPOSE 5500
COPY supervisord.conf.sflowoverall /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord","-c","/etc/supervisor/conf.d/supervisord.conf"]
