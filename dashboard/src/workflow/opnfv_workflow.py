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
# from workflow.booking_workflow import Resource_Select
from resource_inventory.models import Installer, Scenario, OPNFVConfig, GenericHost, ConfigBundle
from workflow.forms import OPNFVSelectionForm, OPNFVNetworkRoleForm, OPNFVHostRoleForm, SWConfigSelectorForm


class OPNFVWorkflowStep(WorkflowStep):
    """
    prepopulate repo models dict so accesses are less cumbersome and we dont have to deal with two "bad" cases (invalid + not initialized)
    """
    def prepopulate_opnfv_repo(self):
        models = self.repo_get(self.repo.OPNFV_MODELS, None)
        if not models:
            models = {}
            validity = {}
            validity["configbundle_step"] = {"valid": False, "modified": {"installer": False, "network_roles": False, "host_roles": False, "confirm": False}}
            validity["installer_step"] = {"valid": False, "modified": {"network_roles": False, "host_roles": False, "confirm": False}}
            validity["net_roles_step"] = {"valid": False, "modified": {"confirm": False}}
            validity["host_roles_step"] = {"valid": False, "modified": {"confirm": False}}
            models["validity"] = validity
            models["configbundle"] = None
            models["req_roles"] = {"netroles": [], "hostroles": []}
            self.repo_put(self.repo.OPNFV_MODELS, models)


class OPNFV_Resource_Select(OPNFVWorkflowStep):
    template = 'booking/steps/swconfig_select.html'
    title = "Select Software Configuration"
    description = "Choose the software and related configurations you want to use to configure OPNFV"
    short_title = "software configuration"

    def post_render(self, request):
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

            models = self.repo_get(self.repo.OPNFV_MODELS, {})
            models['configbundle'] = bundle
            models['configbundle_modified'] = True
            self.repo_put(self.repo.OPNFV_MODELS, models)
            confirm = self.repo_get(self.repo.CONFIRMATION)
            self.repo_put(self.repo.CONFIRMATION, confirm)
            self.metastep.set_valid("Step Completed")
            messages.add_message(request, messages.SUCCESS, 'Form Validated Successfully', fail_silently=True)
        else:
            self.metastep.set_invalid("Please select or create a valid config")
            messages.add_message(request, messages.ERROR, "Form Didn't Validate", fail_silently=True)

        return self.render(request)

    def get_context(self):
        context = super(OPNFV_Resource_Select, self).get_context()
        default = []
        chosen_bundle = None
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        chosen_bundle = None
        if 'configbundle' in models:
            chosen_bundle = models['configbundle']
            default.append(chosen_bundle.id)

        context['form'] = SWConfigSelectorForm(chosen_software=default, bundle=None, edit=True, resource=None)
        return context


class Pick_Installer(OPNFVWorkflowStep):
    template = 'config_bundle/steps/pick_installer.html'
    title = 'Pick OPNFV Installer'
    description = 'Choose which OPNFV installer to use'
    short_title = "opnfv installer"

    def get_context(self):
        context = super(Pick_Installer, self).get_context()
        try:
            models = self.repo_get(self.repo.OPNFV_MODELS, None)
            if models is None:
                context["step_unrenderable"] = True
            if not models["configbundle"]
        except Exception:
            pass

        context['installers'] = Installer.objects.all()  # need to filter based on OS used for head node, possibly other factors?
        # context['scenarios'] = Scenario.objects.all()  # need to do dependent filtering here, maybe need to specify more info about
        # whether scenario works with topology of pod
        context['form'] = OPNFVSelectionForm(initial={'scenario': 'os-nosdn-noha'})

        return context

    def post_render(self, request):
        try:
            models = self.repo_put(self.repo.OPNFV_MODELS, None)
            if models is None:
                # this step needs to run and initialize the models
                models = {}
                models["opnfvconfig"] = OPNFVConfig()
                models["opnfvconfig"] = None

        except Exception:  # this seems to be how we do it everywhere else,
            # but we should probably amend this behavior
            pass


