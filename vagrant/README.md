Introduction
============
This subproject uses vagrant to setup kiloeyes. To make the install easier,
one should download java 8, elasticsearch, kibana and kafka binaries and place
these files into a directory named leapbin at the same directory where the
project kiloeyes is. Here is an example::

        leapbin
            elasticsearch-2.3.0.deb
            jdk-8u77-linux-x64.tar.gz
            kafka_2.11-0.9.0.0.tgz
            kibana-4.5.0-linux-x64.tar.gz
        kiloeyes
            etc
            kiloeyes
            vagrant
            ....

Having the structure like this will make the install goes faster. And when you
need to run the scripts repeatly, you won't need to keep downloading these
large files. The example directory leapbin above also lists the current
required software to run kiloeyes.


Usage:
======
You can install everything onto one machine or you can choose install different
components onto different servers. There can be a lot of ways to split up
servers for different services. Here is an example:

        controller:
            java
            elasticsearch
            kibana
            kiloeyes
        devstack:
            OpenStack environment
        agent01:
            agent

To indicate how the servers will be used, please edit configuration file in
vagrant/onvm/conf/nodes.conf.yml and ids.conf.yml file.