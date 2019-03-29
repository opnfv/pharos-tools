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
import jinja2
import requests


class NotifyAction(Action):

    def __init__(self, *args, **kwargs):
        self._config = kwargs.get('config', None)
        super(NotifyAction, self).__init__(*args, **kwargs)

    def render(self, template, info):
        jinja_template = jinja2.Template(template)
        return jinja_template.render(info=info)

    def send_message(self, job_id=None, task_id=None, payload=None):
        endpoint = "/jobs/" + str(job_id) + "/" + task_id
        self.send_api_message(endpoint, payload)

    def send_api_message(self, endpoint="", payload={}):
        server = self._config['dashboard']['address']
        name = self._config['dashboard']['lab_name']
        url = server + "/api/labs/" + name + endpoint
        header = {"auth-token": self.action_service.get_value("lab_auth_token", local=False)}
        r = requests.post(url, data=payload, timeout=10, headers=header)
        print("response " + str(r.status_code))

