##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.forms import formset_factory

from workflow.models import WorkflowStep
from workflow.booking_workflow import Resource_Select
from resource_inventory.models import Installer, Scenario, OPNFVConfig, GenericHost, ConfigBundle
from workflow.forms import OPNFVSelectionForm, OPNFVNetworkRoleForm, OPNFVHostRoleForm


class OPNFV_Resource_Select(Resource_Select):
    def __init__(self, *args, **kwargs):
        super(OPNFV_Resource_Select, self).__init__(*args, **kwargs)
        self.repo_key = self.repo.SELECTED_GRESOURCE_BUNDLE
        self.confirm_key = "configuration"

    def post_render(self, request):
        response = super(OPNFV_Resource_Select, self).post_render(request)
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        bundle = models.get("bundle", ConfigBundle(owner=self.repo_get(self.repo.SESSION_USER)))
        bundle.bundle = self.repo_get(self.repo_key)  # super put grb here
        models['bundle'] = bundle
        self.repo_put(self.repo.OPNFV_MODELS, models)
        return response


class Pick_Installer(WorkflowStep):
    template = 'config_bundle/steps/pick_installer.html'
    title = 'Pick OPNFV Installer'
    description = 'Choose which OPNFV installer to use'
    short_title = "opnfv installer"

    def get_context(self):
        context = super(Pick_Installer, self).get_context()

        context['installers'] = Installer.objects.all()  # need to filter based on OS used for head node, possibly other factors?
        # context['scenarios'] = Scenario.objects.all()  # need to do dependent filtering here, maybe need to specify more info about
        # whether scenario works with topology of pod
        context['form'] = OPNFVSelectionForm(initial={'scenario': 'os-nosdn-noha'})

        return context

    def post_render(self, request):
        try:
            models = self.repo_get(self.repo.OPNFV_MODELS, {})

        except Exception:  # this seems to be how we do it everywhere else,
            # but we should probably amend this behavior
            pass


class Assign_Network_Roles(WorkflowStep):
    template = 'config_bundle/steps/assign_network_roles.html'
    title = 'Pick Network Roles'
    description = 'Choose what role each network should get'
    short_title = "network roles"

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


class Assign_Host_Roles(WorkflowStep):  # taken verbatim from Define_Software in sw workflow, merge the two?
    template = 'config_bundle/steps/assign_host_roles.html'
    title = 'Pick Host Roles'
    description = "Choose the role each machine will have in your OPNFV pod"
    short_title = "host roles"

    def create_hostformset(self, hostlist):
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

        HostFormset = formset_factory(OPNFVHostRoleForm, extra=0)
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
            formset, filter_data = self.create_hostformset(self.get_host_list(grb))
            context["formset"] = formset
            context["filter_data"] = filter_data
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
