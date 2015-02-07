from django.test import SimpleTestCase
from django_dynamic_fixture import N

from entity_event import context_loader
from entity_event import models
from entity_event.tests import models as test_models


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


class TestGetQuerysetsForContextHints(SimpleTestCase):
    def test_no_context_hints(self):
        qsets = context_loader.get_querysets_for_context_hints({})
        self.assertEquals(qsets, {})

    def test_one_context_hint_no_select_related(self):
        source = N(models.Source, persist_dependencies=False, id=1)
        qsets = context_loader.get_querysets_for_context_hints({
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                },
            },
        })
        self.assertEquals(qsets, {
            test_models.TestModel: test_models.TestModel.objects
        })

    def test_one_context_hint_w_select_related(self):
        source = N(models.Source, persist_dependencies=False, id=1)
        qsets = context_loader.get_querysets_for_context_hints({
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk'],
                },
            },
        })
        # Verify the raw sql to ensure select relateds will happen
        raw_sql = (
            'SELECT "tests_testmodel"."id", "tests_testmodel"."value", "tests_testmodel"."fk_id", '
            '"tests_testmodel"."fk2_id", '
            '"tests_testfkmodel"."id", "tests_testfkmodel"."value" FROM "tests_testmodel" INNER JOIN '
            '"tests_testfkmodel" ON ( "tests_testmodel"."fk_id" = "tests_testfkmodel"."id" )'
        )

        self.assertEquals(str(qsets[test_models.TestModel].query), raw_sql)

    def test_multiple_context_hints_w_multiple_select_related(self):
        source = N(models.Source, persist_dependencies=False, id=1)
        source2 = N(models.Source, persist_dependencies=False, id=2)
        qsets = context_loader.get_querysets_for_context_hints({
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk'],
                },
            },
            source2: {
                'key2': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk2'],
                },
            }
        })
        # Verify the raw sql to ensure select relateds will happen
        raw_sql = (
            'SELECT "tests_testmodel"."id", "tests_testmodel"."value", "tests_testmodel"."fk_id", '
            '"tests_testmodel"."fk2_id", '
            '"tests_testfkmodel"."id", "tests_testfkmodel"."value", '
            '"tests_testfkmodel2"."id", "tests_testfkmodel2"."value" FROM "tests_testmodel" INNER JOIN '
            '"tests_testfkmodel" ON ( "tests_testmodel"."fk_id" = "tests_testfkmodel"."id" ) '
            'INNER JOIN "tests_testfkmodel2" ON ( "tests_testmodel"."fk2_id" = "tests_testfkmodel2"."id" )'
        )

        self.assertEquals(str(qsets[test_models.TestModel].query), raw_sql)
