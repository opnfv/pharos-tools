##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from jira import JIRA
from jira import JIRAError
from django.utils.crypto import get_random_string
import hashlib

from dashboard.models import Resource

class Scenario(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name

class Installer(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    sup_scenarios = models.ManyToManyField(Scenario, blank=True)

    def __str__(self):
        return self.name

class Opsys(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    sup_installers = models.ManyToManyField(Installer, blank=True)

    def __str__(self):
        return self.name

class Booking(models.Model):
    id = models.AutoField(primary_key=True)
    changeid = models.TextField(default='initial', blank=True, null=True)
    user = models.ForeignKey(User, models.CASCADE)  # delete if user is deleted
    resource = models.ForeignKey(Resource, models.PROTECT)
    start = models.DateTimeField()
    end = models.DateTimeField()
    reset = models.BooleanField(default=False)
    jira_issue_id = models.IntegerField(null=True)
    jira_issue_status = models.CharField(max_length=50)

    opsys = models.ForeignKey(Opsys, models.DO_NOTHING, null=True)
    installer = models.ForeignKey(Installer, models.DO_NOTHING, null=True)
    scenario = models.ForeignKey(Scenario, models.DO_NOTHING, null=True)
    purpose = models.CharField(max_length=300, blank=False)

    class Meta:
        db_table = 'booking'

    def get_jira_issue(self):
        try:
            jira = JIRA(server=settings.JIRA_URL,
                        basic_auth=(settings.JIRA_USER_NAME, settings.JIRA_USER_PASSWORD))
            issue = jira.issue(self.jira_issue_id)
            return issue
        except JIRAError:
            return None

    def save(self, *args, **kwargs):
        """
        Save the booking if self.user is authorized and there is no overlapping booking.
        Raise PermissionError if the user is not authorized
        Raise ValueError if there is an overlapping booking
        """
        if self.start >= self.end:
            raise ValueError('Start date is after end date')
        # conflicts end after booking starts, and start before booking ends
        conflicting_dates = Booking.objects.filter(resource=self.resource).exclude(id=self.id)
        conflicting_dates = conflicting_dates.filter(end__gt=self.start)
        conflicting_dates = conflicting_dates.filter(start__lt=self.end)
        if conflicting_dates.count() > 0:
            raise ValueError('This booking overlaps with another booking')
        if not self.changeid:
            self.changeid = self.id
        else:
            self.changeid = hashlib.md5(self.changeid.encode() + get_random_string(length=32).encode()).hexdigest()
        return super(Booking, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.resource) + ' from ' + str(self.start) + ' until ' + str(self.end)
