##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib import messages
from django.shortcuts import render
from django.contrib.auth.models import User
from django.utils import timezone

import json
from datetime import timedelta

from booking.models import Booking
from workflow.models import WorkflowStep, AbstractSelectOrCreate
from workflow.forms import ResourceSelectorForm, SWConfigSelectorForm, BookingMetaForm
from resource_inventory.models import GenericResourceBundle, ResourceBundle, ConfigBundle


"""
subclassing notes:
    subclasses have to define the following class attributes:
        self.repo_key: main output of step, where the selected/created single selector
            result is placed at the end
        self.confirm_key:
"""


class Abstract_Resource_Select(AbstractSelectOrCreate):
    form = ResourceSelectorForm
    template = 'dashboard/genericselect.html'
    title = "Select Resource"
    description = "Select a resource template to use for your deployment"
    short_title = "pod select"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.select_repo_key = self.repo.SELECTED_GRESOURCE_BUNDLE
        self.confirm_key = self.workflow_type

    def alert_bundle_missing(self):
        self.set_invalid("Please select a valid resource bundle")

    def get_form_queryset(self):
        user = self.repo_get(self.repo.SESSION_USER)
        qs = GenericResourceBundle.objects.filter(owner=user)
        return qs

    def get_page_context(self):
        return {
            'select_type': 'resource',
            'select_type_title': 'Resource Bundle',
            'description': "Select a resource template to use for your deployment",
            'title': 'Select Resource',
            'short_title': 'pod select',
            'addable_type_num': 1
        }

    def put_confirm_info(self, bundle):
        confirm_dict = self.repo_get(self.repo.CONFIRMATION)
        if self.confirm_key not in confirm_dict:
            confirm_dict[self.confirm_key] = {}
        confirm_dict[self.confirm_key]["Resource Template"] = bundle.name
        self.repo_put(self.repo.CONFIRMATION, confirm_dict)


class Booking_Resource_Select(Abstract_Resource_Select):
    workflow_type = "booking"


class SWConfig_Select(AbstractSelectOrCreate):
    title = "Select Software Configuration"
    description = "Choose the software and related configurations you want to have used for your deployment"
    short_title = "pod config"
    form = SWConfigSelectorForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.select_repo_key = self.repo.SELECTED_CONFIG_BUNDLE
        self.confirm_key = "booking"

    def alert_bundle_missing(self):
        self.set_invalid("Please select a valid pod config")

    def get_form_queryset(self):
        user = self.repo_get(self.repo.SESSION_USER)
        grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE)
        qs = ConfigBundle.objects.filter(owner=user).filter(bundle=grb)
        return qs

    def put_confirm_info(self, bundle):
        confirm_dict = self.repo_get(self.repo.CONFIRMATION)
        if self.confirm_key not in confirm_dict:
            confirm_dict[self.confirm_key] = {}
        confirm_dict[self.confirm_key]["Software Configuration"] = bundle.name
        self.repo_put(self.repo.CONFIRMATION, confirm_dict)

    def get_page_context(self):
        return {
            'select_type': 'swconfig',
            'select_type_title': 'Software Config',
            'description': "Choose the software and related configurations you want to have used for your deployment",
            'title': 'Select Software Configuration',
            'short_title': 'pod config',
            'addable_type_num': 2
        }

