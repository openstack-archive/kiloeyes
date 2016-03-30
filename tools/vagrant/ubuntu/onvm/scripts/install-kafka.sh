#!/usr/bin/env bash
# $1 sys_password
# $2 public ip eth0

source /onvm/scripts/ini-config
eval $(parse_yaml '/onvm/conf/nodes.conf.yml' 'leap_')

if [ -f /leapbin/kafka_*-0.9.0.0.tgz ]; then
  tar -zxf /leapbin/kafka_*-0.9.0.0.tgz -C /opt
  mv /opt/kafka_*-0.9.0.0 /opt/kafka_0.9.0.0

  /opt/kafka_0.9.0.0/bin/zookeeper-server-start.sh -daemon /opt/kafka_0.9.0.0/config/zookeeper.properties
  sleep 2

  /opt/kafka_0.9.0.0/bin/kafka-server-start.sh -daemon /opt/kafka_0.9.0.0/config/server.properties 

  echo 'Kafka install is now complete!'
else
  echo 'Kafka binary was not found!'
fi

