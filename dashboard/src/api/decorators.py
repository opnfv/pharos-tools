##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.                             #
#                                                                            #
# All rights reserved. This program and the accompanying materials           #
# are made available under the terms of the Apache License, Version 2.0      #
# which accompanies this distribution, and is available at                   #
# http://www.apache.org/licenses/LICENSE-2.0                                 #
##############################################################################

from django.core.exceptions import PermissionDenied
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.conf import settings
from django.http import HttpResponse

def user_has_api_permission(function):
    def wrap(request, *args, **kwargs):
        if 'HTTP_AUTHORIZATION' in request.META:
            authtoken = request.META['HTTP_AUTHORIZATION'].split()
            if len(authtoken) == 2:
                    if authtoken[0].lower() == 'token':
                        user = authenticate(token=authtoken[1])
                        if user.groups.filter(name__in=['apiviewperm']).exists():
                            return function(request, *args, **kwargs)
                    if authtoken[0].lower() == 'basic':
                        uname, passwd = authtoken[1].split(':')
                        user = authenticate(username=uname, password=passwd)
                        if user:
                            request.user = user
                        if request.user.groups.filter(name__in=['apiviewperm']).exists():
                            return function(request, *args, **kwargs)
            raise PermissionDenied
            return False
            
            
        if request.user.is_authenticated():
            if request.user.groups.filter(name__in=['apiviewperm']).exists():
                return function(request, *args, **kwargs)
        else:
            raise PermissionDenied
            return False
    return wrap