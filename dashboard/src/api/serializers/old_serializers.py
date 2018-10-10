##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from rest_framework import serializers

from account.models import UserProfile
from django.contrib.auth.models import User
from notifier.models import Notifier
from booking.models import Booking
from resource_inventory.models import Host
class BookingSerializer(serializers.ModelSerializer):
    #installer_name = serializers.CharField(source='installer.name')
    #scenario_name = serializers.CharField(source='scenario.name')
    #opsys_name = serializers.CharField(source='opsys.name')
    def to_representation(self, booking):

        return {
            "id": booking.id,
            "changeid": booking.changeid,
            "reset": booking.reset,
            "user": booking.user.username,
            "start": booking.start,
            "end": booking.end,
            "purpose": booking.purpose
        }

    def to_internal_value(self, data):

        try:
            resource = Host.objects.get(pk=int( data['resource'] ))
        except ValueError:
            resource_set = Host.objects.filter(name=data['resource'])
            if resource_set.count() != 0:
                resource = resource_set.first()
            else:
                raise serializers.ValidationError({"Error:":"Invalid resource specified"})
        except Host.DoesNotExist:
            raise serializers.ValidationError({"Error:":"Invalid resource specified"})

        start = data['start']

        end = data['end']

        try:
            user = User.objects.get(pk=int( data['user'] ))
        except ValueError:
            user_set = User.objects.filter(username=data['user'])
            if user_set.count() != 1:
                raise serializers.ValidationError({"Error:":"Given user does not point to valid user object"})
            user = user_set.first()
        except User.DoesNotExist:
            raise serializers.ValidationError({"Error:":"Given user does not point to valid user object: " })


#        return Booking(start=start,
#                          end=end,
#                          purpose=purpose,
#                          opsys=os,
#                          installer=installer,
#                          scenario=scenario,
#                          reset=reset,
#                          resource=resource,
#                          user=user)
        #return booking

        return {'start':start, 'end':end, 'resource':resource, 'user':user}

        #retdat[] = {'op



    class Meta:
        model = Booking
#        fields = ('id', 'changeid', 'reset', 'user', 'resource_id', 'opsys_name', 'start', 'end', 'installer_name', 'scenario_name', 'purpose')
        fields = ('start', 'end', 'user', 'purpose', 'opsys', 'installer', 'scenario', 'resource')


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Host
        fields = ('id', 'name', 'description', 'resource_lab', 'url', 'server_set', 'dev_pod')

class NotifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifier
        fields = ('id', 'title', 'content', 'user', 'sender', 'message_type', 'msg_sent')

class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    class Meta:
        model = UserProfile
        fields = ('user', 'username', 'ssh_public_key', 'pgp_public_key', 'email_addr')
