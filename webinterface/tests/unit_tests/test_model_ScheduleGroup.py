from django.test import TestCase
from webinterface.models import *


class ScheduleGroupTest(TestCase):
    def test__str(self):
        group = ScheduleGroup(name="test")
        self.assertEqual(group.__str__(), group.name)
