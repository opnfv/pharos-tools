##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from typing import List

from django.contrib.auth.models import User

from account.models import UserProfile, Lab, LabStatus, VlanManager
from resource_inventory import (
    HostProfile,
    InterfaceProfile,
    DiskProfile,
    CpuProfile,
)


def instantiate_user(is_superuser: bool,
                     username: str = "testuser",
                     password: str = "testpassword",
                     email: str = "default_email@user.com"
                     ) -> User:
    user: User = User.objects.create_user(username=username, email=email, password=password)
    user.is_superuser = is_superuser

    user.save()

    return user


def instantiate_userprofile(user: User = None, can_book_multiple: bool = False) -> UserProfile:
    if not user:
        user = instantiate_user(True, 'test_user', 'test_pass', 'test_user@test_site.org')
    userprofile: UserProfile = UserProfile()
    userprofile.user = user
    userprofile.booking_privledge = can_book_multiple

    userprofile.save()

    return user


def make_basic_lab(number_of_host_profiles: int = 2, number_of_images: int = 3) -> Lab:
    lab: Lab = instantiate_lab()  # i_l() creates the vlanmanager and user automatically
    for i in range(0, number_of_host_profiles):
        profile: HostProfile = make_hostprofile_set(lab, "test_hostprofile_" + str(i))
        for i in range(0, number_of_images):

        for i in range(0, number_of_hosts):
            host


    return lab


def instantiate_vlanmanager(vlans: str = None,
                            block_size: int = 20,
                            allow_overlapping: bool = False,
                            reserved_vlans: str = None
                            ) -> VlanManager:
    vlanmanager: VlanManager = VlanManager()
    if not vlans:
        vlans: List[int] = []
        for vlan in range(0, 4095):
            vlans.append(vlan % 2)
    vlanmanager.vlans = '[' + ', '.join(vlans) + ']'
    if not reserved_vlans:
        for vlan in range(0, 4095):
            reserved_vlans.append(0)
    vlanmanager.reserved_vlans = '[' + ', '.join(reserved_vlans) + ']'

    vlanmanager.block_size = block_size
    vlanmanager.allow_overlapping = allow_overlapping

    vlanmanager.save()

    return vlanmanager


def instantiate_lab(user: User = None,
                    name: str = "Test Lab Instance",
                    status: int = LabStatus.UP,
                    vlan_manager: VlanManager = None
                    ) -> Lab:
    if not vlan_manager:
        vlan_manager = instantiate_vlanmanager()

    if not user:
        user = instantiate_user(True, 'test_user', 'test_pass', 'test_user@test_site.org')

    lab: Lab = Lab()
    lab.lab_user = user
    lab.name = name
    lab.contact_email = 'test_lab@test_site.org'
    lab.contact_phone = '603 123 4567'
    lab.status = status
    lab.vlan_manager = vlan_manager
    lab.description = 'test lab instantiation'
    lab.api_token = '12345678'

    lab.save()

    return lab


"""
resource_inventory instantiation section for permenant resources
"""


def make_hostprofile_set(lab: Lab, name: str = "test_hostprofile") -> HostProfile:
    hostprof: HostProfile = instantiate_hostprofile(lab, name=name)
    instantiate_diskprofile(hostprof, 500, name=name)
    instantiate_cpuprofile(hostprof)
    instantiate_interfaceprofile(hostprof, name=name)

    return hostprof


def instantiate_hostprofile(lab: Lab,
                            host_type: int = 0,
                            name: str = "test hostprofile instance"
                            ) -> HostProfile:
    hostprof: HostProfile = HostProfile()
    hostprof.host_type = host_type
    hostprof.name = name
    hostprof.description = 'test hostprofile instance'
    hostprof.labs.add(lab)

    hostprof.save()

    return hostprof


def instantiate_diskprofile(hostprofile: HostProfile,
                            size: int = 0,
                            media_type: str = "SSD",
                            name: str = "test diskprofile",
                            rotation: int = 0,
                            interface: str = "sata") -> DiskProfile:

    diskprof: DiskProfile = DiskProfile()
    diskprof.name = name
    diskprof.size = size
    diskprof.media_type = media_type
    diskprof.host = hostprofile
    diskprof.rotation = rotation
    diskprof.interface = interface

    diskprof.save()

    return diskprof


def instantiate_cpuprofile(hostprofile: HostProfile,
                           cores: int = 4,
                           architecture: str = "x86_64",
                           cpus: int = 2,
                           ) -> CpuProfile:
    cpuprof: CpuProfile = CpuProfile()
    cpuprof.cores = cores
    cpuprof.architecture = architecture
    cpuprof.cpus = cpus
    cpuprof.host = hostprofile
    cpuprof.cflags = ''

    cpuprof.save()

    return cpuprof


def instantiate_interfaceprofile(hostprofile: HostProfile,
                                 speed: int = 1000,
                                 name: str = "test interface profile",
                                 nic_type: str = "pcie"
                                 ) -> InterfaceProfile:
    intprof: InterfaceProfile = InterfaceProfile()
    intprof.host = hostprofile
    intprof.name = name
    intprof.spoeed = speed
    intprof.nic_type = nic_type

    intprof.save()

    return intprof


def instantiate_image(lab: Lab,
                     lab_id: int,
                     owner: User,
                     os: Opsys,
                     host_profile: HostProfile,
                     public: bool = True,
                     name: str = "default image",
                     description: str = "default image"
                     ) -> Image:
    image: Image = Image()
    image.from_lab = lab
    image.lab_id = lab_id
    image.os = os
    image.host_type = host_profile
    image.public = public
    image.name = name
    image.description = description

    image.save()

    return image


