# Copyright 2015 Carnegie Mellon University
#
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

import email.mime.text
import mock
from oslo_log import log
import smtplib

from kiloeyes.common import email_sender
from kiloeyes import tests

LOG = log.getLogger(__name__)


class TestEmailSender(tests.BaseTestCase):
    content = "Mocked Mail Content"

    def setUp(self):
        super(TestEmailSender, self).setUp()

    def testEmailSender_Success(self):
        with mock.patch.object(smtplib.SMTP,
                               "set_debuglevel",
                               return_value=True):
            with mock.patch.object(smtplib.SMTP,
                                   "connect",
                                   return_value=True):
                with mock.patch.object(smtplib.SMTP,
                                       "starttls",
                                       return_value=True):
                    with mock.patch.object(smtplib.SMTP,
                                           "login",
                                           return_value=True):
                        with mock.patch.object(smtplib.SMTP,
                                               "sendmail",
                                               return_value=True):
                            with mock.patch.object(email.mime.text,
                                                   "MIMEText",
                                                   return_value=(
                                                       email.mime.text.
                                                       MIMEText(
                                                           self.content))):
                                with mock.patch.object(smtplib.SMTP,
                                                       "quit",
                                                       return_value=True):
                                    ret = (email_sender.EmailSender().
                                           send_emails(
                                               ["hanc@andrew.cmu.edu", ],
                                               "Mocked email subject",
                                               "Mocked email content"))
                                    self.assertEqual(ret, True)

    def testEmailSender_Failure(self):
        with mock.patch.object(smtplib.SMTP,
                               "set_debuglevel",
                               return_value=True):
            with mock.patch.object(smtplib.SMTP,
                                   "connect",
                                   return_value=True):
                with mock.patch.object(smtplib.SMTP,
                                       "starttls",
                                       return_value=True):
                    with mock.patch.object(smtplib.SMTP,
                                           "login",
                                           return_value=True):
                        with mock.patch.object(smtplib.SMTP,
                                               "sendmail",
                                               return_value=True,
                                               side_effect=Exception(
                                                   'Mock_Exception')):
                            with mock.patch.object(email.mime.text,
                                                   "MIMEText",
                                                   return_value=(
                                                       email.mime.text.
                                                       MIMEText(
                                                           self.content))):
                                with mock.patch.object(smtplib.SMTP,
                                                       "quit",
                                                       return_value=True):
                                    ret = (email_sender.EmailSender().
                                           send_emails(
                                               ["hanc@andrew.cmu.edu", ],
                                               "Mocked email subject",
                                               "Mocked email content"))
                                    self.assertEqual(ret, False)
