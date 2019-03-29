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
from st2tests.base import BaseSensorTestCase
import Pharos_api

# Test class for pharos
# each method should have test_ prefix
class PharosSensorTest(BaseSensorTestCase):
    sensor_cls = Pharos_api

    def new_booking_tests(self, sensor):
        pass
        # Test that sensor throws appropriate triggers
        # and detects parameters correctly

    def changed_booking_tests(self, sensor):
        pass
        # Test that sensor detects a change has occured
        # and changes what is necessary

    def end_booking_tests(self, sensor):
        pass
        # Test that the sensor detects when a booking ends
        # and throws the correct triggers

    def clean(self, sensor):
        # Removes all existing bookings from the keystore
        sensor.sensor_service.set_value(name="bookings", value="[]", local=False)
        kvps = sensor.sensor_service.list_values(local=False, prefix="booking_")
        for kvp in kvps:
            sensor.sensor_service.delete_value(local=False, name=kvp.name)

    def test_poll(self):
        pass
        #sensor = self.get_sensor_instance()
        #self.clean(sensor)
        #self.new_booking_tests(sensor)
        #self.changed_booking_tests(sensor)
        #self.end_booking_tests(sensor)
        # do stuff
