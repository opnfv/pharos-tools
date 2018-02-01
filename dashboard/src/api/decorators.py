##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.                             #
#                                                                            #
# All rights reserved. This program and the accompanying materials           #
# are made available under the terms of the Apache License, Version 2.0      #
# which accompanies this distribution, and is available at                   #
# http://www.apache.org/licenses/LICENSE-2.0                                 #
##############################################################################

from django.core.exceptions import PermissionDenied

def user_has_api_permission(function):
    def wrap(request, *args, **kwargs):
        if request.user.groups.filter(name__in=['apiviewperm']).exists():
            return function(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return wrap
