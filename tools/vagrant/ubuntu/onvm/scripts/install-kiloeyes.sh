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

# Config the kiloeyes

echo 'Kiloeyes install is now complete!'

