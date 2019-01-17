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
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
import json

from resource_inventory.models import *
from resource_inventory.resource_manager import ResourceManager
from booking.models import Booking
from booking.stats import StatisticsManager
from workflow.views import login
from booking.forms import QuickBookingForm
from booking.quick_deployer import *


def drop_filter(user):
    installer_filter = {}
    for image in Image.objects.all():
        installer_filter[image.id] = {}
        for installer in image.os.sup_installers.all():
            installer_filter[image.id][installer.id] = 1

    scenario_filter = {}
    for installer in Installer.objects.all():
        scenario_filter[installer.id] = {}
        for scenario in installer.sup_scenarios.all():
            scenario_filter[installer.id][scenario.id] = 1

    images = Image.objects.filter(Q(public=True) | Q(owner=user))
    image_filter = {}
    for image in images:
        image_filter[image.id] = {}
        image_filter[image.id]['lab'] = 'lab_' + str(image.from_lab.lab_user.id)
        image_filter[image.id]['host_profile'] = 'host_' + str(image.host_type.id)
        image_filter[image.id]['name'] = image.name


    return {'installer_filter': json.dumps(installer_filter), 'scenario_filter': json.dumps(scenario_filter), 'image_filter': json.dumps(image_filter)}


def quick_create_clear_fields(request):
    request.session['quick_create_forminfo'] = None

def quick_create(request):
    if not request.user.is_authenticated:
        return login(request)

    if request.method == 'GET':
        context = {}

        #create field context for host selection field
        r_manager = ResourceManager.getInstance()
        profiles = {}
        for lab in Lab.objects.all():
            profiles[str(lab)] = r_manager.getAvailableHostTypes(lab)

        context['lab_profile_map'] = profiles

        default_user = request.user.username

        context['form'] = QuickBookingForm(initial={}, chosen_users=[], default_user=request.user.username, user=request.user)

        context.update(drop_filter(request.user))

        return render(request, 'booking/quick_deploy.html', context)
    if request.method == 'POST':
        form = QuickBookingForm(request.POST, user=request.user)

        if form.is_valid():
            context = {}
            context['lab_profile_map'] = {}
            context['form'] = form

            try:
                create_from_form(form, request)
            except Exception as e:
                messages.error(request, "Whoops, looks like an error occurred. Let the admins know that you got the following message: " + str(e))
                return render(request, 'workflow/exit_redirect.html', context)

            messages.success(request, "We've processed your request. Check Account->My Bookings for the status of your new booking")
            return render(request, 'workflow/exit_redirect.html', context) #if form successful, don't need to do this unless
                                                                        #models don't validate, so can return redirect instead
        else:
            context = {}
            context['lab_profile_map'] = {}
            context['form'] = form

            messages.error(request, "Looks like the form didn't validate. Check that you entered everything correctly")
            return render(request, 'booking/quick_deploy.html', context)

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

    return render(
        request,
        "booking/booking_detail.html",
        {
            'title': 'Booking Details',
            'booking': booking,
            'pdf': booking.pdf,
            'user_id': user.id
        })


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
