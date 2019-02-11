##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.test import TestCase, Client

from booking.models import Booking
from account.models import UserProfile
from pharos_dashboard.testing_utils import *
# from dashboard import test_utils


class QuickBookingTestCase(TestCase):
    def setUp(self):
        pass
    def test_with_missing_lab(self):
        pass
    def test_with_missing_hostprofile(self):
        pass
    def test_with_missing_image(self):
        pass
    def test_with_missing_installer(self):
        pass
    def test_with_valid_form(self):
        c = Client()
        response = c.post('/booking/quick/', {
            'filter_field': '{"hosts":[{"host_1":"true"}],"labs":[{"lab_35":"true"}]}',
            'lab_35_selected': 'true',
            'host_1_selected': 'true',
            'purpose': 'purposefieldcontentstring',
            'project': 'projectfieldcontentstring',
            'length': '3',
            'ignore_this': 1,  # this should be changed in the filter field
            'users': '[{"id":1,"expanded_name":"Parker Berberian","string":"pberberian@iol.unh.edu","small_name":"ParkerBerberian"},{"id":41,"expanded_name":"Lincoln Lavoie","string":"lylavoie@iol.unh.edu","small_name":"lylavoie"}]',
            'hostname': 'hostnamefieldcontentstring',
            'image': '1',
            'installer': '2',
            'scenario': '1',
        })
        self.assertEqual(response.status_code, 200)

        # Booking.objects.get(
