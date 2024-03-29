##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.shortcuts import render
from django.forms import formset_factory
from django.conf import settings

import json
import re
from xml.dom import minidom

from workflow.models import WorkflowStep
from account.models import Lab
from workflow.forms import (
    HardwareDefinitionForm,
    NetworkDefinitionForm,
    ResourceMetaForm,
    GenericHostMetaForm
)
from resource_inventory.models import (
    GenericResourceBundle,
    GenericInterface,
    GenericHost,
    GenericResource,
    HostProfile,
    Network,
    NetworkConnection
)
from dashboard.exceptions import (
    InvalidVlanConfigurationException,
    NetworkExistsException,
    InvalidHostnameException,
    NonUniqueHostnameException,
    ResourceAvailabilityException
)

import logging
logger = logging.getLogger(__name__)


class Define_Hardware(WorkflowStep):

    template = 'resource/steps/define_hardware.html'
    title = "Define Hardware"
    description = "Choose the type and amount of machines you want"
    short_title = "hosts"

    def __init__(self, *args, **kwargs):
        self.form = None
        super().__init__(*args, **kwargs)

    def get_context(self):
        context = super(Define_Hardware, self).get_context()
        context['form'] = self.form or HardwareDefinitionForm()
        return context

    def update_models(self, data):
        data = data['filter_field']
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        models['hosts'] = []  # This will always clear existing data when this step changes
        models['interfaces'] = {}
        if "bundle" not in models:
            models['bundle'] = GenericResourceBundle(owner=self.repo_get(self.repo.SESSION_USER))
        host_data = data['host']
        names = {}
        for host_profile_dict in host_data.values():
            id = host_profile_dict['id']
            profile = HostProfile.objects.get(id=id)
            # instantiate genericHost and store in repo
            for name in host_profile_dict['values'].values():
                if not re.match(r"(?=^.{1,253}$)(^([A-Za-z0-9-_]{1,62}\.)*[A-Za-z0-9-_]{1,63})", name):
                    raise InvalidHostnameException("Invalid hostname: '" + name + "'")
                if name in names:
                    raise NonUniqueHostnameException("All hosts must have unique names")
                names[name] = True
                genericResource = GenericResource(bundle=models['bundle'], name=name)
                genericHost = GenericHost(profile=profile, resource=genericResource)
                models['hosts'].append(genericHost)
                for interface_profile in profile.interfaceprofile.all():
                    genericInterface = GenericInterface(profile=interface_profile, host=genericHost)
                    if genericHost.resource.name not in models['interfaces']:
                        models['interfaces'][genericHost.resource.name] = []
                    models['interfaces'][genericHost.resource.name].append(genericInterface)

        # add selected lab to models
        for lab_dict in data['lab'].values():
            if lab_dict['selected']:
                models['bundle'].lab = Lab.objects.get(lab_user__id=lab_dict['id'])
                break  # if somehow we get two 'true' labs, we only use one

        # return to repo
        self.repo_put(self.repo.GRESOURCE_BUNDLE_MODELS, models)

    def update_confirmation(self):
        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        if "resource" not in confirm:
            confirm['resource'] = {}
        confirm['resource']['hosts'] = []
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {"hosts": []})
        for host in models['hosts']:
            host_dict = {"name": host.resource.name, "profile": host.profile.name}
            confirm['resource']['hosts'].append(host_dict)
        if "lab" in models:
            confirm['resource']['lab'] = models['lab'].lab_user.username
        self.repo_put(self.repo.CONFIRMATION, confirm)

    def post_render(self, request):
        try:
            self.form = HardwareDefinitionForm(request.POST)
            if self.form.is_valid():
                self.update_models(self.form.cleaned_data)
                self.update_confirmation()
                self.set_valid("Step Completed")
            else:
                self.set_invalid("Please complete the fields highlighted in red to continue")
        except Exception as e:
            self.set_invalid(str(e))
        self.context = self.get_context()
        return render(request, self.template, self.context)


