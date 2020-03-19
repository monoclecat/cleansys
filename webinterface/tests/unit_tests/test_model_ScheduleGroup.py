from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *


class ScheduleGroupQuerySetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # ScheduleGroup
        cls.enabled = ScheduleGroup.objects.create(name="enabled", disabled=False)
        cls.disabled = ScheduleGroup.objects.create(name="disabled", disabled=True)

    def test__enabled(self):
        enabled_groups = ScheduleGroup.objects.enabled()
        self.assertIn(self.enabled, enabled_groups)
        self.assertNotIn(self.disabled, enabled_groups)

    def test__disabled(self):
        disabled_groups = ScheduleGroup.objects.disabled()
        self.assertNotIn(self.enabled, disabled_groups)
        self.assertIn(self.disabled, disabled_groups)


class ScheduleGroupTest(TestCase):
    def test__str(self):
        group = ScheduleGroup(name="test")
        self.assertEqual(group.__str__(), group.name)
