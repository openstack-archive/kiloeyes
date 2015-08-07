#!/usr/bin/env python
#
# Copyright 2013 IBM Corp
##
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
# The name of the dashboard to be added to HORIZON['dashboards']. Required.
DASHBOARD = "monitoring"

# A list of applications to be added to INSTALLED_APPS.
ADD_INSTALLED_APPS = ['monitoring']

# A list of angular modules to be added as dependencies to horizon app.
ADD_ANGULAR_MODULES = ['monitoringApp']

# A list of javascript files to be included for all pages
ADD_JS_FILES = ['monitoring/js/app.js',
                'monitoring/js/controllers.js',
                'monitoring/js/ng-tags-input.js']

from monascaclient import exc
# A dictionary of exception classes to be added to HORIZON['exceptions'].
ADD_EXCEPTIONS = {
    'recoverable': (exc.HTTPUnProcessable, exc.HTTPConflict,
                    exc.HTTPException),
    'not_found': (exc.HTTPNotFound,),
    'unauthorized': (exc.HTTPUnauthorized,),
}

# If set to True, this dashboard will not be added to the settings.
DISABLED = False
