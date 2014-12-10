from django.test import TestCase
from django_dynamic_fixture import G

from entity_event.admin import AdminEventForm
from entity_event.models import Source, Event


class AdminEventFormSaveTest(TestCase):
    def setUp(self):
        source = G(Source)
        self.form_data = {
            'source': source.id,
            'text': 'test text',
        }

    def test_new_obj(self):
        form = AdminEventForm(self.form_data)
        form.is_valid()
        form.save()
        self.assertEqual(Event.objects.count(), 1)


class AdminEventFormSaveM2MTest(TestCase):
    def setUp(self):
        source = G(Source)
        self.form_data = {
            'source': source.id,
            'text': 'test text',
        }

    def test_does_nothing(self):
        form = AdminEventForm(self.form_data)
        form.save_m2m()
        self.assertEqual(Event.objects.count(), 0)
