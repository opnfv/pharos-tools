from django.test import TestCase, Client

class SuperViewTestCase(TestCase):
    url = "/"
    client = Client()

    def test_get(self):
        response = self.client.get(self.url)
        self.assertLess(response.status_code, 300)


class DefineHardwareViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/define_hardware"

class DefineNetworkViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/define_net"

class ResourceMetaViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/resource_meta"

class BookingMetaViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/booking_meta"

class SoftwareSelectViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/software_select"

class ResourceSelectViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/resource_select"