"""
class Resource_Select(WorkflowStep):
    template = 'booking/steps/resource_select.html'
    title = "Select Resource"
    description = "Select a resource template to use for your deployment"
    short_title = "pod select"

    def __init__(self, *args, **kwargs):
        super(Resource_Select, self).__init__(*args, **kwargs)
        self.repo_key = self.repo.SELECTED_GRESOURCE_BUNDLE
        self.repo_check_key = False
        self.confirm_key = "booking"

    def get_context(self):
        context = super(Resource_Select, self).get_context()
        default = []

        chosen_bundle = self.repo_get(self.repo_key, False)
        if chosen_bundle:
            default.append(chosen_bundle.id)

        bundle = chosen_bundle
        edit = self.repo_get(self.repo.EDIT, False)
        user = self.repo_get(self.repo.SESSION_USER)
        context['form'] = ResourceSelectorForm(
            data={"user": user},
            chosen_resource=default,
            bundle=bundle,
            edit=edit
        )
        return context

    def post_render(self, request):
        form = ResourceSelectorForm(request.POST)
        context = self.get_context()
        if form.is_valid():
            data = form.cleaned_data['generic_resource_bundle']
            data = data[2:-2]
            if not data:
                self.set_invalid("Please select a valid bundle")
                return render(request, self.template, context)
            selected_bundle = json.loads(data)
            if len(selected_bundle) < 1:
                self.set_invalid("Please select a valid bundle")
                return render(request, self.template, context)
            selected_id = selected_bundle[0]['id']
            gresource_bundle = None
            try:
                selected_id = int(selected_id)
                gresource_bundle = GenericResourceBundle.objects.get(id=selected_id)

            except ValueError:
                # we want the bundle in the repo
                gresource_bundle = self.repo_get(
                    self.repo.GRESOURCE_BUNDLE_MODELS,
                    {}
                ).get("bundle", GenericResourceBundle())
            self.repo_put(
                self.repo_key,
                gresource_bundle
            )
            confirm = self.repo_get(self.repo.CONFIRMATION)
            if self.confirm_key not in confirm:
                confirm[self.confirm_key] = {}
            confirm[self.confirm_key]["resource name"] = gresource_bundle.name
            self.repo_put(self.repo.CONFIRMATION, confirm)
            messages.add_message(request, messages.SUCCESS, 'Form Validated Successfully', fail_silently=True)
            self.set_valid("Step Completed")

            return render(request, self.template, context)
        else:
            messages.add_message(request, messages.ERROR, "Form Didn't Validate", fail_silently=True)
            self.set_invalid("Please complete the fields highlighted in red to continue")
            return render(request, self.template, context)


class Booking_Resource_Select(Resource_Select):

    def __init__(self, *args, **kwargs):
        super(Booking_Resource_Select, self).__init__(*args, **kwargs)
        self.repo_key = self.repo.SELECTED_GRESOURCE_BUNDLE
        self.confirm_key = "booking"

    def get_context(self):
        context = super(Booking_Resource_Select, self).get_context()
        return context

    def post_render(self, request):
        response = super(Booking_Resource_Select, self).post_render(request)
        models = self.repo_get(self.repo.BOOKING_MODELS, {})
        if "booking" not in models:
            models['booking'] = Booking()
        booking = models['booking']
        resource = self.repo_get(self.repo_key, False)
        if resource:
            try:
                booking.resource.template = resource
            except Exception:
                booking.resource = ResourceBundle(template=resource)
        models['booking'] = booking
        self.repo_put(self.repo.BOOKING_MODELS, models)
        return response


class SWConfig_Select(WorkflowStep):
    template = 'booking/steps/swconfig_select.html'
    title = "Select Software Configuration"
    description = "Choose the software and related configurations you want to have used for your deployment"
    short_title = "pod config"

    def post_render(self, request):
        form = SWConfigSelectorForm(request.POST)
        if form.is_valid():

            bundle_json = form.cleaned_data['software_bundle']
            bundle_json = bundle_json[2:-2]  # Stupid django string bug
            if not bundle_json:
                self.set_invalid("Please select a valid config")
                return self.render(request)
            bundle_json = json.loads(bundle_json)
            if len(bundle_json) < 1:
                self.set_invalid("Please select a valid config")
                return self.render(request)
            bundle = None
            id = int(bundle_json[0]['id'])
            bundle = ConfigBundle.objects.get(id=id)

            grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE)

            if grb and bundle.bundle != grb:
                self.set_invalid("Incompatible config selected for resource bundle")
                return self.render(request)
            if not grb:
                self.repo_set(self.repo.SELECTED_GRESOURCE_BUNDLE, bundle.bundle)

            models = self.repo_get(self.repo.BOOKING_MODELS, {})
            if "booking" not in models:
                models['booking'] = Booking()
            models['booking'].config_bundle = bundle
            self.repo_put(self.repo.BOOKING_MODELS, models)
            confirm = self.repo_get(self.repo.CONFIRMATION)
            if "booking" not in confirm:
                confirm['booking'] = {}
            confirm['booking']["configuration name"] = bundle.name
            self.repo_put(self.repo.CONFIRMATION, confirm)
            self.set_valid("Step Completed")
            messages.add_message(request, messages.SUCCESS, 'Form Validated Successfully', fail_silently=True)
        else:
            self.set_invalid("Please select or create a valid config")
            messages.add_message(request, messages.ERROR, "Form Didn't Validate", fail_silently=True)

        return self.render(request)

    def get_context(self):
        context = super(SWConfig_Select, self).get_context()
        default = []
        bundle = None
        chosen_bundle = None
        created_bundle = self.repo_get(self.repo.SELECTED_CONFIG_BUNDLE)
        booking = self.repo_get(self.repo.BOOKING_MODELS, {}).get("booking", False)
        try:
            chosen_bundle = booking.config_bundle
            default.append(chosen_bundle.id)
            bundle = chosen_bundle
        except Exception:
            if created_bundle:
                default.append(created_bundle.id)
                bundle = created_bundle
        edit = self.repo_get(self.repo.EDIT, False)
        grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE)
        context['form'] = SWConfigSelectorForm(chosen_software=default, bundle=bundle, edit=edit, resource=grb)
        return context
"""


