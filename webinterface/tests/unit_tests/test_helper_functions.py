from django.test import TestCase
from webinterface.models import *

import logging
from unittest.mock import *

logging.disable(logging.FATAL)


class HelperFunctionsTest(TestCase):
    def test__correct_dates_to_weekday__date_argument(self):
        self.assertEqual(correct_dates_to_weekday(datetime.date(2010, 2, 1), 3).weekday(), 3)

    def test__correct_dates_to_weekday__list_argument(self):
        corrected_list = correct_dates_to_weekday([datetime.date(2010, 2, 1), datetime.date(2010, 2, 1)], 3)
        self.assertIsInstance(corrected_list, list)
        self.assertEqual(corrected_list[0].weekday(), 3)

    def test__correct_dates_to_weekday__invalid_argument(self):
        self.assertIsNone(correct_dates_to_weekday("thisisnotadate", 4))

    def test__correct_dates_to_due_day(self):
        reference_date = datetime.date(2010, 2, 1)  # Has weekday #0
        self.assertEqual(correct_dates_to_due_day(reference_date).weekday(), 6)

        corrected_list = correct_dates_to_weekday([reference_date, reference_date], 6)
        self.assertIsInstance(corrected_list, list)
        self.assertEqual(corrected_list[0].weekday(), 6)

        self.assertIsNone(correct_dates_to_weekday("thisisnotadate", 6))

















