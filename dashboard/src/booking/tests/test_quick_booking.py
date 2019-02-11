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
from dashboard.testing_utils import (
    instantiate_user,
    instantiate_userprofile,
    instantiate_lab,
    instantiate_installer,
    instantiate_image,
    instantiate_scenario,
    instantiate_os,
    make_hostprofile_set,
)
# from dashboard import test_utils


class QuickBookingValidFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.loginuser = instantiate_user(False,username="newtestuser", password="testpassword")
        instantiate_userprofile(cls.loginuser, True)

        lab_user = instantiate_user(True)
        cls.lab = instantiate_lab(lab_user)

        cls.host_profile = make_hostprofile_set(cls.lab)
        cls.scenario = instantiate_scenario()
        cls.installer = instantiate_installer([cls.scenario])
        os = instantiate_os([cls.installer])
        cls.image = instantiate_image(cls.lab, 1, cls.loginuser, os, cls.host_profile)

        cls.client = Client()

    def setUp(self):
        self.client.login(
            username=self.loginuser.username, password="testpassword")

    def test_with_valid_form(self):
        response = self.client.post('/booking/quick/', {
            'filter_field': '{"hosts":[{"host_' + str(self.host_profile.id) +
            '":"true"}], "labs": [{"lab_' + str(self.lab.lab_user.id) +
            '":"true"}]}',
            'lab_' + str(self.lab.lab_user.id) + '_selected': 'true',
            'host_' + str(self.host_profile.id) + '_selected': 'true',
            'purpose': 'purposefieldcontentstring',
            'project': 'projectfieldcontentstring',
            'length': '3',
            'ignore_this': 1,
            'users': '',
            'hostname': 'hostnamefieldcontentstring',
            'image': str(self.image.id),
            'installer': str(self.installer.id),
            'scenario': str(self.scenario.id),
        })
        self.assertEqual(response.status_code, 200)

        booking = Booking.objects.first()
        print(str(booking.objects.all()))
        self.assertIsNotNone(booking)
