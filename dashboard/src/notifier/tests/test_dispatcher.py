from django.test import TestCase
from notifier.models import *
from django.contrib.auth.models import User

class DispatchTestCase(TestCase):

    # I have no clue how to test this, maybe mock signal? 
    # or mock dispatcher to verify signal and mock email server?