FROM ixp.sflowruntime
ENV DEBIAN_FRONTEND noninteractive

ADD sflow-ip2ip-handler   /usr/local/bin/
EXPOSE 5502
COPY supervisord.conf.sflowip2ip /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord","-c","/etc/supervisor/conf.d/supervisord.conf"]
