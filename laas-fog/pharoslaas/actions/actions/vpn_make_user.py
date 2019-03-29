##############################################################################
# Copyright 2017 Parker Berberian and Others                                 #
#                                                                            #
# Licensed under the Apache License, Version 2.0 (the "License");            #
# you may not use this file except in compliance with the License.           #
# You may obtain a copy of the License at                                    #
#                                                                            #
#    http://www.apache.org/licenses/LICENSE-2.0                              #
#                                                                            #
# Unless required by applicable law or agreed to in writing, software        #
# distributed under the License is distributed on an "AS IS" BASIS,          #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.   #
# See the License for the specific language governing permissions and        #
# limitations under the License.                                             #
##############################################################################

import datetime
from vpnAction import VPNAction
import json


class Make_VPN_User(VPNAction):

    def __init__(self, config=None):
        super(Make_VPN_User, self).__init__(config=config)

    def run(self, booking=None, user=None, passwd=None, job_id=None):
        if user == "None":
            user = None
        if passwd == "None":
            passwd = None
        name, passwd, dn = self.makeNewUser(name=user, passwd=passwd)
        vpn_info = {}
        vpn_info['dn'] = dn
        vpn_info['username'] = name
        vpn_info['password'] = passwd
        now = datetime.date.today()
        vpn_info['created'] = now.isoformat()  # 'YYYY-MM-DD' today
        self.action_service.set_value(
                name='vpn_'+name,
                value=json.dumps(vpn_info),
                local=False,
                encrypt=True
                )
        if booking is not None and booking is not "None":
            self.addUserToBooking(vpn_info, booking)

        if job_id is not None and job_id is not "None":
            self.addUserToJob(vpn_info, job_id)

        return "vpn_" + name

    def addUserToBooking(self, vpn_info, booking):
        name = "booking_" + str(booking)
        booking = json.loads(
                self.action_service.get_value(
                    name=name,
                    local=False
                    )
                )
        vpn_key = "vpn_" + vpn_info['username']
        if "vpn_key" not in booking.keys():
            booking['vpn_key'] = "vpn_" + vpn_info['username']
        else:
            if "additional_vpn_users" not in booking.keys():
                booking['additional_vpn_users'] = [vpn_key]
            else:
                booking['additional_vpn_users'].append(vpn_key)
        self.action_service.set_value(
                name=name,
                value=json.dumps(booking),
                local=False
                )

    def addUserToJob(self, vpn_info, job):
        name = "job_" + job
        job = json.loads(
                self.action_service.get_value(name, local=False)
                )
        if 'vpn_keys' not in job:
            job['vpn_keys'] = []
        job['vpn_keys'].append("vpn_" + vpn_info['username'])
        self.action_service.set_value(
                name=name,
                value=json.dumps(job),
                local=False
                )


