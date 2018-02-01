##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################



from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import viewsets
from rest_framework.authtoken.models import Token

from api.decorators import user_has_api_permission
from api.serializers import *
from booking.models import Booking
from dashboard.models import Resource, Server, ResourceStatus


@method_decorator(user_has_api_permission, name='dispatch')
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    filter_fields = ('resource', 'id')


@method_decorator(user_has_api_permission, name='dispatch')
class ServerViewSet(viewsets.ModelViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer
    filter_fields = ('resource', 'name')


@method_decorator(user_has_api_permission, name='dispatch')
class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    filter_fields = ('name', 'id')

@method_decorator(user_has_api_permission, name='dispatch')
class ResourceStatusViewSet(viewsets.ModelViewSet):
    queryset = ResourceStatus.objects.all()
    serializer_class = ResourceStatusSerializer

@method_decorator(user_has_api_permission, name='dispatch')
class NotifierViewSet(viewsets.ModelViewSet):
    queryset = Notifier.objects.none()
    serializer_class = NotifierSerializer

@method_decorator(user_has_api_permission, name='dispatch')
class GenerateTokenView(View):
    def get(self, request, *args, **kwargs):
        user = self.request.user
        token, created = Token.objects.get_or_create(user=user)
        if not created:
            token.delete()
            Token.objects.create(user=user)
        return redirect('account:settings')