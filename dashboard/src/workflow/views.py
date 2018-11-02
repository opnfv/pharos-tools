##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.http import HttpResponse, HttpRequest, HttpResponseGone
from django.urls import reverse
from django.shortcuts import render, redirect
from workflow.forms import *
from workflow.workflow_manager import *
from django.utils import timezone
from django import forms
from sys import stdout

import uuid

from workflow.forms import *
from workflow.workflow_manager import *
from pharos_dashboard import settings

import logging
logger = logging.getLogger(__name__)


def attempt_auth(request):
    try:
        manager = ManagerTracker.managers[request.session['manager_session']]

        return manager

    except KeyError:
        return None

def delete_session(request):
    try:
        manager = ManagerTracker.managers[request.session['manager_session']]
        del ManagerTracker.managers[request.session['manager_session']]
        return HttpResponse('')
    except KeyError:
        return None

def step_view(request):
    manager = attempt_auth(request)
    if not manager:
        #no manager found, redirect to "lost" page
        return no_workflow(request)

    if request.GET.get('step') is not None:
        manager.goto(int(request.GET.get('step')))
        manager.repository.logger().info("User requested step change to: %s", request.GET.get('step'))
    else:
        manager.repository.logger().debug("Requested step is None")

    return manager.render(request)

def manager_view(request):
    manager = attempt_auth(request)

    if not manager:
        return HttpResponseGone("No session found that relates to current request")

    if request.method == 'GET': #no need for this statement if only intercepting post requests

        #return general context for viewport page
        return manager.status(request)

    if request.method == 'POST':
        if request.POST.get('add') is not None:
            target_id = None
            if 'target' in request.POST:
                target_id=int(request.POST.get('target'))
            manager.repository.logger().info("adding workflow type %s", str(target_id))
            manager.add_workflow(workflow_type=int(request.POST.get('add')), target_id=target_id)
        elif request.POST.get('edit') is not None and request.POST.get('edit_id') is not None:
            edit_id=int(request.POST.get('edit_id'))
            manager.repository.logger().info("adding edit workflow type %d", edit_id)
            manager.add_workflow(workflow_type=request.POST.get('edit'), edit_object=edit_id)
        elif request.POST.get('cancel') is not None:
            manager.repository.logger().info("cancelling workflow")
            mgr = ManagerTracker.managers[request.session['manager_session']]
            del ManagerTracker.managers[request.session['manager_session']]
            del mgr

    return manager.status(request)

def viewport_view(request):
    if not request.user.is_authenticated:
        return login(request)

    manager = attempt_auth(request)
    if manager is None:
        return no_workflow(request)

    if  request.method == 'GET':
        return render(request, 'workflow/viewport-base.html')
    else:
        pass

def create_session(wf_type, request):
    wf = int(wf_type)
    manager_uuid = uuid.uuid4().hex
    smgr = SessionManager(request=request)
    smgr.set_logger(create_session_logger(smgr, manager_uuid))
    smgr.add_workflow(workflow_type=wf, target_id=request.POST.get("target"))
    ManagerTracker.getInstance().managers[manager_uuid] = smgr

    return manager_uuid

def create_session_logger(sessionmanager, session_id):
    repo = sessionmanager.repository

    log_level = logging.INFO
    if settings.DEBUG:
        log_level = logging.DEBUG

    # string representation of this user
    user = str(repo.get(repo.SESSION_USER, "unknown", 0))

    formatter = logging.Formatter('%(asctime)s - %(name)s - ' + user + ' - %(levelname)s  = %(message)s')
    logger = logging.getLogger(session_id)
    logger.setLevel(log_level)

    log_file = timezone.now().strftime("%d-%m-%y-%H:%M")
    log_file += "sid-" + session_id[:5]
    log_file += "_u-" + user

    file_handler = logging.FileHandler(settings.LOGGING_DIR + "/" + log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    #prints logs
    printer = logging.StreamHandler(stream=stdout)
    printer.setLevel(log_level)
    printer.setFormatter(formatter)
    logger.addHandler(printer)

    logger.info("Session log for user %s with session id %s",
            str(repo.get(repo.SESSION_USER, "(unknown)", 0)),
            str(session_id)
            )
    return logger

def no_workflow(request):
    logger.debug("There is no active workflow")

    return render(request, 'workflow/no_workflow.html', {'title': "Not Found"})

def login(request):
    return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
