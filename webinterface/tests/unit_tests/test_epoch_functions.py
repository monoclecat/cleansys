from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *

logging.disable(logging.FATAL)


class EpochFunctionsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # each 'start' is a verified Monday, each 'end' is a verified Sunday, 'week_nr' has been verified manually
        cls.first_week = {'start': datetime.date(1969, 12, 29), 'end': datetime.date(1970, 1, 4), 'week_nr': 0}
        cls.second_week = {'start': datetime.date(1970, 1, 5), 'end': datetime.date(1970, 1, 11), 'week_nr': 1}

    def test__date_to_epoch_week(self):
        self.assertEqual(date_to_epoch_week(self.first_week['start']), self.first_week['week_nr'])
        self.assertEqual(date_to_epoch_week(self.first_week['end']), self.first_week['week_nr'])

        self.assertEqual(date_to_epoch_week(self.second_week['start']), self.second_week['week_nr'])
        self.assertEqual(date_to_epoch_week(self.second_week['end']), self.second_week['week_nr'])

    def test__epoch_week_to_monday(self):
        self.assertEqual(epoch_week_to_monday(self.first_week['week_nr']), self.first_week['start'])
        self.assertEqual(epoch_week_to_monday(self.second_week['week_nr']), self.second_week['start'])

    def test__epoch_week_to_sunday(self):
        self.assertEqual(epoch_week_to_sunday(self.first_week['week_nr']), self.first_week['end'])
        self.assertEqual(epoch_week_to_sunday(self.second_week['week_nr']), self.second_week['end'])
