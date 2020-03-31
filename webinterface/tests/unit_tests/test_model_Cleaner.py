from django.test import TestCase
from webinterface.models import *
from unittest.mock import *
from webinterface.tests.unit_tests.fixtures import BaseFixtureWithDutySwitch


class CleanerTest(BaseFixtureWithDutySwitch, TestCase):
    def test__str(self):
        cleaner = Cleaner(name="bob")
        self.assertEqual(cleaner.__str__(), cleaner.name)

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__current_affiliation__exists(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week
        self.assertEqual(self.angie.current_affiliation(), self.angie_affiliation)

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__current_affiliation__does_not_exist(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week-1
        self.assertIsNone(self.angie.current_affiliation())

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__is_active__during_affiliation(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week
        self.assertTrue(self.angie.is_active())

    @patch('webinterface.models.current_epoch_week', autospec=True)
    def test__is_active__outside_of_affiliation(self, mock_current_epoch_week):
        mock_current_epoch_week.return_value = self.start_week-1
        self.assertFalse(self.angie.is_active())

    def test__nr_assignments_on_day(self):
        self.assertListEqual([self.angie.nr_assignments_in_week(x) for x in range(self.start_week, self.end_week+1)],
                             [1, 1, 1, 0])
        self.assertListEqual([self.bob.nr_assignments_in_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [1, 0, 0, 2])
        self.assertListEqual([self.chris.nr_assignments_in_week(x) for x in range(self.start_week, self.end_week + 1)],
                             [0, 1, 1, 1])

    def test__user_is_created_with_cleaner(self):
        self.assertTrue(User.objects.filter(username=self.angie.slug).exists())
        self.assertTrue(User.objects.filter(username=self.bob.slug).exists())
        self.assertTrue(User.objects.filter(username=self.chris.slug).exists())
        self.assertTrue(User.objects.filter(username=self.dave.slug).exists())

    def test__save__name_change_triggers_slug_change(self):
        dave = Cleaner.objects.get(name='dave')
        dave.name = 'eric'
        dave.save()

        self.assertEqual(Cleaner.objects.get(name='eric').slug, 'eric')
        self.assertTrue(User.objects.filter(username=Cleaner.objects.get(name='eric').slug).exists())

        dave = Cleaner.objects.get(name='eric')
        dave.name = 'dave'
        dave.save()

        self.assertEqual(Cleaner.objects.get(name='dave').slug, 'dave')
        self.assertTrue(User.objects.filter(username=Cleaner.objects.get(name='dave').slug).exists())

    def test__save_and_delete(self):
        cleaner = Cleaner.objects.create(name='eric')

        self.assertEqual(Cleaner.objects.get(name='eric').slug, 'eric')
        self.assertTrue(User.objects.filter(username=cleaner.slug).exists())

        cleaner.delete()

        self.assertFalse(Cleaner.objects.filter(name='eric').exists())
        self.assertFalse(User.objects.filter(username='eric').exists())
