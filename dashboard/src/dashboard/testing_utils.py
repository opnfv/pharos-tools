##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils import timezone

import json
import re
from datetime import timedelta

from dashboard.exceptions import InvalidHostnameException
from booking.models import Booking
from account.models import UserProfile, Lab, LabStatus, VlanManager, PublicNetwork
from resource_inventory.models import (
    Host,
    HostProfile,
    InterfaceProfile,
    DiskProfile,
    CpuProfile,
    Opsys,
    Image,
    Scenario,
    Installer,
    OPNFVRole,
    RamProfile,
    Network,
    Vlan,
    GenericResourceBundle,
    GenericResource,
    GenericHost,
    ConfigBundle,
    GenericInterface,
    HostConfiguration,
    OPNFVConfig,
)
from resource_inventory.resource_manager import ResourceManager

"""
Info for make_booking() function:
[topology] argument structure:
    the [topology] argument should describe the structure of the pod
    the top level should be a dictionary, with each key being a hostname
    each value in the top level should be a dictionary with two keys:
        "type" should map to a host profile instance
        "nets" should map to a list of interfaces each with a list of
            dictionaries each defining a network in the format
            { "name": "netname", "tagged": True|False, "public": True|False }
            each network is defined if a matching name is not found

    sample argument structure:
        topology={
            "host1": {
                      "type": instanceOf HostProfile,
                      "role": instanceOf OPNFVRole
                      "image": instanceOf Image
                      "nets": [
                                0: [
                                        0: { "name": "public", "tagged": True, "public": True },
                                        1: { "name": "private", "tagged": False, "public": False },
                                   ]
                                1: []
                              ]
                  }
        }
"""


def make_booking(owner=None, start=timezone.now(),
                 end=timezone.now() + timedelta(days=1),
                 lab=None, purpose="my_purpose",
                 project="my_project", collaborators=[],
                 topology={}, installer=None, scenario=None):

    grb, host_set = make_grb(topology, owner, lab)
    cb = make_config_bundle(grb, owner, topology, host_set, installer, scenario)
    resource = ResourceManager.getInstance().convertResourceBundle(grb, lab, cb)
    if not resource:
        raise Exception("Resource not created")

    return Booking.objects.create(
        resource=resource,
        config_bundle=cb,
        start=start,
        end=end,
        owner=owner,
        purpose=purpose,
        project=project,
        lab=lab
    )


def make_config_bundle(grb, owner, topology={}, host_set={},
                       installer=None, scenario=None):
    cb = ConfigBundle.objects.create(
        owner=owner,
        name="config bundle " + str(ConfigBundle.objects.count()),
        description="cb generated by make_config_bundle() method"
    )

    OPNFVConfig.objects.create(
        installer=installer,
        scenario=scenario,
        bundle=cb
    )

    # generate host configurations based on topology and host set
    for hostname, host_info in topology.items():
        HostConfiguration.objects.create(
            bundle=cb,
            host=host_set[hostname],
            image=host_info["image"],
            opnfvRole=host_info["role"]
        )
    return cb


def make_network(name, lab, grb, public):
    network = Network(name=name, bundle=grb, is_public=public)
    if public:
        public_net = lab.vlan_manager.get_public_vlan()
        if not public_net:
            raise Exception("No more public networks available")
        lab.vlan_manager.reserve_public_vlan(public_net.vlan)
        network.vlan_id = public_net.vlan
    else:
        private_net = lab.vlan_manager.get_vlan()
        if not private_net:
            raise Exception("No more generic vlans are available")
        lab.vlan_manager.reserve_vlans([private_net])
        network.vlan_id = private_net

    network.save()
    return network


def make_grb(topology, owner, lab):

    grb = GenericResourceBundle.objects.create(
        owner=owner,
        lab=lab,
        name="Generic ResourceBundle " + str(GenericResourceBundle.objects.count()),
        description="grb generated by make_grb() method"
    )

    networks = {}
    host_set = {}

    for hostname, info in topology.items():
        host_profile = info["type"]

        # need to construct host from hostname and type
        generic_host = make_generic_host(grb, host_profile, hostname)
        host_set[hostname] = generic_host

        # set up networks
        nets = info["nets"]
        for interface_index, interface_profile in enumerate(host_profile.interfaceprofile.all()):
            generic_interface = GenericInterface.objects.create(host=generic_host, profile=interface_profile)
            netconfig = nets[interface_index]
            for network_info in netconfig:
                network_name = network_info["name"]
                network = None
                if network_name in networks:
                    network = networks[network_name]
                else:
                    networks[network_name] = make_network(network_name, lab, grb, network_info['public'])

                generic_interface.vlans.add(Vlan.objects.create(
                    vlan_id=network.vlan_id,
                    public=network_info["public"],
                    tagged=network_info["tagged"]
                ))

    return grb, host_set


