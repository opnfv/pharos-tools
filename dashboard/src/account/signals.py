##############################################################################
# Copyright (c) 2018 Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
import logging
import pytz

from django.contrib.auth.models import Group
from django.dispatch import receiver
from django.utils import timezone
from django_cas_ng.signals import cas_user_authenticated

from account.models import UserProfile

logger = logging.getLogger(__name__)


@receiver(cas_user_authenticated)
def update_user_attributes(sender, **kwargs):
    logger.debug("CAS Signal Response: %s", kwargs)

    # Grab user attributes and assign them the the user and profile objects
    try:
        attrs = kwargs['attributes']
        user = kwargs['user']
        created = kwargs['created']

        email = attrs['mail']
        first_name = attrs['profile_name_first']
        last_name = attrs['profile_name_last']
        full_name = attrs['profile_name_full']
        groups = attrs['group']
        user_timezone = attrs['timezone']
    except (NameError, KeyError):
        # If we run into any error accessing attributes, continue to let
        # the user login.
        logger.exception("Error accessing CAS attributes")
        return

    # Copy groups the user belongs to in CAS into the system and add
    #   user to those groups.
    new_groups = []
    for group in [g for g in groups if g.startswith('opnfv')]:
        groupobj, created = Group.objects.get_or_create(name=group)
        groupobj.user_set.add(user)
        if created:
            new_groups.append(group)
    logging.debug("New Groups created: %s", new_groups)

    tz = pytz.timezone(user_timezone)
    if created:
        profile = UserProfile()
        profile.user = user
        profile.save()
    user.userprofile.timezone = tz
    timezone.activate(tz)
    user.userprofile.email_addr = email
    user.userprofile.full_name = full_name
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.userprofile.save()
    user.save()
