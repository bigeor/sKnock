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

import time

from threading import Thread

from knock_server.decorators.synchronized import synchronized
from knock_server.definitions.Exceptions import *
from knock_server.definitions import Constants

class PortCloseThread(Thread):

    def __init__(self, runningOpenPortTasks, firewallHandler, ipVersion, protocol, port, addr):
        self.runningOpenPortTasks = runningOpenPortTasks
        self.firewallHandler = firewallHandler
        self.ipVersion = ipVersion
        self.protocol = protocol
        self.port = port
        self.addr = addr
        Thread.__init__(self)


    def run(self):
        threadTaskHash = hash(str(self.port) + str(self.ipVersion) + self.protocol + self.addr)

        try:
            time.sleep(Constants.PORT_OPEN_DURATION_IN_SECONDS)
            self.firewallHandler.closePortForClient(self.port, self.ipVersion, self.protocol, self.addr)

        except:
            return

        finally:
            self.runningOpenPortTasks.remove(threadTaskHash)