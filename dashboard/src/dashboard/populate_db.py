##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.test import TestCase
from booking.models import Booking
from resource_inventory.models import *
from account.models import Lab, UserProfile
from api.serializers.booking_serializer import *
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import Permission, User


class Populator:

    def __init__(self):
        self.host_profile_count = 0
        self.generic_host_count = 0
        self.host_profiles = []
        self.generic_bundle_count = 0
        self.booking_count = 0

    def make_host_profile(self):
        hostProfile = HostProfile.objects.create(
            host_type=self.host_profile_count,
            name='Test profile ' + str(self.host_profile_count),
            description='a test profile'
        )
        hostProfile.save()

        count = 0
        for i in range(3 + count%2):
            count += 1
            interfaceProfile = InterfaceProfile.objects.create(
                speed=1000,
                name='eno' + str(i),
                host=hostProfile
            )
            interfaceProfile.save()

        diskProfile = DiskProfile.objects.create(
            size=1000,
            media_type="SSD",
            name='/dev/sda',
            host=hostProfile
        )
        diskProfile.save()
        cpuProfile = CpuProfile.objects.create(
            cores=96,
            architecture="x86_64",
            cpus=2,
            host=hostProfile
        )
        cpuProfile.save()
        ramProfile = RamProfile.objects.create(
            amount=256,
            channels=4,
            host=hostProfile
        )
        ramProfile.save()
        labs = set()
        labs.add(self.labs[self.host_profile_count%len(self.labs)])
        labs.add(self.labs[-(self.host_profile_count%len(self.labs))])
        hostProfile.labs.set(list(labs))
        self.host_profile_count += 1
        return hostProfile

    def make_users(self):
        user_aab = User.objects.create(username="user 1")
        user_aab.save()
        user_aab_prof = UserProfile.objects.create(user=user_aab)
        user_aab_prof.save()

        user_asdf = User.objects.create(username="user 2")
        user_asdf.save()
        user_asdf_prof = UserProfile.objects.create(user=user_asdf)
        user_asdf_prof.save()

        user_sdfg = User.objects.create(username="johnsmith")
        user_sdfg.save()
        user_sdfg_prof = UserProfile.objects.create(user=user_sdfg)
        user_sdfg_prof.save()

        user_a = User.objects.create(username="parkerberb")
        user_a.save()
        user_a_prof = UserProfile.objects.create(user=user_a)
        user_a_prof.save()

        user_ab = User.objects.create(username="sberberon")
        user_ab.save()
        user_ab_prof = UserProfile.objects.create(user=user_ab)
        user_ab_prof.save()
        return [user_aab, user_asdf, user_sdfg, user_a, user_ab]

    def make_generic_host(self, host_profile, bundle):
        gres = GenericResource.objects.create(
            name="generic host " + str(self.generic_host_count),
            bundle=bundle
        )
        gres.save()
        ghost = GenericHost.objects.create(
            profile=host_profile,
            resource=gres
        )
        for iface in host_profile.interfaceprofile.all():
            giface = GenericInterface.objects.create(
                profile=iface,
                host=ghost
            )
            giface.save()
        ghost.save()
        self.generic_host_count += 1
        return ghost

    def make_labs(self):
        lab_user1 = User.objects.create(username="lab_user1")
        lab_user1.save()
        lab1 = Lab.objects.create(
                lab_user=lab_user1,
                name="lab1"
                )
        lab1.save()
        lab_user2 = User.objects.create(username="lab_user2")
        lab_user2.save()
        lab2 = Lab.objects.create(
                lab_user=lab_user2,
                name="lab2"
                )
        lab2.save()
        lab_user3 = User.objects.create(username="lab_user3")
        lab_user3.save()
        lab3 = Lab.objects.create(
                lab_user=lab_user3,
                name="lab3"
                )
        lab3.save()
        return [lab1, lab2, lab3]

    def make_generic_bundle(self, profiles, lab):
        bundle = GenericResourceBundle.objects.create(
                name="generic bundle " + str(self.generic_bundle_count),
                owner=self.users[self.generic_bundle_count % len(self.users)],
                lab=lab
                )
        self.generic_bundle_count += 1
        count = 0
        for profile in profiles:
            for i in range((count%2) + 1):
                count += 1
                self.make_generic_host(profile, bundle)
        bundle.save()
        return bundle

    def make_resource_bundle(self, generic_bundle, lab):
        bundle = ResourceBundle.objects.create(template=generic_bundle)
        for ghost in generic_bundle.generic_resources.all():
            host = Host.objects.create(
                template = ghost.generic_host,
                booked=False,
                name=ghost.name[8:],
                bundle=bundle,
                profile=ghost.generic_host.profile,
                lab=lab,
                labid=lab.lab_user.username + "_" + ghost.name[8:]
            )
            for giface in ghost.generic_host.generic_interfaces.all():
                iface = Interface.objects.create(
                    mac_address="00:11:22:33:44:55",
                    bus_address="a bus address",
                    switch_name="a switch",
                    port_name="a port",
                    host=host
                )
                vlan1 = Vlan.objects.create(vlan_id=iface.id * 20, tagged=True)
                vlan2 = Vlan.objects.create(vlan_id=iface.id * 21, tagged=False)
                iface.config.set([vlan1, vlan2])
        bundle.save()
        return bundle

    def make_booking(self, user, resource, collaborator=None):
        add_booking_perm = Permission.objects.get(codename='add_booking')
        user.user_permissions.add(add_booking_perm)
        conf = ConfigBundle.objects.create(owner=user, name="test conf " + str(self.booking_count))
        conf.save()
        start = timezone.now() + timedelta(weeks=self.booking_count)
        end = start + timedelta(days=3)
        booking = Booking.objects.create(
            owner=user,
            start=start,
            end=end,
            purpose="testing",
            resource=resource,
            config_bundle=conf
        )
        if collaborator:
            booking.collaborators.add(collaborator)
        self.booking_count += 1


    def make_configurations(self):
        #scenarios
        scen1 = Scenario.objects.create(name="os-nosdn-nofeature-noha")
        scen2 = Scenario.objects.create(name="os-odl-kvm-ha")
        scen3 = Scenario.objects.create(name="os-nosdn-nofeature-ha")

        #installers
        fuel = Installer.objects.create(name="Fuel")
        fuel.sup_scenarios.add(scen1)
        fuel.sup_scenarios.add(scen3)
        fuel.save()
        joid = Installer.objects.create(name="Joid")
        joid.sup_scenarios.add(scen1)
        joid.sup_scenarios.add(scen2)
        joid.save()
        apex = Installer.objects.create(name="Apex")
        apex.sup_scenarios.add(scen2)
        apex.sup_scenarios.add(scen3)
        apex.save()
        daisy = Installer.objects.create(name="Daisy")
        daisy.sup_scenarios.add(scen1)
        daisy.sup_scenarios.add(scen2)
        daisy.sup_scenarios.add(scen3)
        daisy.save()
        compass = Installer.objects.create(name="Compass")
        compass.sup_scenarios.add(scen1)
        compass.sup_scenarios.add(scen3)
        compass.save()

        #operating systems
        ubuntu = Opsys.objects.create(name="Ubuntu")
        ubuntu.sup_installers.add(compass)
        ubuntu.sup_installers.add(joid)
        ubuntu.save()
        centos = Opsys.objects.create(name="CentOs")
        centos.sup_installers.add(apex)
        centos.sup_installers.add(fuel)
        centos.save()
        suse = Opsys.objects.create(name="Suse")
        suse.sup_installers.add(fuel)
        suse.save()

        #opfvn roles
        compute = OPNFVRole.objects.create(name="Compute", description="does the heavy lifting")
        controller = OPNFVRole.objects.create(name="Controller", description="Controls everything")
        jumphost = OPNFVRole.objects.create(name="Jumphost", description="Entry Point")

        lab = Lab.objects.all()[0]
        user = UserProfile.objects.all()[0].user
        for i in range(0,10):
            image = Image.objects.create(
                    lab_id=666,
                    name="a host image " + str(i),
                    from_lab=lab,
                    owner=user,
                    host_type=HostProfile.objects.order_by("?").first(),
                    )
        lab = list(Lab.objects.all())[-1]
        user = list(UserProfile.objects.all())[-1].user
        for i in range(0,10):
            image = Image.objects.create(
                    lab_id=999,
                    name="another host image " + str(i),
                    from_lab=lab,
                    owner=user,
                    host_type=HostProfile.objects.order_by("?").first(),
                    )

    def make_lab_hosts(self, profiles, lab):
        for profile in profiles:
            for i in range(5):
                name="Host_"+profile.name+"_"+lab.name+"_"+str(i)
                host = Host.objects.create(
                        name=name,
                        lab=lab,
                        profile=profile,
                        labid="lab_" + name
                        )
                for iface_profile in profile.interfaceprofile.all():
                    Interface.objects.create(
                            mac_address="00:11:22:33:44:55",
                            bus_address="addr",
                            switch_name="ciscoN",
                            port_name="Ethernet1/M",
                            name=iface_profile.name,
                            host=host
                            )

    def populate(self):
        self.labs = self.make_labs()
        for i in range(6):
            self.host_profiles.append(self.make_host_profile())
        self.users = self.make_users()

        self.resource_bundles = []

        count = 0
        for lab in self.labs:
            all_profiles = list(lab.hostprofiles.all())
            start = count%2
            profiles = all_profiles[start:]
            self.make_lab_hosts(profiles, lab)
            gbundle = self.make_generic_bundle(profiles, lab)
            bundle = self.make_resource_bundle(gbundle, lab)
            self.resource_bundles.append(bundle)
            count += 1

        self.configs = self.make_configurations()
        collaborator = User.objects.create(username="collab")
        UserProfile.objects.create(
                user=collaborator,
                timezone="UTC",
                email_addr="email@mail.com",
                company="abc",
                oauth_token="123",
                oauth_secret="xyz"
                )

        for i in range(3):
            user = self.users[i%len(self.users)]
            resource = self.resource_bundles[-(i%len(self.resource_bundles))]
            collab = None
            if i % 2:
                collab = collaborator
            self.make_booking(user, resource, collab)
