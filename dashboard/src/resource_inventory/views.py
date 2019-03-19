##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.shortcuts import render

from resource_inventory.models import Host


class HostView(TemplateView):
    template_name = "resource/hosts.html"

    def get_context_data(self, **kwargs):
        context = super(HostView, self).get_context_data(**kwargs)
        hosts = Host.objects.filter(working=True)
        context.update({'hosts': hosts, 'title': "Hardware Resources"})
        return context

def host_detail_view(request, host_id):
    print("host detail view called with id " + str(host_id))
    host = get_object_or_404(Host, id=host_id)

    return render(
        request,
        "resource/host_detail.html",
        {
            'title': "Host Overview",
            'host': host
        }
    )
