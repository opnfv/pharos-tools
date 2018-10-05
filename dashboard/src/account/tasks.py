##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
# Copyright (c) 2018 Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
from celery import shared_task
from django.core.management import call_command

@shared_task
def clear_old_sessions():
    call_command('clearsessions')
    call_command('django_cas_ng_clean_sessions')
