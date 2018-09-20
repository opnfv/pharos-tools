##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import django.forms as forms

from datetime import datetime

class BookingForm(forms.Form):
    fields = ['start', 'end', 'purpose', 'opsys', 'reset', 'installer', 'scenario']

    start = forms.DateTimeField()
    end = forms.DateTimeField()
    reset = forms.ChoiceField(choices = ((True, 'Yes'),(False, 'No')), label="Reset System", initial='False', required=False)
    purpose = forms.CharField(max_length=300)

class BookingEditForm(forms.Form):
    fields = ['start', 'end', 'purpose', 'opsys', 'reset', 'installer', 'scenario']

    start = forms.DateTimeField()
    end = forms.DateTimeField()
    purpose = forms.CharField(max_length=300)
    reset = forms.ChoiceField(choices = ((True, 'Yes'),(False, 'No')), label="Reset System", initial='False', required=True)


    def __init__(self, *args, **kwargs ):
        cloned_kwargs = {}
        cloned_kwargs['purpose'] = kwargs.pop('purpose')
        cloned_kwargs['start'] = kwargs.pop('start')
        cloned_kwargs['end'] = kwargs.pop('end')
        super(BookingEditForm, self).__init__( *args, **kwargs)

        self.fields['purpose'].initial = cloned_kwargs['purpose']
        self.fields['start'].initial = cloned_kwargs['start'].strftime('%m/%d/%Y %H:%M')
        self.fields['end'].initial = cloned_kwargs['end'].strftime('%m/%d/%Y %H:%M')
