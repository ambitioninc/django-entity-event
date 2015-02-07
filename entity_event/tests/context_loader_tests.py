from django.test import SimpleTestCase, TestCase
from django_dynamic_fixture import N, G

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

    def test_multiple_context_hints_w_multiple_select_related_multiple_prefetch_related(self):
        source = N(models.Source, persist_dependencies=False, id=1)
        source2 = N(models.Source, persist_dependencies=False, id=2)
        qsets = context_loader.get_querysets_for_context_hints({
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk'],
                    'prefetch_related': ['fk_m2m'],
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

        # Verify the raw sql to ensure select relateds will happen. Note that prefetch relateds are not
        # included in raw sql
        raw_sql = (
            'SELECT "tests_testmodel"."id", "tests_testmodel"."value", "tests_testmodel"."fk_id", '
            '"tests_testmodel"."fk2_id", '
            '"tests_testfkmodel"."id", "tests_testfkmodel"."value", '
            '"tests_testfkmodel2"."id", "tests_testfkmodel2"."value" FROM "tests_testmodel" INNER JOIN '
            '"tests_testfkmodel" ON ( "tests_testmodel"."fk_id" = "tests_testfkmodel"."id" ) '
            'INNER JOIN "tests_testfkmodel2" ON ( "tests_testmodel"."fk2_id" = "tests_testfkmodel2"."id" )'
        )

        self.assertEquals(str(qsets[test_models.TestModel].query), raw_sql)


class TestGetQuerysetsForContextHintsDbTests(TestCase):
    def test_multiple_context_hints_w_multiple_select_related_multiple_prefetch_related(self):
        source = N(models.Source, persist_dependencies=False, id=1)
        source2 = N(models.Source, persist_dependencies=False, id=2)
        qsets = context_loader.get_querysets_for_context_hints({
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk'],
                    'prefetch_related': ['fk_m2m'],
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

        # Create objects to query in order to test optimal number of queries
        fk = G(test_models.TestFKModel)
        fk2 = G(test_models.TestFKModel2)
        o = G(test_models.TestModel, fk=fk, fk2=fk2)
        m2ms = [G(test_models.TestFKModel), G(test_models.TestFKModel)]
        o.fk_m2m.add(*m2ms)

        with self.assertNumQueries(2):
            v = qsets[test_models.TestModel].get(id=o.id)
            self.assertEquals(v.fk, fk)
            self.assertEquals(v.fk2, fk2)
            self.assertEquals(set(v.fk_m2m.all()), set(m2ms))


class DictFindTest(SimpleTestCase):
    def test_dict_find_none(self):
        self.assertEquals(list(context_loader.dict_find({}, 'key')), [])

    def test_dict_find_list_key(self):
        d = {'key': ['value']}
        self.assertEquals(list(context_loader.dict_find(d, 'key')), [(d, ['value'])])

    def test_dict_find_nested_list_key(self):
        d = {'key': ['value']}
        larger_dict = {
            'l': [{
                'hi': {},
            }, {
                'hi2': d
            }]
        }
        self.assertEquals(list(context_loader.dict_find(larger_dict, 'key')), [(d, ['value'])])

    def test_dict_find_double_nested_list_key(self):
        d = {'key': ['value']}
        larger_dict = {
            'l': [{
                'hi': {},
            }, {
                'hi2': d
            }],
            'hi3': d
        }
        self.assertEquals(list(context_loader.dict_find(larger_dict, 'key')), [(d, ['value']), (d, ['value'])])

    def test_dict_find_deep_nested_list_key(self):
        d = {'key': ['value']}
        larger_dict = [[{
            'l': [{
                'hi': {},
            }, {
                'hi2': d
            }],
            'hi3': d
        }]]
        self.assertEquals(list(context_loader.dict_find(larger_dict, 'key')), [(d, ['value']), (d, ['value'])])


class GetModelIdsToFetchTest(SimpleTestCase):
    def test_no_events(self):
        self.assertEquals(context_loader.get_model_ids_to_fetch([], {}), {})

    def test_no_context_hints(self):
        e = N(models.Event, context={}, persist_dependencies=False)
        self.assertEquals(context_loader.get_model_ids_to_fetch([e], {}), {})

    def test_w_one_event_one_context_hint_single_pk(self):
        source = N(models.Source, persist_dependencies=False, id=1)
        hints = {
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                },
            },
        }
        e = N(models.Event, context={'key': 2}, persist_dependencies=False, source=source)
        self.assertEquals(context_loader.get_model_ids_to_fetch([e], hints), {
            test_models.TestModel: set([2])
        })

    def test_w_one_event_one_context_hint_list_pks(self):
        source = N(models.Source, persist_dependencies=False, id=1)
        hints = {
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                },
            },
        }
        e = N(models.Event, context={'key': [2, 3, 5]}, persist_dependencies=False, source=source)
        self.assertEquals(context_loader.get_model_ids_to_fetch([e], hints), {
            test_models.TestModel: set([2, 3, 5])
        })

    def test_w_multiple_events_one_context_hint_list_pks(self):
        source = N(models.Source, persist_dependencies=False, id=1)
        hints = {
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                },
            },
        }
        e1 = N(models.Event, context={'key': [2, 3, 5]}, persist_dependencies=False, source=source)
        e2 = N(models.Event, context={'key': 88}, persist_dependencies=False, source=source)
        self.assertEquals(context_loader.get_model_ids_to_fetch([e1, e2], hints), {
            test_models.TestModel: set([2, 3, 5, 88])
        })

    def test_w_multiple_events_multiple_context_hints_list_pks(self):
        source1 = N(models.Source, persist_dependencies=False, id=1)
        source2 = N(models.Source, persist_dependencies=False, id=2)
        hints = {
            source1: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                },
            },
            source2: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                },
                'key2': {
                    'app_name': 'tests',
                    'model_name': 'TestFKModel',
                },
            },
        }
        e1 = N(models.Event, context={'key': [2, 3, 5]}, persist_dependencies=False, source=source1)
        e2 = N(models.Event, context={'key': 88}, persist_dependencies=False, source=source1)
        e3 = N(models.Event, context={'key': 100, 'key2': [50]}, persist_dependencies=False, source=source2)
        e4 = N(models.Event, context={'key2': [60]}, persist_dependencies=False, source=source2)
        self.assertEquals(context_loader.get_model_ids_to_fetch([e1, e2, e3, e4], hints), {
            test_models.TestModel: set([2, 3, 5, 88, 100]),
            test_models.TestFKModel: set([50, 60])
        })
