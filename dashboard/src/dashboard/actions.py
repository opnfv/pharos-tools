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


def free_leaked_hosts(free_old_bookings=False):
    hosts_to_check = Host.objects.filter(booked=false)
    hosts_without_rb = hosts_to_check.filter(bundle=None)

    hosts_on_old_bookings = hosts_to_check.filter(bundle__booking__end__lt=timezone.now() - timedelta(days=1))

    hosts_to_free = hosts_without_rb

    if free_old_bookings:
        hosts_to_free = hosts_to_free + hosts_on_old_bookings

    for host in hosts_to_free:
        host.booked = False
        host.save()


def free_leaked_public_vlans():
    unbooked_host_interfaces = []

    for lab in Lab.objects.all():

        for host in Host.objects.filter(booked=False).filter(lab=lab):
            for interface in host.interfaces.all():
                unbooked_host_interfaces.append(interface)

        vlans = Vlan.objects.filter(public=True).distinct('vlan_id').filter(interface__in=unbooked_host_interfaces)

        for vlan in vlans:
            # at this stage each vlan should be on an unbooked host. This structure will probably require that we modify this
            # after the network model change
