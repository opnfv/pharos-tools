##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import os
import urllib
import pytz

import oauth2 as oauth
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import RedirectView, TemplateView, UpdateView
from jira import JIRA
from rest_framework.authtoken.models import Token
from xml.etree import ElementTree

from account.forms import AccountSettingsForm
from account.jira_util import SignatureMethod_RSA_SHA1
from account.models import UserProfile


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


class JiraLoginView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        consumer = oauth.Consumer(settings.OAUTH_CONSUMER_KEY, settings.OAUTH_CONSUMER_SECRET)
        client = oauth.Client(consumer)
        client.set_signature_method(SignatureMethod_RSA_SHA1())

        # Step 1. Get a request token from Jira.
        try:
            resp, content = client.request(settings.OAUTH_REQUEST_TOKEN_URL, "POST")
        except Exception as e:
            messages.add_message(self.request, messages.ERROR,
                                 'Error: Connection to Jira failed. Please contact an Administrator')
            return '/'
        if resp['status'] != '200':
            messages.add_message(self.request, messages.ERROR,
                                 'Error: Connection to Jira failed. Please contact an Administrator')
            return '/'

        # Step 2. Store the request token in a session for later use.
        self.request.session['request_token'] = dict(urllib.parse.parse_qsl(content.decode()))
        # Step 3. Redirect the user to the authentication URL.
        url = settings.OAUTH_AUTHORIZE_URL + '?oauth_token=' + \
              self.request.session['request_token']['oauth_token'] + \
              '&oauth_callback=' + settings.OAUTH_CALLBACK_URL
        return url


class JiraLogoutView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        logout(self.request)
        return '/'

def CASAuthenticatedView(tree):
    """See the Django CAS Middleware documentation on what this method
    should contain:
      https://github.com/kstateome/django-cas#cas-response-callbacks
    """
    ElementTree.register_namespace('cas', 'http://www.yale.edu/tp/cas')
    ns = {'cas': 'http://www.yale.edu/tp/cas'}
    # To list available attributes and print the ElementTree, uncomment the
    # following line:
    # ElementTree.dump(tree)

    username = tree[0].find('cas:user', ns).text
    url = '/'
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        url = reverse('account:settings')
        user = User.objects.create_user(username=username)
        profile = UserProfile()
        profile.user = user
        profile.save()

    # Grab user attributes and assign them the the user and profile objects
    attribs = tree[0].find('cas:attributes', ns)
    email = attribs.find('cas:mail', ns).text
    first_name = attribs.find('cas:profile_name_first', ns).text
    last_name = attribs.find('cas:profile_name_last', ns).text
    user_timezone = attribs.find('cas:timezone', ns).text

    # TODO: Groups exist in Identity but not in the dashboard need to be
    #   created and the user added to them
    # groups = [group.text for group in attribs.findall('cas:group', ns)]

    # TODO: Determine if a superuser/admin group should/can be managed through
    #   Django or through Identity groups
    # if settings.CAS_SUPERUSER_GROUP in groups:
    #     user.is_superuser = True
    # else:
    #     user.is_superuser = False

    tz = pytz.timezone(user_timezone)
    user.userprofile.timezone = tz
    timezone.activate(tz)
    user.userprofile.email_addr = email
    user.first_name = first_name
    user.last_name = last_name
    user.userprofile.save()
    user.save()

    # Redirect user to settings page to complete profile if they're a new
    # user, otherwise redirect to homepage
    return url

@method_decorator(login_required, name='dispatch')
class UserListView(TemplateView):
    template_name = "account/user_list.html"

    def get_context_data(self, **kwargs):
        users = User.objects.all()
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({'title': "Dashboard Users", 'users': users})
        return context