class Assign_Network_Roles(OPNFVWorkflowStep):
    template = 'config_bundle/steps/assign_network_roles.html'
    title = 'Pick Network Roles'
    description = 'Choose what role each network should get'
    short_title = "network roles"

    """
    to do initial filling, repo should have a "network_roles" array with the following structure for each element:
    {
        "role": <NetworkRole object ref>,
        "network": <Network object ref>
    }
    """
    def create_netformset(self, networks, roles):
        roles_initial = []
        set_roles = self.repo_get(self.repo.OPNFV_MODELS, {}).get("network_roles")
        if set_roles:
            for role_config in set_roles:
                # role_initial = {'selected_network': role_config['sele
                pass

    def get_context(self):
        context = super(Assign_Network_Roles, self).get_context()
        try:
            models = self.repo_get(self.repo.OPNFV_MODELS, {})
            if "installer" not in models:
                # we need the installer in order to continue
                context["context_unreachable"] = True

        except Exception:
            pass

    def construct_default_networks(self, installer):
        pass


class Assign_Host_Roles(OPNFVWorkflowStep):  # taken verbatim from Define_Software in sw workflow, merge the two?
    template = 'config_bundle/steps/assign_host_roles.html'
    title = 'Pick Host Roles'
    description = "Choose the role each machine will have in your OPNFV pod"
    short_title = "host roles"

    def create_hostformset(self, hostlist, roles):
        hosts_initial = []
        host_configs = self.repo_get(self.repo.OPNFV_MODELS, {}).get("host_configs", False)
        if host_configs:
            for config in host_configs:
                host_initial = {'host_id': config.host.id, 'host_name': config.host.resource.name}
                host_initial['role'] = config.opnfvRole
                hosts_initial.append(host_initial)

        else:
            for host in hostlist:
                host_initial = {'host_id': host.id, 'host_name': host.resource.name}

                hosts_initial.append(host_initial)

        HostFormset = formset_factory(OPNFVHostRoleForm, extra=0, form_kwargs={'roles':roles})
        host_formset = HostFormset(initial=hosts_initial)

        # user = self.repo_get(self.repo.SESSION_USER)

        return host_formset

    def get_host_list(self, grb=None):
        if grb is None:
            grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE, False)
            if not grb:
                return []
        if grb.id:
            return GenericHost.objects.filter(resource__bundle=grb)
        generic_hosts = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {}).get("hosts", [])
        return generic_hosts

    def get_context(self):
        context = super(Assign_Host_Roles, self).get_context()

        grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE, False)

        if grb:
            context["grb"] = grb
            formset = self.create_hostformset(self.get_host_list(grb))
            context["formset"] = formset
        else:
            context["error"] = "Please select a resource first"
            self.metastep.set_invalid("Step requires information that is not yet provided by previous step")

        return context

    def post_render(self, request):
        models = self.repo_get(self.repo.CONFIG_MODELS, {})
        if "bundle" not in models:
            models['bundle'] = ConfigBundle(owner=self.repo_get(self.repo.SESSION_USER))

        confirm = self.repo_get(self.repo.CONFIRMATION, {})

        HostFormset = formset_factory(OPNFVHostRoleForm, extra=0)
        formset = HostFormset(request.POST)
        hosts = self.get_host_list()
        has_jumphost = False
        if formset.is_valid():
            models['host_configs'] = []
            i = 0
            confirm_hosts = []
            for form in formset:
                host = hosts[i]
                i += 1
                # checks image compatability
                role = form.cleaned_data['role']
                if "jumphost" in role.name.lower():
                    has_jumphost = True
                # bundle = models['bundle']
                # hostConfig = HostConfiguration(
                #    host=host,
                #    image=image,
                #    bundle=bundle,
                #    opnfvRole=role
                # )
                # models['host_configs'].append(hostConfig)
                confirm_host = {"name": host.resource.name, "role": role.name}
                confirm_hosts.append(confirm_host)

            if not has_jumphost:
                self.metastep.set_invalid('Must have at least one "Jumphost" per POD')
                return self.render(request)

            self.repo_put(self.repo.CONFIG_MODELS, models)
            if "configuration" not in confirm:
                confirm['configuration'] = {}
            confirm['configuration']['hosts'] = confirm_hosts
            self.repo_put(self.repo.CONFIRMATION, confirm)
            self.metastep.set_valid("Completed")
        else:
            self.metastep.set_invalid("Please complete all fields")

        return self.render(request)
