##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from resource_inventory.models import Host, Vlan
from datetime import timedelta
from django.utils import timezone


def free_leaked_hosts(free_old_bookings=False, old_booking_age=timedelta(days=1)):
    hosts_to_check = Host.objects.filter(booked=True)
    
    #hosts_without_rb = hosts_to_check.filter(bundle=None)

    bundles = [booking.resource for booking in Booking.objects.filter(end__gt=timezone.now()]
    hosts = []
    for bundle in bundles:
        hosts += [host for host in bundle.hosts.all()]

    for host in Host.objects.all():
        if host not in hosts:
            host.booked = False
            host.save()


def free_leaked_public_vlans():
    booked_host_interfaces = []

    for lab in Lab.objects.all():

        for host in Host.objects.filter(booked=True).filter(lab=lab):
            for interface in host.interfaces.all():
                booked_host_interfaces.append(interface)

        in_use_vlans = Vlan.objects.filter(public=True).distinct('vlan_id').filter(interface__in=booked_host_interfaces)

        manager = lab.vlan_manager
        for vlan in Vlan.objects.all():
            if vlan not in in_use_vlans:
            if vlan.public:
                manager.release_public_vlan(vlan.vlan_id)
            manager.release_vlans(vlan)
