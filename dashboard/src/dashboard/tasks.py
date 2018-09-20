##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.conf import settings
from booking.models import Booking
from notifier.manager import *
from notifier.models import *
from api.models import *

@shared_task
def conjure_aggregate_notifiers():
    print("creating notifications")
    NotifyPeriodic.task()

@shared_task
def database_cleanup():
    print("\n\n\nexecuting database cleanup\n\n\n")
    now = timezone.now()

def booking_cleanup():
    expire_time = timedelta(days=int(settings.BOOKING_EXP_TIME))
    expire_number = int(settings.BOOKING_MAX_NUM)
    expired_set = Booking.objects.filter(end__lte=timezone.now())
    expired_count = len(expired_set)

    for booking in expired_set:
        if timezone.now() - booking.end > expire_time:
            booking.delete()
            expired_count = expired_count - 1

    if expired_count > expire_number:
        oldest = expired_set.order_by("end")[:expired_count-expire_number]
        for booking in oldest:
            booking.delete()
@shared_task
def booking_poll():
    print("Booking poll has run at " + str(timezone.now()))
    cleanup_set = Booking.objects.filter(end__lte=timezone.now()).filter(job__complete=False)

    print("cleanup_set: " + str(cleanup_set))

    for booking in cleanup_set:
        print("cleaning " + str(booking))
        if not booking.job.complete:
            print("Booking job not complete, so modifying job")
            job = booking.job
            software = SoftwareRelation.objects.filter(job=job).first().config.opnfv
            software.clear_delta()
            software.save()
            for hostrelation in HostHardwareRelation.objects.filter(job=job):
                print("cleaning hwconf: " + str(hostrelation))
                config = hostrelation.config
                config.clear_delta()
                config.set_power("off")
                config.save()
            for hostrelation in HostNetworkRelation.objects.filter(job=job):
                print("cleaning hconf: " + str(hostrelation))
                network = hostrelation.config
                network.interfaces.clear()
                host = hostrelation.host
                network.clear_delta()
                for interface in host.interfaces.all():
                    print("cleaning interface " + str(interface))
                    interface.config.clear()
                    network.add_interface(interface)
            job.complete = True
            print("Job modification complete")
            job.save()
