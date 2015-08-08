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
from oslo_config import cfg
import smtplib

from oslo_log import log

MAILSENDER_OPTS = [
    cfg.StrOpt('username',
               default='kiloeyes.notification@gmail.com',
               help='The email account user name.'),
    cfg.StrOpt('password',
               default='password',
               help='The email account user password.'),
    cfg.StrOpt('smtp_host', default='smtp.gmail.com',
               help='The email service host.'),
    cfg.IntOpt('port', default=25,
               help='The email service port.'),
    cfg.BoolOpt('use_tls', default=True,
                help='Set to True if the service uses TLS.'),

]

cfg.CONF.register_opts(MAILSENDER_OPTS, group="mailsender")

LOG = log.getLogger(__name__)


class EmailSender(object):

    def __init__(self):
        self.username = cfg.CONF.mailsender.username
        self.password = cfg.CONF.mailsender.password
        self.smtp_host = cfg.CONF.mailsender.smtp_host
        self.port = cfg.CONF.mailsender.port
        self.use_tls = cfg.CONF.mailsender.use_tls
        self.from_addr = self.username

        self.smtp = smtplib.SMTP()

        LOG.debug('connecting ...')

        # connect
        try:
            self.smtp.connect(self.smtp_host, self.port)
        except Exception:
            LOG.debug('SMTP Connection error.')

        if self.use_tls:
            self.smtp.starttls()
        # login with username & password
        try:
            LOG.debug('Login ...')
            self.smtp.login(self.username, self.password)
        except Exception:
            LOG.debug('Login exception.')

    def reset(self):
        self.__init__()

    def send_emails(self, to_addrs, subject, content):
        # fill content with MIMEText's object
        msg = email.mime.text.MIMEText(content)
        msg['From'] = self.from_addr
        msg['To'] = ';'.join(to_addrs)
        msg['Subject'] = subject
        try:
            self.smtp.sendmail(self.from_addr, to_addrs, msg.as_string())
            LOG.debug('Mail sent to: %s' % str(to_addrs))
            return True
        except Exception as e:
            LOG.debug('Mail sent Exception: %s, reset the sender.' % str(e))
            self.reset()
            return False