def make_generic_host(grb, host_profile, hostname):
    if not re.match(r"(?=^.{1,253}$)(^([A-Za-z0-9-_]{1,62}\.)*[A-Za-z0-9-_]{1,63})$", hostname):
        raise InvalidHostnameException("Hostname must comply to RFC 952 and all extensions")
    gresource = GenericResource.objects.create(bundle=grb, name=hostname)

    return GenericHost.objects.create(resource=gresource, profile=host_profile)


def make_user(is_superuser=False, username="testuser",
              password="testpassword", email="default_email@user.com"):
    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_superuser = is_superuser
    user.save()

    return user


def make_user_profile(user=None, email_addr="email@email.com",
                      company="company", full_name="John Doe",
                      booking_privledge=True, ssh_file=None):
    user = user or User.objects.first() or make_user()
    profile = UserProfile.objects.create(
        email_addr=email_addr,
        company=company,
        full_name=full_name,
        booking_privledge=booking_privledge,
        user=user
    )
    profile.ssh_public_key.save("user_ssh_key", ssh_file if ssh_file else ContentFile("public key content string"))

    return profile


def make_vlan_manager(vlans=None, block_size=20, allow_overlapping=False, reserved_vlans=None):
    if not vlans:
        vlans = [vlan % 2 for vlan in range(4095)]
    if not reserved_vlans:
        reserved_vlans = [0 for i in range(4095)]

    return VlanManager.objects.create(
        vlans=json.dumps(vlans),
        reserved_vlans=json.dumps(vlans),
        block_size=block_size,
        allow_overlapping=allow_overlapping
    )


def make_lab(user=None, name="Test Lab Instance",
             status=LabStatus.UP, vlan_manager=None):
    if not vlan_manager:
        vlan_manager = make_vlan_manager()

    if not user:
        user = make_user()

    return Lab.objects.create(
        lab_user=user,
        name=name,
        contact_email='test_lab@test_site.org',
        contact_phone='603 123 4567',
        status=status,
        vlan_manager=vlan_manager,
        description='test lab instantiation',
        api_token='12345678'
    )


"""
resource_inventory instantiation section for permanent resources
"""


def make_complete_host_profile(lab, name="test_hostprofile"):
    host_profile = make_host_profile(lab, name=name)
    make_disk_profile(host_profile, 500, name=name)
    make_cpu_profile(host_profile)
    make_interface_profile(host_profile, name=name)
    make_ram_profile(host_profile)

    return host_profile


def make_host_profile(lab, host_type=0, name="test hostprofile"):
    host_profile = HostProfile.objects.create(
        host_type=host_type,
        name=name,
        description='test hostprofile instance'
    )
    host_profile.labs.add(lab)

    return host_profile


def make_ram_profile(host, channels=4, amount=256):
    return RamProfile.objects.create(
        host=host,
        amount=amount,
        channels=channels
    )


def make_disk_profile(hostprofile, size=0, media_type="SSD",
                      name="test diskprofile", rotation=0,
                      interface="sata"):
    return DiskProfile.objects.create(
        name=name,
        size=size,
        media_type=media_type,
        host=hostprofile,
        rotation=rotation,
        interface=interface
    )


def make_cpu_profile(hostprofile,
                     cores=4,
                     architecture="x86_64",
                     cpus=4,):
    return CpuProfile.objects.create(
        cores=cores,
        architecture=architecture,
        cpus=cpus,
        host=hostprofile,
        cflags=''
    )


def make_interface_profile(hostprofile,
                           speed=1000,
                           name="test interface profile",
                           nic_type="pcie"):
    return InterfaceProfile.objects.create(
        host=hostprofile,
        name=name,
        speed=speed,
        nic_type=nic_type
    )


def make_image(lab, lab_id, owner, os, host_profile,
               public=True, name="default image", description="default image"):
    return Image.objects.create(
        from_lab=lab,
        lab_id=lab_id,
        os=os,
        host_type=host_profile,
        public=public,
        name=name,
        description=description
    )


def make_scenario(name="test scenario"):
    return Scenario.objects.create(name=name)


def make_installer(scenarios, name="test installer"):
    installer = Installer.objects.create(name=name)
    for scenario in scenarios:
        installer.sup_scenarios.add(scenario)

    return installer


def make_os(installers, name="test OS"):
    os = Opsys.objects.create(name=name)
    for installer in installers:
        os.sup_installers.add(installer)

    return os


def make_host(host_profile, lab, labid="test_host", name="test_host",
              booked=False, working=True, config=None, template=None,
              bundle=None, model="Model 1", vendor="ACME"):
    return Host.objects.create(
        lab=lab,
        profile=host_profile,
        name=name,
        booked=booked,
        working=working,
        config=config,
        template=template,
        bundle=bundle,
        model=model,
        vendor=vendor
    )


def make_opnfv_role(name="Jumphost", description="test opnfvrole"):
    return OPNFVRole.objects.create(
        name=name,
        description=description
    )


def make_public_net(vlan, lab, in_use=False,
                    cidr="0.0.0.0/0", gateway="0.0.0.0"):
    return PublicNetwork.objects.create(
        lab=lab,
        vlan=vlan,
        cidr=cidr,
        gateway=gateway
    )
