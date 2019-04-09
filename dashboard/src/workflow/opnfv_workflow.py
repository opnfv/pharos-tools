##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.forms import formset_factory
from django.contrib import messages
from django.contrib.auth.models import User

import json
from datetime import timedelta
from django.shortcuts import render

from workflow.models import WorkflowStep
from dashboard.exceptions import ModelValidationException
from resource_inventory.models import Installer, Scenario, OPNFVConfig, GenericHost, ConfigBundle, HostOPNFVConfig, OPNFV_SETTINGS
from workflow.forms import OPNFVSelectionForm, OPNFVNetworkRoleForm, OPNFVHostRoleForm, SWConfigSelectorForm


class OPNFV_Resource_Select(WorkflowStep):
    template = 'booking/steps/swconfig_select.html'
    title = "Select Software Configuration"
    description = "Choose the software and related configurations you want to use to configure OPNFV"
    short_title = "software configuration"
    modified_key = "configbundle_step"

    def post_render(self, request):
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        form = SWConfigSelectorForm(request.POST)
        if form.is_valid():
            bundle_json = form.cleaned_data['software_bundle']
            bundle_json = bundle_json[2:-2]  # Stupid django string bug
            if not bundle_json:
                self.metastep.set_invalid("Please select a valid config")
                return self.render(request)
            bundle_json = json.loads(bundle_json)
            if len(bundle_json) < 1:
                self.metastep.set_invalid("Please select a valid config")
                return self.render(request)
            bundle = None
            id = int(bundle_json[0]['id'])
            bundle = ConfigBundle.objects.get(id=id)

            models['configbundle'] = bundle
            self.repo_put(self.repo.OPNFV_MODELS, models)
            self.metastep.set_valid("Step Completed")
            messages.add_message(request, messages.SUCCESS, 'Form Validated Successfully', fail_silently=True)
        else:
            self.metastep.set_invalid("Please select or create a valid config")
            messages.add_message(request, messages.ERROR, "Form Didn't Validate", fail_silently=True)

        return self.render(request)

    def get_context(self):
        context = super(OPNFV_Resource_Select, self).get_context()
        default = []
        user = self.repo_get(self.repo.SESSION_USER)

        context['form'] = SWConfigSelectorForm(chosen_software=default, bundle=None, edit=True, resource=None, user=user)
        return context


class Pick_Installer(WorkflowStep):
    template = 'config_bundle/steps/pick_installer.html'
    title = 'Pick OPNFV Installer'
    description = 'Choose which OPNFV installer to use'
    short_title = "opnfv installer"
    modified_key = "installer_step"

    def get_context(self):
        context = super(Pick_Installer, self).get_context()

        models = self.repo_get(self.repo.OPNFV_MODELS, None)
        initial = {
            "installer": models['installer_chosen']
            "scenario": models['scenario_chosen']
        }

        context["form"] = OPNFVSelectionForm(initial=initial)
        return context

    def post_render(self, request):
        form = OPNFVSelectionForm(request.POST)
        if form.is_valid():
            installer = form.cleaned_data['installer']
            scenario = form.cleaned_data['scenario']
            models = self.repo_get(self.repo.OPNFV_MODELS)
            models['installer_chosen'] = installer
            models['scenario_chosen'] = scenario
            self.metastep.set_valid("Step Completed")
        else:
            self.set_validity(False, False)
            self.metastep.set_invalid("Please select an Installer and Scenario")

        return self.render(request)


