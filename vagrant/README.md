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
components onto different servers. Currently python-keystonemiddleware which
is used by kiloeyes for security, but its dependencies conflict with agent
dependcies, so kiloeyes currently can not co-exist with agent on a signle
machine. It is best to have kiloeyes and agent installed onto the separate
machines to avoid the installation headaches. This vagrant project uses
configuration files in directory vagrant/onvm/conf. File nodes.conf.yml is
used to configure how many nodes to install various components, ids.conf.yml
file is used to save credentials.

Here is an example::

    controller:
        host_name: controller.leap.dev
        eth0: 192.168.1.90

    agent01:
        host_name: agent01.leap.dev
        eth0: 192.168.1.88

    logical2physical:
        kiloeyes: controller
        elastic: controller
        kafka: controller

    ctlnodes:
        - elastic
        - kafka
        - kiloeyes

    agentes:
        - agent01


Above configuration, indicates that there are total of 4 logical nodes, they
are elastic, kafka, kiloeyes and agent01. The installation sequence is in
order of elastic, kafka, kiloeyes and agent01, the ctlnodes section indicates
that sequence, ctlnodes will be always installed before agent nodes. The
section logical2physical node indicates how a logical node maps to a physical
machine, in the above example, 3 logical nodes (elastic, kafka and kiloeyes)
are all mapped to a physical node called controller, which gets defined by its
ip address and a name. agent01 is also defined by using its ip and name. From
this setup, you can install elastic, kafka and kiloeyes onto different
machines.

Since the agent was specifically developed to work with openstack security,
without openstack running somewhere, it will be pretty pointless to setup
agent. The best way to set the whole thing up, is to following the following
steps::

1. Prepare 3 machines, either physical or virtual machines should work fine.
2. Install DevStack onto the first machine and configure the keystone url and
   userid and password in nodes.conf.yml file. If you already have a OpenStack
   system running, you can use that system as well, simply configure 
   nodes.conf.yml file using the right keystone auth url and credentials.
3. Find out the second and third machine IPs and fill the IPs in the
   nodes.conf.yml file, use the second machine for controller and the third
   for agent.
4. Make sure that you have the same password for the root user for the second
   and third machine. Place the user name and password in file ids.conf.yml.
   Also make sure that the server has ssh turned on so that vagrant can run
   successfully.
5  Kiloeyes depend on java, elastic search and kafka. This vagrant project will
   install these components onto the machine you specified in the conf file,
   but you will have to download these binaries into a directory which will be
   located in the same directory kiloeyes root resides. The structure is indicated
   above in introduction section.
6. Change to vagrant directory and now run the following two commands::

        vagrant up
        vagrant provision
7. If all goes well, you should have everything running successfully, after
   awhile, agent should be sending messages to kiloeyes and the data should be
   available in elasticsearch and can be seen by using kibana::

        http://192.168.1.90:5601