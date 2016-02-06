Kiloeyes
========

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


Install an all-in-one kiloeyes clean ubuntu system
==================================================

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
         
    4. Try to create a topic and make sure things running all right:
    
         ./bin/kafka-topics.sh --create --topic test --zookeeper localhost:2181 --partitions 1 --replication-factor 1

Install Kiloeyes dependencies, server and services by following instructions above.
 