class Assign_Network_Roles(OPNFVWorkflowStep):
    template = 'config_bundle/steps/assign_network_roles.html'
    title = 'Pick Network Roles'
    description = 'Choose what role each network should get'
    short_title = "network roles"
    modified_key = "net_roles_step"

    """
    to do initial filling, repo should have a "network_roles" array with the following structure for each element:
    {
        "role": <NetworkRole object ref>,
        "network": <Network object ref>
    }
    """
    def create_netformset(self, roles, config_bundle):
        roles_initial = []
        set_roles = self.repo_get(self.repo.OPNFV_MODELS, {}).get("network_roles")
        if set_roles:
            roles_initial = set_roles
        else:
            for role in OPNFV_SETTINGS.NETWORK_ROLES:
                roles_initial.append({"role": role})

        Formset = formset_factory(OPNFVNetworkRoleForm, extra=0)
        kwargs = {
            "initial": roles_initial,
            "form_kwargs": {"config_bundle": config_bundle}
        }
        return Formset, kwargs

    def get_context(self):
        context = super(Assign_Network_Roles, self).get_context()
        config_bundle = self.repo_get(self.repo.OPNFV_MODELS, {}).get("configbundle")
        if config_bundle is None:
            context["unavailable"] = True
            return context

        roles = OPNFV_SETTINGS.NETWORK_ROLES
        Formset, kwargs = self.create_netformset(roles, config_bundle)
        context['formset'] = Formset(**kwargs)

        return context

    def post_render(self, request):
        context = super(Assign_Network_Roles, self).get_context()
        config_bundle = self.repo_get(self.repo.OPNFV_MODELS, {}).get("configbundle")
        roles = OPNFV_SETTINGS.NETWORK_ROLES
        Formset, kwargs = self.create_netformset(roles, config_bundle)
        kwargs.pop("initial")
        context['formset'] = Formset(**kwargs)
        #assert config bundle is good




class Assign_Host_Roles(OPNFVWorkflowStep):  # taken verbatim from Define_Software in sw workflow, merge the two?
    template = 'config_bundle/steps/assign_host_roles.html'
    title = 'Pick Host Roles'
    description = "Choose the role each machine will have in your OPNFV pod"
    short_title = "host roles"
    modified_key = "host_roles_step"

    def get_host_list(self, grb=None):
        if grb is None:
            grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE, False)
            if not grb:
                return []
        if grb.id:
            return GenericHost.objects.filter(resource__bundle=grb)
        generic_hosts = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {}).get("hosts", [])
        return generic_hosts

    # expects hostlist to be a list of HostConfiguration objects,
    # and existing_assignments to map from HostConfiguration ids to OPNFVRole objects
    def create_hostformset(self, hostlist, required_roles, existing_assignments):
        hosts_initial = []
        for host in hostlist:
            initial = {"host_name": host.host.resource.name}
            if host.id in existing_assignments:
                initial["role"] = existing_assignments[host.id].role
            hosts_initial.append(initial)

        HostFormset = formset_factory(OPNFVHostRoleForm, extra=0)
        host_formset = HostFormset(initial=hosts_initial)

        return host_formset

    def get_context(self):
        context = super(Assign_Host_Roles, self).get_context()
        context["hide_image_column"] = True

        if not self.depends(["installer_step", "configbundle_step"]):
            context["unavailable"] = True
            return context

        models = self.repo_get(self.repo.OPNFV_MODELS, None)

        configbundle = models["configbundle"]

        host_configs = [hconf for hconf in configbundle.hostConfigurations.all()]

        initial = {}
        required_roles = []

        if self.depends(["host_roles_step"]):  # already visited, so we have initial to account for
            for hostopnfvconfig in models["hostopnfvconfigs"]:
                initial[hostopnfvconfig.config.id] = hostopnfvconfig

        formset = self.create_hostformset(host_configs, required_roles, initial)
        context["formset"] = formset

        return context

    def post_render(self, request):
        if not self.depends(["installer_step", "configbundle_step"]):
            # inform user step inaccessible
            self.metastep.set_invalid("Please choose a pod config and installer before continuing to this step")
            return self.render(request)

        HostFormset = formset_factory(OPNFVHostRoleForm, extra=0)
        formset = HostFormset(request.POST)

        models = self.repo_get(self.repo.OPNFV_MODELS, None)

        configbundle = models["configbundle"]

        host_configs = [hconf for hconf in configbundle.hostConfigurations.all()]

        has_jumphost = False
        if formset.is_valid():
            if "hostopnfvconfigs" not in models:
                models["hostopnfvconfigs"] = []
            i = 0
            for form in formset:
                host = host_configs[i]
                i += 1
                # checks image compatability
                role = form.cleaned_data['role']
                if "jumphost" in role.name.lower():
                    has_jumphost = True
                hostopnfvconfig = HostOPNFVConfig(role=role, config=host)
                models["hostopnfvconfigs"].append(hostopnfvconfig)

            if not has_jumphost:
                self.metastep.set_invalid('Must have at least one "Jumphost" per POD')
                return self.render(request)
            self.metastep.set_valid("Completed")
            self.set_validity(modified=True, validity=True)
        else:
            self.metastep.set_invalid("Please complete all fields")

        return self.render(request)
