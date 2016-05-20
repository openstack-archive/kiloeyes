$$$
Kiloeyes
========
shengping

Kiloeyes is a monitoring software allowing you to collect data from any compute
systems.

Install Prerequisites
=====================

Kiloeyes python implementation install process installs Kiloeyes and most of its
dependencies automatically. However some components cannot be installed automatically
by python setup tools, they will have to be installed manually. These components are
python setup tools, python-dev, python-pip and gunicorn. Follow the steps below to
install dependencies:

Install python setuptools::

    wget https://bootstrap.pypa.io/ez_setup.py -O - | sudo python

Install python-dev, pip and pastedeploy, run the following command:

    sudo apt-get install python-dev python-pip python-pastedeploy

Kiloeyes depends on Kafka and ElasticSearch, both requires Java. At the end of
this document in the all-in-one section, you can find detailed instructions on
how to install each of them. Please refer to respective document on how to
install Java, Kafka and ElasticSearch if you want to know more::

    http://www.java.com
    http://kafka.apache.org/documentation.html#introduction
    https://www.elastic.co/products/elasticsearch

Use vagrant to setup kiloeyes and agent
=======================================
A vagrant sub project has been created in vagrant directory to allow users to
setup kiloeyes and agent very easily if couple of clean machines are setup.
[Read more on how to use the sub project](vagrant/README.md)

Install Kiloeyes
================
Get the source code::

    git clone https://github.com/openstack/kiloeyes.git

Go to the root directory of the project and run the following command:

    sudo pip install -r requirements.txt
    sudo python setup.py install

Create a log directory::

    sudo mkdir -p /var/log/kiloeyes

If Kiloeyes installs successfully, you can then make changes to the following
two files to reflect your system settings, such as Kafka server locations::

    /etc/kiloeyes/kiloeyes.ini
    /etc/kiloeyes/kiloeyes.conf

Once the configurations are modified to match your environment, you can start
up various services by following these instructions.

To start the API server, run the following command:

    Run the server in foreground mode
    gunicorn -k eventlet --worker-connections=2000 --backlog=1000
             --paste /etc/kiloeyes/kiloeyes.ini

    Run the server as daemons
    gunicorn -k eventlet --worker-connections=2000 --backlog=1000
             --paste /etc/kiloeyes/kiloeyes.ini -D

To start a Kiloeyes micro service servers, run the following command:

    kiloeyes-service --config-file /etc/kiloeyes/xxxx.conf

    where xxxx.conf should be a micro service specific configuration file.
    Currently the following services are available:

    Metrics persister service:
    kiloeyes-service --config-file /etc/kiloeyes/metrics-persister.conf

    Alarm persister service:
    kiloeyes-service --config-file /etc/kiloeyes/alarms-persister.conf

    Notification service:
    kiloeyes-service --config-file /etc/kiloeyes/kiloeyes-notification-engine.conf

    Threshold service:
    kiloeyes-service --config-file /etc/kiloeyes/kiloeyes-threshold-engine.conf

In the future, there might be other services such as threshold engine,
anomaly detection, alarms etc. All these services should be able to take
a specific configuration file to be launched. Here are the examples:

    kiloeyes-service --config-file /etc/kiloeyes/kiloeyes-anomaly.conf

If you are developing kiloeyes, and would like to run all the services in one
screen and use default configurations, then you can simply run the following
command from kiloeyes root direction:

    screen -c kiloeyes


Kiloeyes Integration with OpenStack Horizon
===========================================
To integrate with Horizon, two projects (monasca-ui and python-monascaclient)
have to be installed. The steps on how to install these two projects can be
found here::

    https://github.com/stackforge/monasca-ui
    https://github.com/stackforge/python-monascaclient

Once both projects are installed, some configurations are needed:

    Copy _60_monitoring.py to Horizon openstack_dashboard/local/enabled directory

    Run the following command to create service and endpoint

    setup_horizon.sh


Kiloeyes Development
====================
To check if the code follows python coding style, run the following command
from the root directory of this project

    ./run_tests.sh -p

To run all the unit test cases, run the following command from the root
directory of this project

    ./run_tests.sh

To see the unit test case coverage, run the following command from the root
directory of the project

    ./run_tests.sh -c

If the command runs successfully, a set of files will be created in the root
directory named covhtml. Open up the index.html from a browser to see the summary
of the unit test coverage and the details.


Install an all-in-one kiloeyes onto a clean ubuntu system
=========================================================

Install java 8::

    sudo add-apt-repository ppa:webupd8team/java
    sudo apt-get update
    sudo apt-get install oracle-java8-installer

