from django.shortcuts import render
from resource_inventory.models import Host
from django.views import View
from django.views.generic import TemplateView

# Create your views here.

class HostView(TemplateView):
    template_name = "resource/hosts.html"

    def get_context_data(self, **kwargs):
        context = super(HostView, self).get_context_data(**kwargs)
        hosts = Host.objects.filter(working=True)
        context.update({'hosts':hosts, 'title':"Hardware Resources"})
        return context