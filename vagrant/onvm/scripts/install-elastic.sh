#!/usr/bin/env bash
# $1 sys_password
# $2 public ip eth0

source /onvm/scripts/ini-config
eval $(parse_yaml '/onvm/conf/nodes.conf.yml' 'leap_')

# Java is required, install java first
source /onvm/scripts/install-java.sh

if [ -f /leapbin/elasticsearch-2.*.deb ];then
  dpkg -i /leapbin/elasticsearch-2.*.deb
  echo -e "network.host: $2" >> /etc/elasticsearch/elasticsearch.yml
  update-rc.d elasticsearch defaults
  service elasticsearch restart
  echo 'Elastic install is now complete!'
else
  echo 'Elasticsearch binary was not found!'
  echo 'Download elasticsearch and configure the location in nodes.conf.yml file.'
fi

if [ -f /leapbin/kibana-4.*-linux-x64.tar.gz ];then
  mkdir -p /opt/kibana
  tar -zxf /leapbin/kibana-4.*-linux-x64.tar.gz -C /opt/kibana
  mv /opt/kibana/* /opt/kibana/kibana
  echo -e 'elasticsearch.url: "http://'$2':9200"' >> /opt/kibana/kibana/config/kibana.yml

  # Start the kibana services
  start-stop-daemon --start --quiet --chuid root \
    --exec /opt/kibana/kibana/bin/kibana \
    --pidfile /opt/kibana/kibana.pid --make-pidfile --background >> /dev/null 2>&1

  echo 'Kibana install is now complete!'
else
  echo 'Kibana binary was not found!'
  echo 'Download kibana and  and configure the location in nodes.conf.yml file.'
fi
