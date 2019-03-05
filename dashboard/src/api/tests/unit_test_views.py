##############################################################################
# Copyright (c) 2019 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from api.models import LabManager

from booking.models import Booking
from api.models import (
    Job,
    AccessRelation,
    HostNetworkRelation,
    HostHardwareRelation,
    SnapshotRelation,
    SoftwareRelation
)

from django.test import TestCase, Client

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


class ValidBookingCreatesValidJob(TestCase):
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

        cls.lab_selected = 'lab_' + str(cls.lab.lab_user.id) + '_selected'
        cls.host_selected = 'host_' + str(cls.host_profile.id) + '_selected'

        cls.post_data = cls.build_post_data()

        cls.client = Client()

    @classmethod
    def build_post_data(cls):
        post_data = {}
        post_data['filter_field'] = '{"hosts":[{"host_' + str(cls.host_profile.id) + '":"true"}], "labs": [{"lab_' + str(cls.lab.lab_user.id) + '":"true"}]}'
        post_data['purpose'] = 'purposefieldcontentstring'
        post_data['project'] = 'projectfieldcontentstring'
        post_data['length'] = '3'
        post_data['ignore_this'] = 1
        post_data['users'] = ''
        post_data['hostname'] = 'hostnamefieldcontentstring'
        post_data['image'] = str(cls.image.id)
        post_data['installer'] = str(cls.installer.id)
        post_data['scenario'] = str(cls.scenario.id)
        return post_data

    def post(self, changed_fields={}):
        payload = self.post_data.copy()
        payload.update(changed_fields)
        response = self.client.post('/booking/quick/', payload)
        return response

    def generate_booking(self):
        self.post()
        return Booking.objects.first()

    def validate_job(self, job, booking):
        tasks = job.get_tasklist()

        print("validating job that has tasklist:")
        print(str(tasks))

        # need to somehow isolate tasks and check existance

        # separate tasks based on type
        hardware_relations = []
        access_relations = []
        network_relations = []
        software_relations = []
        snapshot_relations = []

        relation_type_map = {
            SoftwareRelation: software_relations,
            HostHardwareRelation: hardware_relations,
            HostNetworkRelation: network_relations,
            SnapshotRelation: snapshot_relations,
            AccessRelation: access_relations}

        for task in tasks:
            relation_type_map[type(task)] += [task]

        self.assertGreaterEqual(len(access_relations), 1)

        

    def validate_basic_booking(self):
        booking = self.generate_booking()
        self.assertIsNotNone(Job.objects.first())
        self.assertEqual(booking, Job.objects.first().booking)

        self.validate_job(booking, Job.objects.first())

    def validate_hardware_config(self, config, booking):
        rbundle = booking.resource
        # cbundle = booking.config_bundle

        hosts = rbundle.hosts

        first_host = hosts.first()

        hostconfig = first_host.configuration

        imagename = hostconfig.image.lab_id

        self.assertEqual(config.image, imagename)

        hostname = first_host.template.resource.name

        self.assertEqual(config.hostname, hostname)

        self.assertTrue(config.ipmi_create)
