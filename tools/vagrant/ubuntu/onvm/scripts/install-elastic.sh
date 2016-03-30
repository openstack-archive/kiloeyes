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
  echo 'Download elasticsearch 2.2.x.deb and place it in tools/vagrant/ubuntu/leapbin directory.'
fi
