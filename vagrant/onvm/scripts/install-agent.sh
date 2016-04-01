#!/usr/bin/env bash
# $1 sys_password
# $2 public ip eth0

source /onvm/scripts/ini-config
eval $(parse_yaml '/onvm/conf/nodes.conf.yml' 'leap_')

# Install git in case it has not been installed.
apt-get update
apt-get -qqy install git python-dev python-pip

git clone https://github.com/openstack/monasca-agent.git /opt/monasca-agent

cd /opt/monasca-agent

# Make sure few required things installed first
pip install "requests>=2.9.1"
pip install "psutil>=3.4.2"
pip install -r requirements.txt

python setup.py install

echo 'Setting up agent by running monasca-setup...'
monasca-setup --username $leap_agent_user \
  --password $leap_agent_pw \
  --project_name kiloeyes \
  --system_only --keystone_url "${leap_auth_uri}/v3"

echo 'Configuring supervisor.conf file...'
iniset /etc/monasca/agent/supervisor.conf inet_http_server port 'localhost:9001'

rm -r -f /etc/monasca/agent/conf.d/vcenter.yaml

# The following section is to prepare for manual installation
#mkdir -p /etc/monasca/agent/conf.d
#
#cp agent.yaml.template /etc/monasca/agent/agent.yaml
#
# Get the plugin configuration files
#for key in cpu disk load memory network; do
#  cp conf.d/$key.yaml /etc/monasca/agent/conf.d
#done

service monasca-agent restart

echo 'Agent install is now complete!'