class Booking_Meta(WorkflowStep):
    template = 'booking/steps/booking_meta.html'
    title = "Extra Info"
    description = "Tell us how long you want your booking, what it is for, and who else should have access to it"
    short_title = "booking info"

    def get_context(self):
        context = super(Booking_Meta, self).get_context()
        initial = {}
        default = []
        try:
            models = self.repo_get(self.repo.BOOKING_MODELS, {})
            booking = models.get("booking")
            if booking:
                initial['purpose'] = booking.purpose
                initial['project'] = booking.project
                initial['length'] = (booking.end - booking.start).days
            info = self.repo_get(self.repo.BOOKING_INFO_FILE, False)
            if info:
                initial['info_file'] = info
            users = models.get("collaborators", [])
            for user in users:
                default.append(user.userprofile)
        except Exception:
            pass

        owner = self.repo_get(self.repo.SESSION_USER)

        context['form'] = BookingMetaForm(initial=initial, user_initial=default, owner=owner)
        return context

    def post_render(self, request):
        form = BookingMetaForm(data=request.POST, owner=request.user)
        #context = self.get_context()

        forms = self.repo_get(self.repo.BOOKING_FORMS, {})

        forms["meta_form"] = form
        self.repo_put(self.repo.BOOKING_FORMS, forms)

        if form.is_valid():
            print("form was valid")
            models = self.repo_get(self.repo.BOOKING_MODELS, {})
            if "booking" not in models:
                models['booking'] = Booking()
            models['collaborators'] = []
            confirm = self.repo_get(self.repo.CONFIRMATION)
            if "booking" not in confirm:
                confirm['booking'] = {}

            models['booking'].start = timezone.now()
            models['booking'].end = timezone.now() + timedelta(days=int(form.cleaned_data['length']))
            models['booking'].purpose = form.cleaned_data['purpose']
            models['booking'].project = form.cleaned_data['project']
            for key in ['length', 'project', 'purpose']:
                confirm['booking'][key] = form.cleaned_data[key]

            userprofile_list = form.cleaned_data['users']
            confirm['booking']['collaborators'] = []
            for userprofile in userprofile_list:
                models['collaborators'].append(userprofile.user)
                confirm['booking']['collaborators'].append(userprofile.user.username)

            info_file = form.cleaned_data.get("info_file", False)
            if info_file:
                self.repo_put(self.repo.BOOKING_INFO_FILE, info_file)

            self.repo_put(self.repo.BOOKING_MODELS, models)
            self.repo_put(self.repo.CONFIRMATION, confirm)
            messages.add_message(request, messages.SUCCESS, 'Form Validated', fail_silently=True)
            self.set_valid("Step Completed")
        else:
            print("form was invalid")
            messages.add_message(request, messages.ERROR, "Form didn't validate", fail_silently=True)
            self.set_invalid("Please complete the fields highlighted in red to continue")
            # context['form'] = form  # TODO: store this form
        return self.render(request)
