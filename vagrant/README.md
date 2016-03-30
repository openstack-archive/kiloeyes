Note
======

Only tested on Vagrant 1.7.x + VirtualBox 4.3

It will install JDK8, ElasticSeach, Kafka, Virtualenv, and VirtualenvWrapper for you.

Usage
======

Create your own Vagrant config. file

```
  cp ubuntu-virtualbox.yml.sample ubuntu-virtualbox.yml
```

You can change VM memory, Kafka, or ElasticSearch package URL.

```
  vagrant up
```

Under /vagrant folder you can find kiloeyes project and Kafka uncompress folders.

Use below command to start ElasticSearch:

```
  sudo /etc/init.d/elasticsearch start
```