Install ElasticSearch 2.2::

    1. Download elasticsearch 2.2.0 deb file
    2. Install the package by running the following command:

         dpkg -i elasticsearch-2.2.0.deb

    3. Edit /etc/elasticsearch/elasticsearch.yml file to make sure that the
       network host looks something like this:

         network.host: 192.168.1.144

    4. Run the following command to make sure the service starts after reboot:

         update-rc.d elasticsearch defaults  (to automatically starts)
         update-rc.d -f elastic search remove  (not to automatically starts)

    5. Check if ElasticSearch is running ok, by point your browser to this url:

         http://192.168.1.144:9200/?pretty

Install Kafka 0.9.0.0 scala 2.11 build::

    1. Download kafka 0.9.0.0 from this link:

         https://www.apache.org/dyn/closer.cgi?path=/kafka/0.9.0.0/kafka_2.11-0.9.0.0.tgz

    2. Unzip the tgz file into a directory:

         tar xf kafka_2.11-0.9.0.0.tgz

    3. Change to the kafka directory and start up zookeeper and kafka server:

         ./bin/zookeeper-server-start.sh ./config/zookeeper.properties
         ./bin/kafka-server-start.sh ./config/server.properties 

    4. Try to create a topic and make sure things running ok:

         ./bin/kafka-topics.sh --create --topic test --zookeeper localhost:2181 --partitions 1 --replication-factor 1

Install Kiloeyes dependencies, server and services by following instructions above.


Register kiloeyes as monitoring service with Keystone::
=======================================================
1. On the keystone server, setup environment variable::

        export OS_USERNAME=admin
        export OS_PASSWORD=<password>
        export OS_TENANT_NAME=admin
        export OS_AUTH_URL=http://localhost:5000/v3
        export OS_IDENTITY_API_VERSION=3

2. Create monitoring service by running the following command::

    openstack service create --name kiloeyes --description "Monitoring" monitoring

3. Create endpoint by running the following command::

    openstack endpoint create --region RegionOne monitoring public http://<<kiloeyes_server_host_ip>>:9090/v2.0


Install monasca-agent from the source::
=======================================
1. Get the source code::

        git clone https://github.com/openstack/monasca-agent.git

2. Install the requirements::

        sudo apt-get install python-dev python-pip
        pip install "requests>=2.9.1"
        pip install "psutil>=3.4.2"
        sudo pip install -r requirements.txt

3. Install monasca agents::

        sudo python setup.py install

4. Run the following command to create agent configurations::

        sudo monasca-setup --username KEYSTONE_USERNAME --password KEYSTONE_PASSWORD --project_name KEYSTONE_PROJECT_NAME --keystone_url http://URL_OF_KEYSTONE_API:5000/v3

    Replace KEYSTONE_USERNAME, KEYSTONE_PASSWORD, KEYSTONE_PROJECT_NAME,
    URL_OF_KEYSTONE_API with correct value according to your openstack
    keystone setups

5. If the above runs with no errors, you need to add the following in
/etc/monasca/agent/supervisor.conf file::

        [inet_http_server]
        port = localhost:9001

6. Check configuration file at /etc/monasca/agent/agent.yml, the content
should look like the following::

        keystone_url: http://192.168.15.5:5000/v3
        username: <<id to use to post data>>
        password: <<user password>>
        project_name: <<kiloeyes project name>>
        url: null

    You can create a user in keystone for agent. Make sure that the user is
    in the project named service.

7. Restart monasca agent services on the machine by running the following command::

        sudo service monasca-agent restart

8. Agent log files will be in /var/log/monasca/agent directory.


Enable keystone middleware for security
=======================================
To enable keystone middleware for security, the following configurations need
to be done.

1. Install keystone middleware::

        apt-get update
        apt-get -qqy install git python-dev python-pip
        pip install keystonemiddleware

2. Edit /etc/kiloeyes/kiloeyes.ini file to insert the middleware in the pipeline::

        [pipeline:main]
        #pipeline = api
        pipeline = authtoken api

        [filter:authtoken]
        paste.filter_factory = keystonemiddleware.auth_token:filter_factory
        delay_auth_decision = false
3. Edit /etc/kiloeyes/kiloeyes.conf file to configure the middleware,The
   following configuration assumes that the user, password, project and keystone
   server IP are all already available. If not, use keystone commands to create
   them. If you are using devstack, you can use demo project, demo id and its
   password for the configuration.

        [keystone_authtoken]
        password = <<demo-password>>
        username = demo
        user_domain_id = default
        project_name = demo
        project_domain_id = default
        auth_type = password
        auth_url = http://<<keystone_ip>>:5000
        auth_uri = http://<<keystone_ip>>:5000

4. Restart kiloeyes api server::

        gunicorn --debug -k eventlet --worker-connections=20 --backlog=10
            --paste /etc/kiloeyes/kiloeyes.ini
