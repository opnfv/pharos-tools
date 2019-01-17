##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import json
import uuid
import collections
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone

from resource_inventory.models import *
from resource_inventory.resource_manager import ResourceManager
from booking.forms import QuickBookingForm
from booking.models import Booking
from dashboard.exceptions import *
from api.models import JobFactory


###model validity exceptions
class IncompatibleInstallerForOS(Exception):
    pass

class IncompatibleScenarioForInstaller(Exception):
    pass

class IncompatibleImageForHost(Exception):
    pass

class ImageOwnershipInvalid(Exception):
    pass

class ImageNotAvailableAtLab(Exception):
    pass

class LabDNE(Exception):
    pass

class HostProfileDNE(Exception):
    pass

class HostNotAvailable(Exception):
    pass

class NoLabSelectedError(Exception):
    pass

class OPNFVRoleDNE(Exception):
    pass

class NoRemainingPublicNetwork(Exception):
    pass


def create_from_form(form, request):
    quick_booking_id = str(uuid.uuid4())


    data = form.cleaned_data
    host_field = form.cleaned_data['filter_field']
    host_json = json.loads(host_field)
    purpose_field = form.cleaned_data['purpose']
    project_field = form.cleaned_data['project']
    users_field = form.cleaned_data['users']
    host_name = form.cleaned_data['hostname']
    length = form.cleaned_data['length']

    image = form.cleaned_data['image']
    scenario = form.cleaned_data['scenario']
    installer = form.cleaned_data['installer']

    ###get all initial info we need to validate
    lab = None
    for lab_dict in host_json['labs']:
        if list(lab_dict.values())[0]:
            lab_user_id = int(list(lab_dict.keys())[0].split("_")[-1])
            lab = Lab.objects.get(lab_user__id=lab_user_id)
            break

    host_dict = host_json['hosts'][0]
    profile_id = list(host_dict.keys())[0]
    profile_id = int(profile_id.split("_")[-1])
    profile = HostProfile.objects.get(id = profile_id)

    ###check validity of field data before trying to apply to models
    if not lab:
        raise LabDNE("Lab with provided ID does not exist")
    if not profile:
        raise HostProfileDNE("Host type with provided ID does not exist")

    #check that hostname is valid
    if not re.match(r"(?=^.{1,253}$)(^([A-Za-z0-9-_]{1,62}\.)*[A-Za-z0-9-_]{1,63})", host_name):
        raise InvalidHostnameException("Hostname must comply to RFC 952 and all extensions to it until this point")
    #check that image os is compatible with installer
    if installer not in image.os.sup_installers.all():
        raise IncompatibleInstallerForOS("Chosen installer is not compatible with the chosen OS")
    if scenario not in installer.sup_scenarios.all():
        raise IncompatibleScenarioForInstaller("The chosen installer does not support the chosen scenario")
    if image.from_lab != lab:
        raise ImageNotAvailableAtLab("The chosen image is not available at the chosen hosting lab")
    if image.host_type != profile:
        raise IncompatibleImageForHost("The chosen image is not available for the chosen host type")
    if not image.public and image.owner != request.user:
        raise ImageOwnershipInvalid("You are not the owner of the chosen private image")
    
    #check if any hosts with profile at lab are still available
    hostset = Host.objects.filter(lab=lab, profile=profile).filter(booked=False)
    if not hostset.first():
        raise HostNotAvailable("Couldn't find any matching unbooked hosts")


    ###generate GenericResourceBundle
    if len(host_json['labs']) != 1:
        raise NoLabSelectedError("No lab was selected")

    grbundle = GenericResourceBundle(owner=request.user)
    grbundle.lab = lab
    grbundle.name = "grbundle for quick booking with uid " + quick_booking_id
    grbundle.description = "grbundle created for quick-deploy booking"
    grbundle.save()

    ###generate GenericResource, GenericHost
    gresource = GenericResource(bundle = grbundle, name = host_name)
    gresource.save()

    ghost = GenericHost()
    ghost.resource = gresource
    ghost.profile = profile
    ghost.save()

    ###acquire physical host, cleanup if fails
    host = None
    try:
        host = ResourceManager.getInstance().acquireHost(ghost, lab.name)
    except Exception as e:
        #TODO: handle deleting generic resource in this instance along with grb
        raise HostNotAvailable("Could not book selected host due to changed availability. Try again later")

    ###generate config bundle
    cbundle = ConfigBundle()
    cbundle.owner = request.user
    cbundle.name = "configbundle for quick booking  with uid " + quick_booking_id
    cbundle.description = "configbundle created for quick-deploy booking"
    cbundle.bundle = grbundle
    cbundle.save()

    ###generate OPNFVConfig pointing to cbundle
    opnfvconfig = OPNFVConfig()
    opnfvconfig.scenario = scenario #get scenario from form
    opnfvconfig.installer = installer #get installer from form
    opnfvconfig.bundle = cbundle
    opnfvconfig.save()

    ###generate HostConfiguration pointing to cbundle
    hconf = HostConfiguration()
    hconf.host = ghost
    hconf.image = image #get image user selects
    hconf.opnfvRole = OPNFVRole.objects.get(name="Jumphost")
    if not hconf.opnfvRole:
        raise OPNFVRoleDNE("No jumphost role was found")
    hconf.bundle = cbundle
    hconf.save()

    ###construct generic interfaces
    for interface_profile in profile.interfaceprofile.all():
        generic_interface = GenericInterface(profile=interface_profile, host=ghost)
        generic_interface.save()
    ghost.save()

    ###get vlan, assign to first interface
    publicnetwork = lab.vlan_manager.get_public_vlan()
    publicvlan = publicnetwork.vlan
    if not publicnetwork:
        raise NoRemainingPublicNetwork("No public networks were available for your pod")
    lab.vlan_manager.reserve_public_vlan(publicvlan)
    
    vlan = Vlan(vlan_id=publicvlan, tagged=False, public=True)
    vlan.save()
    ghost.generic_interfaces.first().vlans.add(vlan)
    ghost.generic_interfaces.first().save()


    ###generate resource bundle
    try:
        resource_bundle = ResourceManager.getInstance().convertResourceBundle(grbundle, config=cbundle)
    except ResourceAvailabilityException as e:
        raise ResourceAvailabilityException("Requested resources not available")
    except ModelValidationException as e:
        raise ModelValidationException("Encountered error while saving grbundle")

    ###generate booking
    booking = Booking()
    booking.purpose = purpose_field
    booking.project = project_field
    booking.lab = lab
    booking.owner = request.user
    booking.start = timezone.now()
    booking.end = timezone.now() + timedelta(days=int(length))
    booking.resource = resource_bundle
    booking.pdf = ResourceManager().makePDF(booking.resource)
    booking.save()


    ###generate job
    JobFactory.makeCompleteJob(booking)

    return True
