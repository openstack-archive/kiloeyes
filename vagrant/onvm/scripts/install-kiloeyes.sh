#!/usr/bin/env bash
# $1 sys_password
# $2 public ip eth0

source /onvm/scripts/ini-config
eval $(parse_yaml '/onvm/conf/nodes.conf.yml' 'leap_')

wget https://bootstrap.pypa.io/ez_setup.py -O - | python
apt-get update
apt-get -qqy install git python-dev python-pip python-pastedeploy

cd /opt/kiloeyes
pip install -r requirements.txt
python setup.py install

echo 'Finding IP addresses...'
eval node_ip=\$leap_${leap_logical2physical_kafka}_eth0; node_ip=`echo $node_ip`
kafka_ip=$node_ip
eval node_ip=\$leap_${leap_logical2physical_elastic}_eth0; node_ip=`echo $node_ip`
elastic_ip=$node_ip


k_log_dir='/var/log/kiloeyes'
k_pid_dir='/var/run/kiloeyes'
mkdir -p $k_log_dir $k_pid_dir

# Config the kiloeyes
echo 'Config /etc/kiloeyes/kiloeyes.conf file...'
iniset /etc/kiloeyes/kiloeyes.conf DEFAULT log_dir $k_log_dir
iniset /etc/kiloeyes/kiloeyes.conf kafka_opts uri $kafka_ip:9092
iniset /etc/kiloeyes/kiloeyes.conf es_conn uri http://$elastic_ip:9200

echo 'Config /etc/kiloeyes/metrics-persister.conf...'
iniset /etc/kiloeyes/metrics-persister.conf DEFAULT log_dir $k_log_dir
iniset /etc/kiloeyes/metrics-persister.conf kafka_opts uri $kafka_ip:9092
iniset /etc/kiloeyes/metrics-persister.conf es_conn uri http://$elastic_ip:9200

echo 'Config /etc/kiloeyes/alarms-persister.conf...'
iniset /etc/kiloeyes/alarms-persister.conf DEFAULT log_dir $k_log_dir
iniset /etc/kiloeyes/alarms-persister.conf kafka_opts uri $kafka_ip:9092
iniset /etc/kiloeyes/alarms-persister.conf es_conn uri http://$elastic_ip:9200

echo 'Config /etc/kiloeyes/kiloeyes-notification-engine.conf...'
iniset /etc/kiloeyes/kiloeyes-notification-engine.conf DEFAULT log_dir $k_log_dir
iniset /etc/kiloeyes/kiloeyes-notification-engine.conf kafka_opts uri $kafka_ip:9092
iniset /etc/kiloeyes/kiloeyes-notification-engine.conf es_conn uri http://$elastic_ip:9200

echo 'Config /etc/kiloeyes/kiloeyes-threshold-engine.conf...'
iniset /etc/kiloeyes/kiloeyes-threshold-engine.conf DEFAULT log_dir $k_log_dir
iniset /etc/kiloeyes/kiloeyes-threshold-engine.conf kafka_opts uri $kafka_ip:9092
iniset /etc/kiloeyes/kiloeyes-threshold-engine.conf es_conn uri http://$elastic_ip:9200

echo 'Start all kiloeyes services...'

gunicorn -k eventlet --worker-connections=20 --backlog=10 --paste /etc/kiloeyes/kiloeyes.ini -D

start-stop-daemon --start --quiet --chuid root --exec /usr/local/bin/kiloeyes-service \
  --pidfile $k_pid_dir/metrics-persister.pid --make-pidfile --background \
  -- --config-file /etc/kiloeyes/metrics-persister.conf >> /dev/null 2>&1

start-stop-daemon --start --quiet --chuid root --exec /usr/local/bin/kiloeyes-service \
  --pidfile $k_pid_dir/alarms-persister.pid --make-pidfile --background \
  -- --config-file /etc/kiloeyes/alarms-persister.conf >> /dev/null 2>&1

start-stop-daemon --start --quiet --chuid root --exec /usr/local/bin/kiloeyes-service \
  --pidfile $k_pid_dir/kiloeyes-notification-engine.pid --make-pidfile --background \
  -- --config-file /etc/kiloeyes/kiloeyes-notification-engine.conf >> /dev/null 2>&1

start-stop-daemon --start --quiet --chuid root --exec /usr/local/bin/kiloeyes-service \
  --pidfile $k_pid_dir/kiloeyes-threshold-engine.pid --make-pidfile --background \
  -- --config-file /etc/kiloeyes/kiloeyes-threshold-engine.conf >> /dev/null 2>&1

echo 'Kiloeyes install is now complete!'

