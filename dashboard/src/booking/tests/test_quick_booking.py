##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

import datetime

from django.test import TestCase, Client

from booking.models import Booking
from dashboard.testing_utils import (
    instantiate_host,
    instantiate_user,
    instantiate_userprofile,
    instantiate_lab,
    instantiate_installer,
    instantiate_image,
    instantiate_scenario,
    instantiate_os,
    make_hostprofile_set,
    instantiate_opnfvrole,
    instantiate_publicnet,
)
# from dashboard import test_utils


class QuickBookingValidFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.loginuser = instantiate_user(False, username="newtestuser", password="testpassword")
        instantiate_userprofile(cls.loginuser, True)

        lab_user = instantiate_user(True)
        cls.lab = instantiate_lab(lab_user)

        cls.host_profile = make_hostprofile_set(cls.lab)
        cls.scenario = instantiate_scenario()
        cls.installer = instantiate_installer([cls.scenario])
        os = instantiate_os([cls.installer])
        cls.image = instantiate_image(cls.lab, 1, cls.loginuser, os, cls.host_profile)
        cls.host = instantiate_host(cls.host_profile, cls.lab)
        cls.role = instantiate_opnfvrole()
        cls.pubnet = instantiate_publicnet(10, cls.lab)

        cls.client = Client()
        print("at end of setUpTestData")

    def setUp(self):
        self.client.login(
            username=self.loginuser.username, password="testpassword")
        print("in setUp:" + str(self.loginuser.username))

    def is_valid_booking(self, booking):
        self.assertEqual(booking.owner, self.loginuser)
        self.assertEqual(booking.purpose, 'purposefieldcontentstring')
        self.assertEqual(booking.project, 'projectfieldcontentstring')
        delta = booking.end - booking.start
        delta -= datetime.timedelta(days=3)
        self.assertLess(delta, datetime.timedelta(minutes=1))

        resourcebundle = booking.resource
        configbundle = booking.config_bundle

        self.assertEqual(self.installer, configbundle.opnfv_config.first().installer)
        self.assertEqual(self.scenario, configbundle.opnfv_config.first().scenario)
        self.assertEqual(resourcebundle.template.getHosts()[0].profile, self.host_profile)
        self.assertEqual(resourcebundle.template.getHosts()[0].resource.name, 'hostnamefieldcontentstring')

        return True

    def test_with_valid_form(self):
        print("test with valid form running")
        response = self.client.post('/booking/quick/', {
            'filter_field': '{"hosts":[{"host_' + str(self.host_profile.id) + '":"true"}], "labs": [{"lab_' + str(self.lab.lab_user.id) + '":"true"}]}',
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
        self.assertIsNotNone(booking)
        self.assertTrue(self.is_valid_booking(booking))
