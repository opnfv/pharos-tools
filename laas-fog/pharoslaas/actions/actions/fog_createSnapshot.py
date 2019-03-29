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

from fogAction import FogAction


class FogCreateSnapshotAction(FogAction):

    def __init__(self, config=None):
        super(FogCreateSnapshotAction, self).__init__(config=config)

    def run(self, host=None, name=None):
        name = name.lower().replace(" ", "_")
        newImage = {}
        currentImageName = self.getFogHostData(host)['imagename']
        currentImage = self.getImage(img=currentImageName)
        basicKeys = [
            'imagePartitionTypeID',
            'toReplicate',
            'isEnabled',
            'compress',
            'storagegroups',
            'osID',
            'imageTypeID'
        ]
        for key in basicKeys:
            newImage[key] = currentImage[key]

        newImage['name'] = name
        newImage['path'] = name

        response = self.createImage(newImage)
        print(response)
