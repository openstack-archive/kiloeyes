===============================================================
Kiloeyes UI: Kiloeyes Extension for the OpenStack Dashboard (Horizon)
===============================================================

Kiloeyes UI is a Horizon Dashboard to monitor openstack metrics collected by Kiloeyes.
It uses the standard Horizon extension systems, and maintains code and styling
consistency where possible.

Most of the developer information, as well as an overview of Horizon, can be
found in the `Horizon documentation online`_.

.. _Horizon documentation online: http://docs.openstack.org/developer/horizon/index.html

Getting Started
===============

The quickest way to get up and running is:

  1. Setup a basic `Devstack installation`_
  2. Clone `Kiloeyes` with ``git clone https://github.com/openstack/kiloeyes``
  3. Open ``/horizon/``
  4. Run ``./tools/with_venv.sh pip install --upgrade <kiloeyes home>/kiloeyes/kiloeyes_horizon/dist/kiloeyes_horizon-0.0.1.tar.gz``.
  5. Copy ``<kiloeyes home>/kiloeyes/kiloeyes_horizon/enabled/_50_kiloeyes_ui.py`` to ``/horizon/openstack_dashboard/enabled``
  6. Copy and paste below configs to ``/horizon/openstack_dashboard/local/local_settings.py``
     	
	``KIBANA_HOST = "<IP Address of Kibana Host>"
  	  KIBANA_URL = "http://%s:5601" % KIBANA_HOST``

Building Documentation
======================

This documentation is written by contributors who wats to add new panel to the dashboard.
After adding the desired panels

  1. Add the panel name in ``/kiloeyes/kiloeyes_horizon/kiloeyes_ui/dashboard.py``
  2. Include the new panel template in ``/kiloeyes/kiloeyes_horizon/MANIFEST.in``
		example: ``recursive-include kiloeyes_ui/<new panel>/templates *`` 
  3. Run ``python Setup.py sdist``

  After this, Follow the steps in ``Getting Started``
