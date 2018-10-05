##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, UpdateView
from django.shortcuts import render
from rest_framework.authtoken.models import Token

from account.forms import AccountSettingsForm
from account.models import UserProfile
from booking.models import Booking
from resource_inventory.models import GenericResourceBundle, ConfigBundle, Image


@method_decorator(login_required, name='dispatch')
class AccountSettingsView(UpdateView):
    model = UserProfile
    form_class = AccountSettingsForm
    template_name_suffix = '_update_form'

    def get_success_url(self):
        messages.add_message(self.request, messages.INFO,
                             'Settings saved')
        return '/'

    def get_object(self, queryset=None):
        return self.request.user.userprofile

    def get_context_data(self, **kwargs):
        token, created = Token.objects.get_or_create(user=self.request.user)
        context = super(AccountSettingsView, self).get_context_data(**kwargs)
        context.update({'title': "Settings", 'token': token})
        return context


@method_decorator(login_required, name='dispatch')
class UserListView(TemplateView):
    template_name = "account/user_list.html"

    def get_context_data(self, **kwargs):
        users = User.objects.all()
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({'title': "Dashboard Users", 'users': users})
        return context


def account_detail_view(request):
    template = "account/details.html"
    return render(request, template)

def account_resource_view(request):
    """
    gathers a users genericResoureBundles and
    turns them into displayable objects
    """
    if not request.user.is_authenticated:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
    template = "account/resource_list.html"
    resources = list(GenericResourceBundle.objects.filter(owner=request.user))
    context = {"resources": resources, "title": "My Resources"}
    return render(request, template, context=context)

def account_booking_view(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
    template = "account/booking_list.html"
    bookings = list(Booking.objects.filter(owner=request.user))
    collab_bookings = list(request.user.collaborators.all())
    context = {"title": "My Bookings", "bookings": bookings, "collab_bookings": collab_bookings}
    return render(request, template, context=context)

def account_configuration_view(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
    template = "account/configuration_list.html"
    configs = list(ConfigBundle.objects.filter(owner=request.user))
    context = {"title": "Configuration List", "configurations": configs}
    return render(request, template, context=context)

def account_images_view(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
    template = "account/image_list.html"
    my_images = Image.objects.filter(owner=request.user)
    public_images = Image.objects.filter(public=True)
    context = {"title": "Images", "images": my_images, "public_images": public_images }
    return render(request, template, context=context)

