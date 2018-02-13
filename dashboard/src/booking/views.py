##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView
from django.views.generic import TemplateView
from jira import JIRAError
from django.shortcuts import redirect

from account.jira_util import get_jira
from booking.forms import BookingForm, BookingEditForm
from booking.models import Booking
from dashboard.models import Resource

def create_jira_ticket(user, booking):
    jira = get_jira(user)
    issue_dict = {
        'project': 'PHAROS',
        'summary': str(booking.resource) + ': Access Request',
        'description': booking.purpose,
        'issuetype': {'name': 'Task'},
        'components': [{'name': 'POD Access Request'}],
        'assignee': {'name': booking.resource.owner.username}
    }
    issue = jira.create_issue(fields=issue_dict)
    jira.add_attachment(issue, user.userprofile.pgp_public_key)
    jira.add_attachment(issue, user.userprofile.ssh_public_key)
    booking.jira_issue_id = issue.id
    booking.save()


class BookingFormView(FormView):
    template_name = "booking/booking_calendar.html"
    form_class = BookingForm

    def dispatch(self, request, *args, **kwargs):
        self.resource = get_object_or_404(Resource, id=self.kwargs['resource_id'])
        return super(BookingFormView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        title = 'Booking: ' + self.resource.name
        context = super(BookingFormView, self).get_context_data(**kwargs)
        context.update({'title': title, 'resource': self.resource})
        #raise PermissionDenied('check')
        return context

    def get_success_url(self):
        return reverse('booking:create', kwargs=self.kwargs)

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR,
                                 'You need to be logged in to book a Pod.')
            return super(BookingFormView, self).form_invalid(form)

        user = self.request.user
        booking = Booking(start=form.cleaned_data['start'],
                          end=form.cleaned_data['end'],
                          purpose=form.cleaned_data['purpose'],
                          opsys=form.cleaned_data['opsys'],
                          installer=form.cleaned_data['installer'],
                          scenario=form.cleaned_data['scenario'],
                          resource=self.resource, user=user)
        try:
            booking.save()
        except ValueError as err:
            messages.add_message(self.request, messages.ERROR, err)
            return super(BookingFormView, self).form_invalid(form)
        try:
            if settings.CREATE_JIRA_TICKET:
                create_jira_ticket(user, booking)
        except JIRAError:
            messages.add_message(self.request, messages.ERROR, 'Failed to create Jira Ticket. '
                                                               'Please check your Jira '
                                                               'permissions.')
            booking.delete()
            return super(BookingFormView, self).form_invalid(form)
        messages.add_message(self.request, messages.SUCCESS, 'Booking saved')
        return super(BookingFormView, self).form_valid(form)


class BookingEditFormView(FormView):
    template_name = "booking/booking_calendar.html"
    form_class = BookingEditForm

    def is_valid(self):
        return True

    def dispatch(self, request, *args, **kwargs):
        self.resource = get_object_or_404(Resource, id=self.kwargs['resource_id'])
        self.original_booking = get_object_or_404(Booking, id=self.kwargs['booking_id'])
        return super(BookingEditFormView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        title = 'Editing Booking on: ' + self.resource.name
        context = super(BookingEditFormView, self).get_context_data(**kwargs)
        context.update({'title': title, 'resource': self.resource})
        return context

    def get_form_kwargs(self):
        kwargs = super(BookingEditFormView, self).get_form_kwargs()
        kwargs['purpose'] = self.original_booking.purpose
        kwargs['start'] = self.original_booking.start
        kwargs['end'] = self.original_booking.end
        try:
            kwargs['installer'] = self.original_booking.installer
        except AttributeError:
            pass
        try:
            kwargs['scenario'] = self.original_booking.scenario
        except AttributeError:
            pass
        return kwargs

    def get_success_url(self):
        return reverse('booking:create', args=(self.resource.id,))

    def form_valid(self, form):

        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR,
                                 'You need to be logged in to book a Pod.')
            return super(BookingEditFormView, self).form_invalid(form)

        if not self.request.user == self.original_booking.user:
            messages.add_message(self.request, messages.ERROR,
                                 'You are not the owner of this booking.')
            return super(BookingEditFormView, self).form_invalid(form)

        #Do Conflict Checks
        if self.original_booking.start != form.cleaned_data['start']:
            if timezone.now() > form.cleaned_data['start']:
                messages.add_message(self.request, messages.ERROR,
                                     'Cannot change start date after it has occurred.')
                return super(BookingEditFormView, self).form_invalid(form)
        self.original_booking.start = form.cleaned_data['start']
        self.original_booking.end = form.cleaned_data['end']
        self.original_booking.purpose = form.cleaned_data['purpose']
        self.original_booking.installer = form.cleaned_data['installer']
        self.original_booking.scenario = form.cleaned_data['scenario']
        self.original_booking.reset = form.cleaned_data['reset']
        try:
            self.original_booking.save()
        except ValueError as err:
            messages.add_message(self.request, messages.ERROR, err)
            return super(BookingEditFormView, self).form_invalid(form)

        user = self.request.user
        return super(BookingEditFormView, self).form_valid(form)

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
        resource = get_object_or_404(Resource, id=self.kwargs['resource_id'])
        bookings = resource.booking_set.get_queryset().values('id', 'start', 'end', 'purpose',
                                                              'jira_issue_status', 'opsys__name',
                                                              'installer__name', 'scenario__name')
        return JsonResponse({'bookings': list(bookings)})
