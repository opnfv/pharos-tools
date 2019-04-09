##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from workflow.models import WorkflowStep

class Assign_Network_Roles(WorkflowStep):
    template = 'config_bundle/steps/assign_network_roles.html'
    title = 'Pick Network Roles'
    description = 'Choose what role each network should get'
    short_title = "network roles"

    def construct_default_networks(self):
        # need to extract installer from repo and do role assigment

class Assign_Host_Roles(WorkflowStep): # taken verbatim from Define_Software in sw workflow, merge the two?
    template = 'config_bundle/steps/assign_host_roles.html'
    title = 'Pick Host Roles'
    description = "Choose the role each machine will have in your OPNFV pod"
    short_title = "host roles"

    def create_hostformset(self, hostlist):
        hosts_initial = []
        host_configs = self.repo_get(self.repo.CONFIG_MODELS, {}).get("host_configs", False)
        if host_configs:
            for config in host_configs:
                host_initial = {'host_id': config.host.id, 'host_name': config.host.resource.name}
                host_initial['role'] = config.opnfvRole
                host_initial['image'] = config.image
                hosts_initial.append(host_initial)

        else:
            for host in hostlist:
                host_initial = {'host_id': host.id, 'host_name': host.resource.name}

                hosts_initial.append(host_initial)

        HostFormset = formset_factory(HostSoftwareDefinitionForm, extra=0)
        host_formset = HostFormset(initial=hosts_initial)

        filter_data = {}
        user = self.repo_get(self.repo.SESSION_USER)
        i = 0
        for host_data in hosts_initial:
            host_profile = None
            try:
                host = GenericHost.objects.get(pk=host_data['host_id'])
                host_profile = host.profile
            except Exception:
                for host in hostlist:
                    if host.resource.name == host_data['host_name']:
                        host_profile = host.profile
                        break
            excluded_images = Image.objects.exclude(owner=user).exclude(public=True)
            excluded_images = excluded_images | Image.objects.exclude(host_type=host_profile)
            lab = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE).lab
            excluded_images = excluded_images | Image.objects.exclude(from_lab=lab)
            filter_data["id_form-" + str(i) + "-image"] = []
            for image in excluded_images:
                filter_data["id_form-" + str(i) + "-image"].append(image.name)
            i += 1

        return host_formset, filter_data

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
        context = super(Define_Software, self).get_context()

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

        HostFormset = formset_factory(HostSoftwareDefinitionForm, extra=0)
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
                image = form.cleaned_data['image']
                # checks image compatability
                grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE)
                lab = None
                if grb:
                    lab = grb.lab
                try:
                    owner = self.repo_get(self.repo.SESSION_USER)
                    q = Image.objects.filter(owner=owner) | Image.objects.filter(public=True)
                    q.filter(host_type=host.profile)
                    q.filter(from_lab=lab)
                    q.get(id=image.id)  # will throw exception if image is not in q
                except Exception:
                    self.metastep.set_invalid("Image " + image.name + " is not compatible with host " + host.resource.name)
                role = form.cleaned_data['role']
                if "jumphost" in role.name.lower():
                    has_jumphost = True
                bundle = models['bundle']
                hostConfig = HostConfiguration(
                    host=host,
                    image=image,
                    bundle=bundle,
                    opnfvRole=role
                )
                models['host_configs'].append(hostConfig)
                confirm_host = {"name": host.resource.name, "image": image.name, "role": role.name}
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
