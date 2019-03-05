##############################################################################
# Copyright (c) 2019 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from datetime import timedelta
from django.utils import timezone

from booking.models import Booking
from api.models import (
    Job,
    JobStatus,
    JobFactory,
    AccessRelation,
    HostNetworkRelation,
    HostHardwareRelation,
    SnapshotRelation,
    SoftwareRelation,
    NetworkConfig
)

from resource_inventory.models import (
    Installer,
    Scenario,
    Image,
    OPNFVRole,
    HostProfile,
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
    instantiate_booking,
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
        for i in range(30):
            instantiate_host(cls.host_profile, cls.lab, name="host" + str(i), labid="host" + str(i))
        cls.role = instantiate_opnfvrole("Jumphost")
        cls.computerole = instantiate_opnfvrole("Compute")
        instantiate_publicnet(10, cls.lab)
        instantiate_publicnet(12, cls.lab)
        instantiate_publicnet(14, cls.lab)

        cls.lab_selected = 'lab_' + str(cls.lab.lab_user.id) + '_selected'
        cls.host_selected = 'host_' + str(cls.host_profile.id) + '_selected'

        cls.post_data = cls.build_post_data()

        cls.client = Client()

    def setUp(self):
        self.client.login(
            username=self.loginuser.username, password="testpassword")

    def validate_hardware_config(self, config, booking):
        rbundle = booking.resource
        # cbundle = booking.config_bundle

        hosts = rbundle.hosts

        first_host = hosts.first()

        hostconfig = first_host.config

        imagename = str(hostconfig.image.lab_id)

        self.assertEqual(config.image, imagename)

        hostname = first_host.template.resource.name

        self.assertEqual(config.hostname, hostname)

        self.assertTrue(config.ipmi_create)

        return ("generic", True)

    def validate_access_config(self, config, booking):
        # need to make this work across owner and collaborators
        # self.assertEqual(config.user, booking.owner)

        access_type = config.access_type

        # there has to be a better way of phrasing this
        self.assertTrue(access_type in ['ssh', 'vpn'])

        self.assertTrue(config.context)

        # this may not be generic enough, but is safe to assert in this case
        self.assertFalse(config.revoke)

        return (access_type, True)

    def validate_software_config(self, config, booking):
        # currently this only links to an opnfv config, this test will
        # need to be made more generic if we expand the list
        opnfvconf = config.opnfv

        self.assertEqual(str(self.installer.id), opnfvconf.installer)
        self.assertEqual(str(self.scenario.id), opnfvconf.scenario)

        # figure out how to test roles (what are they in this case?)

        return ("generic", True)

    def validate_network_config(self, config, booking):
        # can't check too much here for a single machine booking
        # other than that such a config exists

        return ("generic", True)

    def validate_snapshot_config(self, config, booking):

        return ("generic", True)

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
        print("job: " + str(job))
        print("booking: " + str(booking))
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

        # do general validation
        config_call_map = {
            SoftwareRelation: self.validate_software_config,
            HostHardwareRelation: self.validate_hardware_config,
            HostNetworkRelation: self.validate_network_config,
            AccessRelation: self.validate_access_config,
            SnapshotRelation: self.validate_snapshot_config}

        for task in tasks:
            config_call_map[type(task)](task.config, booking)

    # def test_validate_basic_booking(self):
    #     booking = self.generate_booking()
    #     self.assertIsNotNone(Job.objects.first())
    #     self.assertEqual(booking, Job.objects.first().booking)

    #     self.validate_job(Job.objects.first(), booking)
    
    def test_valid_network_configs(self):
        booking, compute_hostnames, jump_hostname = self.create_multinode_generic_booking()

        job = Job.objects.get(booking=booking)
        self.assertIsNotNone(job)

        booking_hosts = booking.resource.hosts.all()

        netconfig_set = NetworkConfig.objects.all()

        for config in netconfig_set:
            for interface in config.interfaces.all():
                self.assertTrue(interface.host in booking_hosts)

        # if no interfaces are referenced that shouldn't have vlans,
        # and no vlans exist outside those accounted for in netconfigs,
        # then the api is faithfully representing networks
        # as netconfigs reference resource_inventory models directly

        # make sure this test is running
        self.assertTrue(False)

    def test_valid_hardware_configs(self):
        booking, compute_hostnames, jump_hostname = self.create_multinode_generic_booking()

        job = Job.objects.get(booking=booking)
        self.assertIsNotNone(job)

        hrelations = HostHardwareRelation.objects.filter(job=job).all()

        job_hosts = [r.host for r in hrelations]

        booking_hosts = booking.resource.hosts.all()

        self.assertEqual(len(booking_hosts), len(job_hosts))

        for relation in hrelations:
            self.assertTrue(relation.host in booking_hosts)
            self.assertEqual(relation.status, JobStatus.NEW)
            config = relation.config
            host = relation.host
            self.assertEqual(config.hostname, host.template.resource.name)

    def test_valid_software_configs(self):
        booking, compute_hostnames, jump_hostname = self.create_multinode_generic_booking()

        job = Job.objects.get(booking=booking)
        self.assertIsNotNone(job)

        srelation = SoftwareRelation.objects.filter(job=job).first()
        self.assertIsNotNone(srelation)

        sconfig = srelation.config
        self.assertIsNotNone(sconfig)

        oconfig = sconfig.opnfv
        self.assertIsNotNone(oconfig)

        # not onetoone in models, but first() is safe here based on how ConfigBundle and a matching OPNFVConfig are created
        # this should, however, be made explicit
        self.assertEqual(oconfig.installer, booking.config_bundle.opnfv_config.first().installer.name)
        self.assertEqual(oconfig.scenario, booking.config_bundle.opnfv_config.first().scenario.name)

        for host in oconfig.roles.all():
            role_name = host.config.opnfvRole.name
            if str(role_name) == "Jumphost":
                self.assertEqual(host.template.resource.name, jump_hostname)
            elif str(role_name) == "Compute":
                self.assertTrue(host.template.resource.name in compute_hostnames)
            else:
                self.fail(msg="Host with non-configured role name related to job: " + str(role_name))

    def create_multinode_generic_booking(self):
        topology = {}

        compute_hostnames = ["cmp01", "cmp02", "cmp03"]

        host_type = HostProfile.objects.first()

        universal_networks = [
            {"name": "public", "tagged": False, "public": True},
            {"name": "admin", "tagged": True, "public": False}]
        just_compute_networks = [{"name": "private", "tagged": True, "public": False}]
        just_jumphost_networks = [{"name": "external", "tagged": True, "public": True}]

        # generate a bunch of extra networks
        for i in range(10):
            net = {"tagged": False, "public": False}
            net["name"] = "u_net" + str(i)
            universal_networks.append(net)

        jhost_info = {}
        jhost_info["type"] = host_type
        jhost_info["role"] = OPNFVRole.objects.get(name="Jumphost")
        jhost_info["nets"] = self.make_networks(host_type, list(just_jumphost_networks + universal_networks))
        jhost_info["image"] = self.image
        topology["jump"] = jhost_info

        for hostname in compute_hostnames:
            host_info = {}
            host_info["type"] = host_type
            host_info["role"] = OPNFVRole.objects.get(name="Compute")
            host_info["nets"] = self.make_networks(host_type, list(just_compute_networks + universal_networks))
            host_info["image"] = self.image
            topology[hostname] = host_info

        booking = instantiate_booking(self.loginuser,
                                      timezone.now(),
                                      timezone.now() + timedelta(days=1),
                                      "demobooking",
                                      self.lab,
                                      topology=topology,
                                      installer=self.installer,
                                      scenario=self.scenario)

        if not booking.resource:
            raise Exception("Booking does not have a resource when trying to pass to makeCompleteJob")
        JobFactory.makeCompleteJob(booking)

        return booking, compute_hostnames, "jump"

    """
    evenly distributes networks given across a given profile's interfaces
    """
    def make_networks(self, hostprofile, nets):
        network_struct = []
        count = hostprofile.interfaceprofile.all().count()
        for i in range(count):
            network_struct.append([])
        while(nets):
            index = len(nets) % count
            network_struct[index].append(nets.pop())

        return network_struct
