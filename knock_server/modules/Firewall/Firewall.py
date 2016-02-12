# Copyright (C) 2015-2016 Daniel Sel
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import datetime
import logging
import random
import string
import sys
from multiprocessing import Process, Pipe

import LinuxHelpers
import LinuxServiceWrapper
from knock_server.decorators.synchronized import synchronized
from knock_server.definitions import Constants
from knock_server.definitions.Exceptions import *
from knock_server.modules.Platform import PlatformUtils

LOG = logging.getLogger(__name__)

class Firewall:

    def __init__(self):
        self.platform = PlatformUtils.detectPlatform()

        if(self.platform == PlatformUtils.LINUX):
            self.linuxFirewallServicePipe, remotePipeEnd = Pipe()
            self.linuxFirewallService = Process(target=LinuxServiceWrapper.processFirewallCommands, args=((remotePipeEnd),))
            self.linuxFirewallService.daemon = True
            self.linuxFirewallService.start()
            self._executeTask(["startService"])

        self._setupDefaultFirewallState()
        self.openPortsList = list()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if(self.platform == PlatformUtils.LINUX):
            self.linuxFirewallServicePipe.send(["stopService"])
            self.linuxFirewallServicePipe.close()
            self.linuxFirewallService.join()

    def _setupEmergencyAccessFirewallRules(self):
        if(self.platform == PlatformUtils.LINUX):
            LinuxHelpers.insertEmergencySSHAccessRule()

    def _setupDefaultFirewallState(self):
        if(self.platform == PlatformUtils.LINUX):
            LinuxHelpers.setupIPTablesPortKnockingChainAndRedirectTraffic()

        self._setupEmergencyAccessFirewallRules()


    def openPortForClient(self, port, ipVersion, protocol, addr):

        openPort = hash(str(port) + str(ipVersion) + protocol + addr)
        if openPort in self.openPortsList:
            LOG.info('%s Port: %s for host: %s is already open!', protocol, port, addr)
            raise PortAlreadyOpenException

        if(self.platform == PlatformUtils.LINUX):
            self._executeTask(['openPort', port, ipVersion, protocol, addr])

        self.openPortsList.append(openPort)
        LOG.info('%s Port: %s opened for host: %s from: %s until: %s',
                    protocol, port, addr,
                    datetime.datetime.now(),
                    datetime.datetime.now() +
                    datetime.timedelta(0, Constants.PORT_OPEN_DURATION_IN_SECONDS))



    def closePortForClient(self, port, ipVersion, protocol, addr):
        if(self.platform == PlatformUtils.LINUX):
            self.linuxFirewallServicePipe.send(['closePort', port, ipVersion, protocol, addr])

        self.openPortsList.remove(hash(str(port) + str(ipVersion) + protocol + addr))
        LOG.info('%s Port: %s closed for host: %s at: %s', protocol, port, addr, datetime.datetime.now())


    @synchronized
    def _executeTask(self, msg):
        taskId = Firewall._generateRandomTaskId()
        taskMsg = [taskId]
        taskMsg.extend(msg)

        self.linuxFirewallServicePipe.send(taskMsg)
        if self.linuxFirewallServicePipe.recv() != taskId:
            Firewall._crashRaceCondition()


    @staticmethod
    def _generateRandomTaskId():
        return ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])

    @staticmethod
    def _crashRaceCondition():
        LOG.error("Tasks executed in wrong order - possible race condition or vulnerability!")
        sys.exit("Tasks executed in wrong order - possible race condition or vulnerability!")