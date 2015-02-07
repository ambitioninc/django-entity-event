from django.test import SimpleTestCase
from django_dynamic_fixture import N

from entity_event import context_loader
from entity_event import models


class TestGetContextHintsFromSource(SimpleTestCase):
    def test_no_context_renderers(self):
        res = context_loader.get_context_hints_per_source([])
        self.assertEquals(res, {})

    def test_one_context_renderer(self):
        source = N(models.Source, persist_dependencies=False)
        res = context_loader.get_context_hints_per_source([
            N(models.ContextRenderer, source=source, context_hints={
                'key': {
                    'app_name': 'entity_event.tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk'],
                },
            }, persist_dependencies=False)
        ])
        self.assertEquals(res, {
            source: {
                'key': {
                    'app_name': 'entity_event.tests',
                    'model_name': 'TestModel',
                    'select_related': set(['fk']),
                    'prefetch_related': set(),
                }
            }
        })

    def test_multiple_context_renderers_over_multiple_source(self):
        source1 = N(models.Source, persist_dependencies=False, id=1)
        source2 = N(models.Source, persist_dependencies=False, id=2)
        res = context_loader.get_context_hints_per_source([
            N(models.ContextRenderer, source=source1, context_hints={
                'key': {
                    'app_name': 'entity_event.tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk'],
                    'prefetch_related': ['prefetch1', 'prefetch2'],
                },
            }, persist_dependencies=False),
            N(models.ContextRenderer, source=source1, context_hints={
                'key': {
                    'app_name': 'entity_event.tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk1'],
                    'prefetch_related': ['prefetch2', 'prefetch3'],
                },
            }, persist_dependencies=False),
            N(models.ContextRenderer, source=source2, context_hints={
                'key2': {
                    'app_name': 'entity_event.tests2',
                    'model_name': 'TestModel2',
                    'select_related': ['fk2'],
                    'prefetch_related': ['prefetch5', 'prefetch6'],
                },
            }, persist_dependencies=False)
        ])
        self.assertEquals(res, {
            source1: {
                'key': {
                    'app_name': 'entity_event.tests',
                    'model_name': 'TestModel',
                    'select_related': set(['fk', 'fk1']),
                    'prefetch_related': set(['prefetch1', 'prefetch2', 'prefetch3']),
                }
            },
            source2: {
                'key2': {
                    'app_name': 'entity_event.tests2',
                    'model_name': 'TestModel2',
                    'select_related': set(['fk2']),
                    'prefetch_related': set(['prefetch5', 'prefetch6']),
                }
            },
        })
