##############################################################################
# Copyright 2018 Parker Berberian and Others                                 #
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

from st2actions.runners.pythonrunner import Action
import json
import time

class DetectHostsAction(Action):

    def run(self):
        host_lookup = self.build_lookup()
        bookings = json.loads(self.action_service.get_value("bookings", local=False))
        hosts = []
        for bookingID in bookings:
            booking = json.loads(
                    self.action_service.get_value("booking_" + str(bookingID), local=False)
                    )
            if booking['start'] > time.time():
                continue
            hosts.append(host_lookup[booking['resource_id']])

        self.action_service.set_value(name="hosts_to_boot", value=json.dumps(hosts), local=False)

    def build_lookup(self):
        """Builds a reverse lookup between pharos ID and host key in st2"""
        kvps = self.action_service.list_values(local=False, prefix=None)
        lookup = {}
        for kvp in kvps:
            try:  #checks if kvp is valid disctionary
                val = json.loads(kvp.value)
                keys = val.keys()
            except:
                continue
            if "pharos_id" in keys:
                lookup[val['pharos_id']] = kvp.name

        return lookup
