##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.test import TestCase
from django.urls import reverse


class DashboardViewTestCase(TestCase):
    def test_booking_utilization_json(self):
        url = reverse('dashboard:booking_utilization', kwargs={'resource_id': 0, 'weeks': 0})
        self.assertEqual(self.client.get(url).status_code, 404)

        url = reverse('dashboard:booking_utilization', kwargs={'resource_id': self.res_active.id,
                                                               'weeks': 0})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data')

    def test_dev_pods_view(self):
        url = reverse('dashboard:dev_pods')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['dev_pods']), 0)