class Define_Nets(WorkflowStep):
    template = 'resource/steps/pod_definition.html'
    title = "Define Networks"
    description = "Use the tool below to draw the network topology of your POD"
    short_title = "networking"
    form = NetworkDefinitionForm

    def get_vlans(self):
        vlans = self.repo_get(self.repo.VLANS)
        if vlans:
            return vlans
        # try to grab some vlans from lab
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        if "bundle" not in models:
            return None
        lab = models['bundle'].lab
        if lab is None or lab.vlan_manager is None:
            return None
        try:
            vlans = lab.vlan_manager.get_vlan(count=lab.vlan_manager.block_size)
            self.repo_put(self.repo.VLANS, vlans)
            return vlans
        except Exception:
            return None

    def make_mx_host_dict(self, generic_host):
        host = {
            'id': generic_host.resource.name,
            'interfaces': [],
            'value': {
                "name": generic_host.resource.name,
                "description": generic_host.profile.description
            }
        }
        for iface in generic_host.profile.interfaceprofile.all():
            host['interfaces'].append({
                "name": iface.name,
                "description": "speed: " + str(iface.speed) + "M\ntype: " + iface.nic_type
            })
        return host

    def get_context(self):
        context = super(Define_Nets, self).get_context()
        context.update({
            'form': NetworkDefinitionForm(),
            'debug': settings.DEBUG,
            'hosts': [],
            'added_hosts': [],
            'removed_hosts': []
        })
        vlans = self.get_vlans()
        if vlans:
            context['vlans'] = vlans
        try:
            models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
            hosts = models.get("hosts", [])
            # calculate if the selected hosts have changed
            added_hosts = set()
            host_set = set(self.repo_get(self.repo.GRB_LAST_HOSTLIST, []))
            if len(host_set):
                new_host_set = set([h.resource.name + "*" + h.profile.name for h in models['hosts']])
                context['removed_hosts'] = [h.split("*")[0] for h in (host_set - new_host_set)]
                added_hosts.update([h.split("*")[0] for h in (new_host_set - host_set)])

            # add all host info to context
            for generic_host in hosts:
                host = self.make_mx_host_dict(generic_host)
                host_serialized = json.dumps(host)
                context['hosts'].append(host_serialized)
                if host['id'] in added_hosts:
                    context['added_hosts'].append(host_serialized)
            bundle = models.get("bundle", False)
            if bundle:
                context['xml'] = bundle.xml or False

        except Exception:
            pass

        return context

    def post_render(self, request):
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        if 'hosts' in models:
            host_set = set([h.resource.name + "*" + h.profile.name for h in models['hosts']])
            self.repo_put(self.repo.GRB_LAST_HOSTLIST, host_set)
        try:
            xmlData = request.POST.get("xml")
            self.updateModels(xmlData)
            # update model with xml
            self.set_valid("Networks applied successfully")
        except ResourceAvailabilityException:
            self.set_invalid("Public network not availble")
        except Exception as e:
            self.set_invalid("An error occurred when applying networks: " + str(e))
        return self.render(request)

    def updateModels(self, xmlData):
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        models["connections"] = {}
        models['networks'] = {}
        given_hosts, interfaces, networks = self.parseXml(xmlData)
        existing_host_list = models.get("hosts", [])
        existing_hosts = {}  # maps id to host
        for host in existing_host_list:
            existing_hosts[host.resource.name] = host

        bundle = models.get("bundle", GenericResourceBundle(owner=self.repo_get(self.repo.SESSION_USER)))

        for net_id, net in networks.items():
            network = Network()
            network.name = net['name']
            network.bundle = bundle
            network.is_public = net['public']
            models['networks'][net_id] = network

        for hostid, given_host in given_hosts.items():
            existing_host = existing_hosts[hostid[5:]]

            for ifaceId in given_host['interfaces']:
                iface = interfaces[ifaceId]
                if existing_host.resource.name not in models['connections']:
                    models['connections'][existing_host.resource.name] = {}
                models['connections'][existing_host.resource.name][iface['profile_name']] = []
                for connection in iface['connections']:
                    network_id = connection['network']
                    net = models['networks'][network_id]
                    connection = NetworkConnection(vlan_is_tagged=connection['tagged'], network=net)
                    models['connections'][existing_host.resource.name][iface['profile_name']].append(connection)
        bundle.xml = xmlData
        self.repo_put(self.repo.GRESOURCE_BUNDLE_MODELS, models)

    def decomposeXml(self, xmlString):
        """
        This function takes in an xml doc from our front end
        and returns dictionaries that map cellIds to the xml
        nodes themselves. There is no unpacking of the
        xml objects, just grouping and organizing
        """

        connections = {}
        networks = {}
        hosts = {}
        interfaces = {}
        network_ports = {}

        xmlDom = minidom.parseString(xmlString)
        root = xmlDom.documentElement.firstChild
        for cell in root.childNodes:
            cellId = cell.getAttribute('id')
            group = cellId.split("_")[0]
            parentGroup = cell.getAttribute("parent").split("_")[0]
            # place cell into correct group

            if cell.getAttribute("edge"):
                connections[cellId] = cell

            elif "network" in group:
                networks[cellId] = cell

            elif "host" in group:
                hosts[cellId] = cell

            elif "host" in parentGroup:
                interfaces[cellId] = cell

            # make network ports also map to thier network
            elif "network" in parentGroup:
                network_ports[cellId] = cell.getAttribute("parent")  # maps port ID to net ID

        return connections, networks, hosts, interfaces, network_ports

    # serialize and deserialize xml from mxGraph
    def parseXml(self, xmlString):
        networks = {}  # maps net name to network object
        hosts = {}  # cotains id -> hosts, each containing interfaces, referencing networks
        interfaces = {}  # maps id -> interface
        untagged_ifaces = set()  # used to check vlan config
        network_names = set()  # used to check network names
        xml_connections, xml_nets, xml_hosts, xml_ifaces, xml_ports = self.decomposeXml(xmlString)

        # parse Hosts
        for cellId, cell in xml_hosts.items():
            cell_json_str = cell.getAttribute("value")
            cell_json = json.loads(cell_json_str)
            host = {"interfaces": [], "name": cellId, "profile_name": cell_json['name']}
            hosts[cellId] = host

        # parse networks
        for cellId, cell in xml_nets.items():
            escaped_json_str = cell.getAttribute("value")
            json_str = escaped_json_str.replace('&quot;', '"')
            net_info = json.loads(json_str)
            net_name = net_info['name']
            public = net_info['public']
            if net_name in network_names:
                raise NetworkExistsException("Non unique network name found")
            network = {"name": net_name, "public": public, "id": cellId}
            networks[cellId] = network
            network_names.add(net_name)

        # parse interfaces
        for cellId, cell in xml_ifaces.items():
            parentId = cell.getAttribute('parent')
            cell_json_str = cell.getAttribute("value")
            cell_json = json.loads(cell_json_str)
            iface = {"name": cellId, "connections": [], "profile_name": cell_json['name']}
            hosts[parentId]['interfaces'].append(cellId)
            interfaces[cellId] = iface

        # parse connections
        for cellId, cell in xml_connections.items():
            escaped_json_str = cell.getAttribute("value")
            json_str = escaped_json_str.replace('&quot;', '"')
            attributes = json.loads(json_str)
            tagged = attributes['tagged']
            interface = None
            network = None
            src = cell.getAttribute("source")
            tgt = cell.getAttribute("target")
            if src in interfaces:
                interface = interfaces[src]
                network = networks[xml_ports[tgt]]
            else:
                interface = interfaces[tgt]
                network = networks[xml_ports[src]]

            if not tagged:
                if interface['name'] in untagged_ifaces:
                    raise InvalidVlanConfigurationException("More than one untagged vlan on an interface")
                untagged_ifaces.add(interface['name'])

            # add connection to interface
            interface['connections'].append({"tagged": tagged, "network": network['id']})

        return hosts, interfaces, networks


