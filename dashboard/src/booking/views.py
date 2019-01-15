##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
from django.db.models import Q
import json

from resource_inventory.models import ResourceBundle, HostProfile, Image, Host
from resource_inventory.resource_manager import ResourceManager
from account.models import Lab
from booking.models import Booking, Installer, Opsys
from booking.stats import StatisticsManager
from booking.forms import HostReImageForm
from api.models import HostHardwareRelation, JobStatus


def drop_filter(context):
    installer_filter = {}
    for os in Opsys.objects.all():
        installer_filter[os.id] = []
        for installer in os.sup_installers.all():
            installer_filter[os.id].append(installer.id)

    scenario_filter = {}
    for installer in Installer.objects.all():
        scenario_filter[installer.id] = []
        for scenario in installer.sup_scenarios.all():
            scenario_filter[installer.id].append(scenario.id)

    context.update({'installer_filter': json.dumps(installer_filter), 'scenario_filter': json.dumps(scenario_filter)})


class BookingView(TemplateView):
    template_name = "booking/booking_detail.html"

    def get_context_data(self, **kwargs):
        booking = get_object_or_404(Booking, id=self.kwargs['booking_id'])
        title = 'Booking Details'
        context = super(BookingView, self).get_context_data(**kwargs)
        context.update({'title': title, 'booking': booking})
        return context


class BookingDeleteView(TemplateView):
    template_name = "booking/booking_delete.html"

    def get_context_data(self, **kwargs):
        booking = get_object_or_404(Booking, id=self.kwargs['booking_id'])
        title = 'Delete Booking'
        context = super(BookingDeleteView, self).get_context_data(**kwargs)
        context.update({'title': title, 'booking': booking})
        return context


def bookingDelete(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.delete()
    messages.add_message(request, messages.SUCCESS, 'Booking deleted')
    return redirect('../../../../')


class BookingListView(TemplateView):
    template_name = "booking/booking_list.html"

    def get_context_data(self, **kwargs):
        bookings = Booking.objects.filter(end__gte=timezone.now())
        title = 'Search Booking'
        context = super(BookingListView, self).get_context_data(**kwargs)
        context.update({'title': title, 'bookings': bookings})
        return context


class ResourceBookingsJSON(View):
    def get(self, request, *args, **kwargs):
        resource = get_object_or_404(ResourceBundle, id=self.kwargs['resource_id'])
        bookings = resource.booking_set.get_queryset().values(
            'id',
            'start',
            'end',
            'purpose',
            'jira_issue_status',
            'config_bundle__name'
        )
        return JsonResponse({'bookings': list(bookings)})


def build_image_mapping(lab, user):
    mapping = {}
    for profile in HostProfile.objects.filter(labs=lab):
        images = Image.objects.filter(
            from_lab=lab,
            host_type=profile
        ).filter(
            Q(public=True) | Q(owner=user)
        )
        mapping[profile.name] = [{"name": image.name, "value": image.id} for image in images]
    return mapping


def booking_detail_view(request, booking_id):
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

    booking = get_object_or_404(Booking, id=booking_id)
    allowed_users = set(list(booking.collaborators.all()))
    allowed_users.add(booking.owner)
    if user not in allowed_users:
        return render(request, "dashboard/login.html", {'title': 'This page is private'})

    context = {
        'title': 'Booking Details',
        'booking': booking,
        'pdf': booking.pdf,
        'user_id': user.id,
        'image_mapping': build_image_mapping(booking.lab, user)
    }

    return render(
        request,
        "booking/booking_detail.html",
        context
    )


def booking_modify_image(request, booking_id):
    form = HostReImageForm(request.POST)
    if form.is_valid():
        booking = Booking.objects.get(id=booking_id)
        if request.user != booking.owner:
            return HttpResponse("unauthorized")
        if timezone.now() > booking.end:
            return HttpResponse("unauthorized")
        new_image = Image.objects.get(id=form.cleaned_data['image_id'])
        host = Host.objects.get(id=form.cleaned_data['host_id'])
        relation = HostHardwareRelation.objects.get(host=host, job__booking=booking)
        config = relation.config
        config.set_image(new_image.lab_id)
        config.save()
        relation.status = JobStatus.NEW
        relation.save()
        return HttpResponse(new_image.name)
    return HttpResponse("error")


def booking_stats_view(request):
    return render(
        request,
        "booking/stats.html",
        context={"data": StatisticsManager.getContinuousBookingTimeSeries(), "title": "Booking Statistics"}
    )


def booking_stats_json(request):
    try:
        span = int(request.GET.get("days", 14))
    except:
        span = 14
    return JsonResponse(StatisticsManager.getContinuousBookingTimeSeries(span), safe=False)
