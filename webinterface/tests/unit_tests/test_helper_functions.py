from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *

logging.disable(logging.FATAL)


class EpochFunctionsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Beginning of epoch has epoch week number 0 but date number 3 (is a Thursday)
        # January 5, 1970 is first Monday of epoch, and thus our reference, since our weeks start on a Monday.
        cls.beginning = {'date': datetime.date(1970, 1, 5), 'week_nr': 0}

        add_weeks = 135
        cls.weeks_after = {'date': cls.beginning.get('date') + datetime.timedelta(weeks=add_weeks),
                           'week_nr': add_weeks}

    def epoch_tester(self, func, conv_from, conv_to, expected_input_instance, return_instance, wrong_input_example):
        self.assertIsInstance(func(self.beginning[conv_from]), return_instance)
        self.assertEqual(func(self.beginning[conv_from]), self.beginning[conv_to])

        self.assertEqual(func(self.weeks_after[conv_from]), self.weeks_after[conv_to])

        self.assertRaisesRegex(TypeError, func.__name__+'.*'+expected_input_instance.__name__,
                               func, wrong_input_example)

    def test__date_to_epoch_week(self):
        self.epoch_tester(func=date_to_epoch_week,
                          conv_from='date', conv_to='week_nr',
                          expected_input_instance=datetime.date, return_instance=int,
                          wrong_input_example=123)

    def test__epoch_week_to_monday(self):
        self.epoch_tester(func=epoch_week_to_monday,
                          conv_from='week_nr', conv_to='date',
                          expected_input_instance=int, return_instance=datetime.date,
                          wrong_input_example=datetime.date(2000, 1, 1))
