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
import requests


class KeyAction(Action):

    def run(self, booking=None):
        booking_info = json.loads(
                self.action_service.get_value(
                    name="booking_" + str(booking),
                    local=False)
                )
        user_url = self.action_service.get_value("dashboard_url", local=False)
        user_url += "/api/user/" + str(booking_info['user'])
        user = requests.get(user_url).json()
        if user['ssh_public_key'] is None:
            self.logger.warning("User does not have ssh key in the dashboard")
            exit(1)

        return user['ssh_public_key']