class Resource_Meta_Info(WorkflowStep):
    template = 'resource/steps/meta_info.html'
    title = "Extra Info"
    description = "Please fill out the rest of the information about your resource"
    short_title = "pod info"

    def get_context(self):
        context = super(Resource_Meta_Info, self).get_context()
        name = ""
        desc = ""
        bundle = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {}).get("bundle", False)
        if bundle and bundle.name:
            name = bundle.name
            desc = bundle.description
        context['form'] = ResourceMetaForm(initial={"bundle_name": name, "bundle_description": desc})
        return context

    def post_render(self, request):
        form = ResourceMetaForm(request.POST)
        if form.is_valid():
            models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
            name = form.cleaned_data['bundle_name']
            desc = form.cleaned_data['bundle_description']
            bundle = models.get("bundle", GenericResourceBundle(owner=self.repo_get(self.repo.SESSION_USER)))
            bundle.name = name
            bundle.description = desc
            models['bundle'] = bundle
            self.repo_put(self.repo.GRESOURCE_BUNDLE_MODELS, models)
            confirm = self.repo_get(self.repo.CONFIRMATION)
            if "resource" not in confirm:
                confirm['resource'] = {}
            confirm_info = confirm['resource']
            confirm_info["name"] = name
            tmp = desc
            if len(tmp) > 60:
                tmp = tmp[:60] + "..."
            confirm_info["description"] = tmp
            self.repo_put(self.repo.CONFIRMATION, confirm)
            self.set_valid("Step Completed")

        else:
            self.set_invalid("Please correct the fields highlighted in red to continue")
            pass
        return self.render(request)


class Host_Meta_Info(WorkflowStep):
    template = "resource/steps/host_info.html"
    title = "Host Info"
    description = "We need a little bit of information about your chosen machines"
    short_title = "host info"

    def __init__(self, *args, **kwargs):
        super(Host_Meta_Info, self).__init__(*args, **kwargs)
        self.formset = formset_factory(GenericHostMetaForm, extra=0)

    def get_context(self):
        context = super(Host_Meta_Info, self).get_context()
        GenericHostFormset = self.formset
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        initial_data = []
        if "hosts" not in models:
            context['error'] = "Please go back and select your hosts"
        else:
            for host in models['hosts']:
                profile = host.profile.name
                name = host.resource.name
                if not name:
                    name = ""
                initial_data.append({"host_profile": profile, "host_name": name})
        context['formset'] = GenericHostFormset(initial=initial_data)
        return context

    def post_render(self, request):
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        if 'hosts' not in models:
            models['hosts'] = []
        hosts = models['hosts']
        i = 0
        confirm_hosts = []
        GenericHostFormset = self.formset
        formset = GenericHostFormset(request.POST)
        if formset.is_valid():
            for form in formset:
                host = hosts[i]
                host.resource.name = form.cleaned_data['host_name']
                i += 1
                confirm_hosts.append({"name": host.resource.name, "profile": host.profile.name})
            models['hosts'] = hosts
            self.repo_put(self.repo.GRESOURCE_BUNDLE_MODELS, models)
            confirm = self.repo_get(self.repo.CONFIRMATION, {})
            if "resource" not in confirm:
                confirm['resource'] = {}
            confirm['resource']['hosts'] = confirm_hosts
            self.repo_put(self.repo.CONFIRMATION, confirm)
        else:
            pass
        return self.render(request)
