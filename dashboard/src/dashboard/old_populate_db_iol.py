from django.test import TestCase
from booking.models import Booking
from resource_inventory.models import *
from account.models import *
from api.serializers.booking_serializer import *
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import Permission, User
import json


class Populator:

    def __init__(self):
        self.host_profile_count = 0
        self.generic_host_count = 0
        self.host_profiles = []
        self.generic_bundle_count = 0
        self.booking_count = 0


    """
    For intspeeds and intnames, pass in single int and string for all interfaces to share pattern. Pass in array of length equal to intnum to specify name for each and speed for each.
    Same applies for disksizes, disktypes, and disknames
    """
    def make_host_profile(self, labs, intnum, intspeeds, intnames, name, desc, ramsize, ramchannels, sockets, cores, arch, disksizes, disktypes, disknames, disknum):
        hostProfile = HostProfile.objects.create(
            host_type=self.host_profile_count,
            name=name,
            description=desc
        )
        hostProfile.save()

        for i in range(0,intnum):
            if isinstance(intnames, list):
                intname = intnames[i]
            else:
                intname = intnames + str(i)

            if isinstance(intspeeds, list):
                intspeed = intspeeds[i]
            else:
                intspeed = intspeeds

            interfaceProfile = InterfaceProfile.objects.create(
                speed=intspeed,
                name=intname,
                host=hostProfile
            )
            interfaceProfile.save()


        for i in range(0,disknum):
            if isinstance(disksizes, list):
                disksize = disksizes[i]
            else:
                disksize = disksizes
            if isinstance(disktypes, list):
                disktype = disktypes[i]
            else:
                disktype = disktypes
            if isinstance(disknames, list):
                diskname = disknames[i]
            else:
                diskname = disknames

            diskProfile = DiskProfile.objects.create(
                size=int(disksize),
                media_type=disktype,
                name=diskname,
                host=hostProfile
            )
            diskProfile.save()

        cpuProfile = CpuProfile.objects.create(
            cores=cores,
            architecture=arch,
            cpus=sockets,
            host=hostProfile
        )
        cpuProfile.save()
        ramProfile = RamProfile.objects.create(
            amount=ramsize,
            channels=ramchannels,
            host=hostProfile
        )
        ramProfile.save()
        labset = set()
        labset.add(self.labs[0])
        hostProfile.labs.set(labs)
        return hostProfile

    def make_users(self):
        
        user_pberbarian = User.objects.create(username="pberbarian")
        user_pberbarian.save()
        user_pberbarian_prof = UserProfile.objects.create(user=user_pberbarian)
        user_pberbarian_prof.save()

        user_sbergeron = User.objects.create(username="sbergeron")
        user_sbergeron.save()
        user_sbergeron_prof = UserProfile.objects.create(user=user_sbergeron)
        user_sbergeron_prof.save()
        return [user_sbergeron, user_pberbarian,]

    def make_generic_host(self, host_profile, bundle):
        pass

    def make_labs(self):
        unh_iol = User.objects.create(username="unh_iol")
        unh_iol.save()
        vlans = []
        reserved = []
        for i in range(1,4096):
            vlans.append(1)
            reserved.append(0)
        iol = Lab.objects.create(
                lab_user=unh_iol,
                name="UNH_IOL",
                vlan_manager=VlanManager.objects.create(
                    vlans = json.dumps(vlans),
                    reserved_vlans = json.dumps(reserved),
                    allow_overlapping = False,
                    block_size = 20,
                    ),
                api_token = Lab.make_api_token()
                )
        return [iol]

    def make_generic_bundle(self, profiles, lab):
        pass

    def make_resource_bundle(self, generic_bundle, lab):
        pass


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


        #opnfv roles
        compute = OPNFVRole.objects.create(name="Compute", description="Does the heavy lifting")
        controller = OPNFVRole.objects.create(name="Controller", description="Controls everything")
        jumphost = OPNFVRole.objects.create(name="Jumphost", description="Entry Point")

        lab = Lab.objects.first()
        user = UserProfile.objects.first().user
        image = Image.objects.create(
                lab_id=23,
                name="hpe centos",
                from_lab=lab,
                owner=user,
                host_type=HostProfile.objects.get(name="hpe")
                )
        image = Image.objects.create(
                lab_id=25,
                name="hpe ubuntu",
                from_lab=lab,
                owner=user,
                host_type=HostProfile.objects.get(name="hpe")
                )

        image = Image.objects.create(
                lab_id=26,
                name="hpe suse",
                from_lab=lab,
                owner=user,
                host_type=HostProfile.objects.get(name="hpe")
                )
        image = Image.objects.create(
                lab_id=27,
                name="arm ubuntu",
                from_lab=lab,
                owner=user,
                host_type=HostProfile.objects.get(name="arm")
                )

    def make_lab_hosts(self, hostcount, profile, lab, offset=1):
        for i in range(hostcount):
            name="Host_" + lab.name + "_" + profile.name + "_" + str(i + offset)
            host = Host.objects.create(
                    name=name,
                    lab=lab,
                    profile=profile,
                    labid=profile.name + str(i + offset)
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
        self.users = self.make_users()
        self.make_host_profile(self.labs, 6, 10000, "eno", "hpe", "hp enterprise server", 512, 8, 2, 88, "x86_64", 
            800,"SSD", "/dev/sda", 1)
        self.make_host_profile(self.labs, 4, 10000, "eno", "arm", "Cavium ThunderX server", 256, 8, 2, 96, "arm64",
            450, "SSD", ["/dev/sda", "/dev/sdb"], 2)

        self.resource_bundles = []

        count = 0
        for lab in self.labs:
            self.make_lab_hosts(38, HostProfile.objects.get(name="hpe"), lab)
            self.make_lab_hosts(14, HostProfile.objects.get(name="arm"), lab, offset=38)

        self.configs = self.make_configurations()

