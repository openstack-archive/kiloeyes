Kiloeyes
=======

Kiloeyes is a monitoring software allowing you to collect data from any compute
systems.

Install Prerequisites
=====================

Kiloeyes python implementation install process installs Kiloeyes and most of its
dependencies automatically. However some components cannot be installed automatically
by python setup tools, they will have to be installed manually. These components are
python setup tools, python-dev, python-pip and gunicorn. Follow the steps below to
install dependencies:

The typical process of installing setup tools is to download the tar.gz file
then tar -xvf and run python setup.py install, you can also reference this page:

    https://pypi.python.org/pypi/setuptools

To install python-dev and pip, run the following command:

    sudo apt-get install python-dev python-pip

To install gunicorn, run the following command:

    sudo pip install gunicorn==19.1.0
    
Kiloeyes depends on Kafka and ElasticSearch, both requires Java. If you do not
already have Java, Kafka and ElasticSearch running, you will have to install
them. Please refer to respective document on how to install Java, Kafka and
ElasticSearch::

    http://www.java.com
    http://kafka.apache.org/documentation.html#introduction
    https://www.elastic.co/products/elasticsearch

Install Kiloeyes
===============
Get the source code::

    git clone https://github.com/openstack/kiloeyes.git

Go to the root directory of the project and run the following command:

    sudo python setup.py install

If Kiloeyes installs successfully, you can then make changes to the following
two files to reflect your system settings, such as Kafka server locations::

    /etc/kiloeyes/kiloeyes.ini
    /etc/kiloeyes/kiloeyes.conf

Once the configurations are modified to match your environment, you can start
up various services by following these instructions.

To start the API server, run the following command:

    Running the server in foreground mode
    gunicorn -k eventlet --worker-connections=2000 --backlog=1000
             --paste /etc/kiloeyes/kiloeyes.ini

    Running the server as daemons
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
==========================================
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
===================
To check if the code follows python coding style, run the following command
from the root directory of this project

    ./run_tests.sh -p

To run all the unit test cases, run the following command from the root
directory of this project

    ./run_tests.sh

To see the unit test case coverage, run the following command from the root
directory of the project

    ./run_tests.sh -c

If the command runs successfully, then set of files will be created in the root
directory named covhtml. Open up the index.html from a browser to see the summary
of the unit test coverage and the details.