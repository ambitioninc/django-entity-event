from django.test import SimpleTestCase, TestCase
from django.test.utils import override_settings
from django_dynamic_fixture import N, G
from mock import patch

from entity_event import context_loader
from entity_event import models
from entity_event.tests import models as test_models


class TestGetDefaultRenderingStyle(TestCase):
    def test_none_defined(self):
        self.assertIsNone(context_loader.get_default_rendering_style())

    @override_settings(DEFAULT_ENTITY_EVENT_RENDERING_STYLE='short')
    def test_defined(self):
        rs = G(models.RenderingStyle, name='short')
        self.assertEquals(context_loader.get_default_rendering_style(), rs)


class TestGetContextHintsFromSource(SimpleTestCase):
    def test_no_context_renderers(self):
        res = context_loader.get_context_hints_per_source([])
        self.assertEquals(res, {})

    @patch.object(models.ContextRenderer, 'get_sources', spec_set=True)
    def test_one_context_renderer(self, mock_get_sources):
        source = N(models.Source, id=1)
        mock_get_sources.return_value = [source]
        res = context_loader.get_context_hints_per_source([
            N(models.ContextRenderer, source=source, context_hints={
                'key': {
                    'app_name': 'entity_event.tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk'],
                },
            })
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
        source1 = N(models.Source, id=1)
        source2 = N(models.Source, id=2)
        res = context_loader.get_context_hints_per_source([
            N(models.ContextRenderer, source=source1, context_hints={
                'key': {
                    'app_name': 'entity_event.tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk'],
                    'prefetch_related': ['prefetch1', 'prefetch2'],
                },
            }),
            N(models.ContextRenderer, source=source1, context_hints={
                'key': {
                    'app_name': 'entity_event.tests',
                    'model_name': 'TestModel',
                    'select_related': ['fk1'],
                    'prefetch_related': ['prefetch2', 'prefetch3'],
                },
            }),
            N(models.ContextRenderer, source=source2, context_hints={
                'key2': {
                    'app_name': 'entity_event.tests2',
                    'model_name': 'TestModel2',
                    'select_related': ['fk2'],
                    'prefetch_related': ['prefetch5', 'prefetch6'],
                },
            })
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
        source = N(models.Source, id=1)
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
        source = N(models.Source, id=1)
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
        source = N(models.Source, id=1)
        source2 = N(models.Source, id=2)
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
        source = N(models.Source, id=1)
        source2 = N(models.Source, id=2)
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
        source = N(models.Source, id=1)
        source2 = N(models.Source, id=2)
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
        e = N(models.Event, id=1, context={})
        self.assertEquals(context_loader.get_model_ids_to_fetch([e], {}), {})

    def test_w_one_event_one_context_hint_single_pk(self):
        source = N(models.Source, id=1)
        hints = {
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                },
            },
        }
        e = N(models.Event, context={'key': 2}, source=source)
        self.assertEquals(context_loader.get_model_ids_to_fetch([e], hints), {
            test_models.TestModel: set([2])
        })

    def test_w_one_event_one_context_hint_list_pks(self):
        source = N(models.Source, id=1)
        hints = {
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                },
            },
        }
        e = N(models.Event, context={'key': [2, 3, 5]}, source=source)
        self.assertEquals(context_loader.get_model_ids_to_fetch([e], hints), {
            test_models.TestModel: set([2, 3, 5])
        })

    def test_w_multiple_events_one_context_hint_list_pks(self):
        source = N(models.Source, id=1)
        hints = {
            source: {
                'key': {
                    'app_name': 'tests',
                    'model_name': 'TestModel',
                },
            },
        }
        e1 = N(models.Event, context={'key': [2, 3, 5]}, source=source)
        e2 = N(models.Event, context={'key': 88}, source=source)
        self.assertEquals(context_loader.get_model_ids_to_fetch([e1, e2], hints), {
            test_models.TestModel: set([2, 3, 5, 88])
        })

    def test_w_multiple_events_multiple_context_hints_list_pks(self):
        source1 = N(models.Source, id=1)
        source2 = N(models.Source, id=2)
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
        e1 = N(models.Event, context={'key': [2, 3, 5]}, source=source1)
        e2 = N(models.Event, context={'key': 88}, source=source1)
        e3 = N(models.Event, context={'key': 100, 'key2': [50]}, source=source2)
        e4 = N(models.Event, context={'key2': [60]}, source=source2)
        self.assertEquals(context_loader.get_model_ids_to_fetch([e1, e2, e3, e4], hints), {
            test_models.TestModel: set([2, 3, 5, 88, 100]),
            test_models.TestFKModel: set([50, 60])
        })


class FetchModelDataTest(TestCase):
    def test_none(self):
        self.assertEquals({}, context_loader.fetch_model_data({}, {}))

    def test_one_model_one_id_to_fetch(self):
        m1 = G(test_models.TestModel)
        self.assertEquals({
            test_models.TestModel: {m1.id: m1}
        }, context_loader.fetch_model_data({
            test_models.TestModel: test_models.TestModel.objects
        }, {
            test_models.TestModel: [m1.id]
        }))

    def test_multiple_models_multiple_ids_to_fetch(self):
        m1 = G(test_models.TestModel)
        m2 = G(test_models.TestModel)
        m3 = G(test_models.TestFKModel)
        self.assertEquals({
            test_models.TestModel: {m1.id: m1, m2.id: m2},
            test_models.TestFKModel: {m3.id: m3}
        }, context_loader.fetch_model_data({
            test_models.TestModel: test_models.TestModel.objects,
            test_models.TestFKModel: test_models.TestFKModel.objects,
        }, {
            test_models.TestModel: [m1.id, m2.id],
            test_models.TestFKModel: [m3.id],
        }))


class LoadFetchedObjectsIntoContextsTest(SimpleTestCase):
    def test_none(self):
        context_loader.load_fetched_objects_into_contexts([], {}, {})

    def test_event_with_no_model_data(self):
        e = N(models.Event, id=1, context={'hi', 'hi'})
        context_loader.load_fetched_objects_into_contexts([e], {}, {})
        self.assertEquals(e, e)

    def test_one_event_w_model_data(self):
        m = N(test_models.TestModel, id=2)
        s = N(models.Source, id=1)
        hints = {
            s: {
                'key': {
                    'model_name': 'TestModel',
                    'app_name': 'tests',
                }
            }
        }
        e = N(models.Event, context={'key': m.id}, source=s)
        context_loader.load_fetched_objects_into_contexts([e], {test_models.TestModel: {m.id: m}}, hints)
        self.assertEquals(e.context, {'key': m})

    def test_one_event_w_list_model_data(self):
        m1 = N(test_models.TestModel, id=2)
        m2 = N(test_models.TestModel, id=3)
        s = N(models.Source, id=1)
        hints = {
            s: {
                'key': {
                    'model_name': 'TestModel',
                    'app_name': 'tests',
                }
            }
        }
        e = N(models.Event, context={'key': [m1.id, m2.id]}, source=s)
        context_loader.load_fetched_objects_into_contexts([e], {test_models.TestModel: {m1.id: m1, m2.id: m2}}, hints)
        self.assertEquals(e.context, {'key': [m1, m2]})


class TestLoadRenderersIntoEvents(SimpleTestCase):
    def test_no_mediums_or_renderers(self):
        events = [N(models.Event, context={})]
        context_loader.load_renderers_into_events(events, [], [], None)
        self.assertEquals(events[0]._context_renderers, {})

    def test_mediums_and_no_renderers(self):
        events = [N(models.Event, context={})]
        mediums = [N(models.Medium)]
        context_loader.load_renderers_into_events(events, mediums, [], None)
        self.assertEquals(events[0]._context_renderers, {})

    def test_mediums_w_renderers(self):
        s1 = N(models.Source, id=1)
        s2 = N(models.Source, id=2)
        e1 = N(models.Event, context={}, source=s1)
        e2 = N(models.Event, context={}, source=s2)
        rg1 = N(models.RenderingStyle, id=1)
        rg2 = N(models.RenderingStyle, id=2)
        m1 = N(models.Medium, id=1, rendering_style=rg1)
        m2 = N(models.Medium, id=2, rendering_style=rg2)
        cr1 = N(models.ContextRenderer, source=s1, rendering_style=rg1, id=1)
        cr2 = N(models.ContextRenderer, source=s2, rendering_style=rg1, id=2)
        cr3 = N(models.ContextRenderer, source=s1, rendering_style=rg2, id=3)

        context_loader.load_renderers_into_events([e1, e2], [m1, m2], [cr1, cr2, cr3], None)

        self.assertEquals(e1._context_renderers, {
            m1: cr1,
            m2: cr3,
        })
        self.assertEquals(e2._context_renderers, {
            m1: cr2
        })

    def test_mediums_w_source_group_renderers(self):
        s1 = N(models.Source, id=1, group=N(models.SourceGroup, id=1))
        s2 = N(models.Source, id=2, group=N(models.SourceGroup, id=1))
        e1 = N(models.Event, context={}, source=s1)
        e2 = N(models.Event, context={}, source=s2)
        rs1 = N(models.RenderingStyle, id=1)
        rs2 = N(models.RenderingStyle, id=2)
        m1 = N(models.Medium, id=1, rendering_style=rs1)
        m2 = N(models.Medium, id=2, rendering_style=rs2)
        cr1 = N(models.ContextRenderer, source_group=s1.group, rendering_style=rs1, id=1)
        cr2 = N(models.ContextRenderer, source_group=s1.group, rendering_style=rs2, id=2)

        context_loader.load_renderers_into_events([e1, e2], [m1, m2], [cr1, cr2], None)

        self.assertEquals(e1._context_renderers, {
            m1: cr1,
            m2: cr2,
        })
        self.assertEquals(e2._context_renderers, {
            m1: cr1,
            m2: cr2,
        })

    def test_mediums_w_source_group_renderers_default(self):
        s1 = N(models.Source, id=1, group=N(models.SourceGroup, id=1))
        s2 = N(models.Source, id=2, group=N(models.SourceGroup, id=1))
        e1 = N(models.Event, context={}, source=s1)
        e2 = N(models.Event, context={}, source=s2)
        rs1 = N(models.RenderingStyle, id=1)
        rs2 = N(models.RenderingStyle, id=2)
        m1 = N(models.Medium, id=1, rendering_style=rs2)
        m2 = N(models.Medium, id=2, rendering_style=rs2)
        cr1 = N(models.ContextRenderer, source_group=s1.group, rendering_style=rs1, id=1)

        context_loader.load_renderers_into_events([e1, e2], [m1, m2], [cr1], rs1)

        self.assertEquals(e1._context_renderers, {
            m1: cr1,
            m2: cr1,
        })
        self.assertEquals(e2._context_renderers, {
            m1: cr1,
            m2: cr1,
        })

    def test_mediums_w_renderers_default_source(self):
        s1 = N(models.Source, id=1)
        s2 = N(models.Source, id=2)
        e1 = N(models.Event, context={}, source=s1)
        e2 = N(models.Event, context={}, source=s2)
        rs1 = N(models.RenderingStyle, id=1)
        rs2 = N(models.RenderingStyle, id=2)
        m1 = N(models.Medium, id=1, rendering_style=rs1)
        m2 = N(models.Medium, id=2, rendering_style=rs1)
        cr1 = N(models.ContextRenderer, source=s1, rendering_style=rs1, id=1)
        cr2 = N(models.ContextRenderer, source=s2, rendering_style=rs1, id=2)
        cr3 = N(models.ContextRenderer, source=s1, rendering_style=rs2, id=3)

        default_style = rs1

        context_loader.load_renderers_into_events([e1, e2], [m1, m2], [cr1, cr2, cr3], default_style)

        self.assertEquals(e1._context_renderers, {
            m1: cr1,
            m2: cr1,
        })
        self.assertEquals(e2._context_renderers, {
            m1: cr2,
            m2: cr2,
        })


class LoadContextsAndRenderersTest(TestCase):
    """
    Integration tests for loading contexts and renderers into events.
    """
    def test_none(self):
        context_loader.load_contexts_and_renderers([], [])

    def test_no_mediums(self):
        e = G(models.Event, context={})
        context_loader.load_contexts_and_renderers([e], [])
        self.assertEquals(e.context, {})

    def test_one_render_target_one_event(self):
        m1 = G(test_models.TestModel)
        s = G(models.Source)
        rg = G(models.RenderingStyle)
        e = G(models.Event, context={'key': m1.id}, source=s)
        medium = G(models.Medium, source=s, rendering_style=rg)
        G(models.ContextRenderer, rendering_style=rg, source=s, context_hints={
            'key': {
                'model_name': 'TestModel',
                'app_name': 'tests',
            }
        })

        context_loader.load_contexts_and_renderers([e], [medium])
        self.assertEquals(e.context, {'key': m1})

    @override_settings(DEFAULT_ENTITY_EVENT_RENDERING_STYLE='short')
    def test_one_render_target_one_event_no_style_with_default(self):
        m1 = G(test_models.TestModel)
        s = G(models.Source)
        rs = G(models.RenderingStyle, name='short')
        e = G(models.Event, context={'key': m1.id}, source=s)
        medium = G(models.Medium, source=s, rendering_style=None)
        G(models.ContextRenderer, rendering_style=rs, source=s, context_hints={
            'key': {
                'model_name': 'TestModel',
                'app_name': 'tests',
            }
        })

        context_loader.load_contexts_and_renderers([e], [medium])
        self.assertEquals(e.context, {'key': m1})

    def test_multiple_render_targets_multiple_events(self):
        test_m1 = G(test_models.TestModel)
        test_m2 = G(test_models.TestModel)
        test_m3 = G(test_models.TestModel)
        test_fk_m1 = G(test_models.TestFKModel)
        test_fk_m2 = G(test_models.TestFKModel)
        s1 = G(models.Source)
        s2 = G(models.Source)
        rg1 = G(models.RenderingStyle)
        rg2 = G(models.RenderingStyle)
        medium1 = G(models.Medium, source=s1, rendering_style=rg1)
        medium2 = G(models.Medium, source=s2, rendering_style=rg2)

        cr1 = G(models.ContextRenderer, rendering_style=rg1, source=s1, context_hints={
            'key': {
                'model_name': 'TestModel',
                'app_name': 'tests',
            }
        })
        cr2 = G(models.ContextRenderer, rendering_style=rg2, source=s2, context_hints={
            'key': {
                'model_name': 'TestModel',
                'app_name': 'tests',
            },
            'key2': {
                'model_name': 'TestFKModel',
                'app_name': 'tests',
            }
        })

        e1 = G(models.Event, context={'key': test_m1.id, 'key2': 'haha'}, source=s1)
        e2 = G(models.Event, context={'key': [test_m2.id, test_m3.id]}, source=s1)
        e3 = G(models.Event, context={'key2': test_fk_m1.id, 'key': test_m1.id}, source=s2)
        e4 = G(models.Event, context={'key2': test_fk_m2.id}, source=s2)

        context_loader.load_contexts_and_renderers([e1, e2, e3, e4], [medium1, medium2])
        self.assertEquals(e1.context, {'key': test_m1, 'key2': 'haha'})
        self.assertEquals(e2.context, {'key': [test_m2, test_m3]})
        self.assertEquals(e3.context, {'key2': test_fk_m1, 'key': test_m1})
        self.assertEquals(e4.context, {'key2': test_fk_m2})

        # Verify context renderers are put into the events properly
        self.assertEquals(e1._context_renderers, {
            medium1: cr1,
        })
        self.assertEquals(e2._context_renderers, {
            medium1: cr1,
        })
        self.assertEquals(e3._context_renderers, {
            medium2: cr2,
        })
        self.assertEquals(e4._context_renderers, {
            medium2: cr2,
        })

    @override_settings(DEFAULT_ENTITY_EVENT_RENDERING_STYLE='short')
    def test_multiple_render_targets_multiple_events_use_default(self):
        """
        Tests the case when a context renderer is not available for a rendering style
        but the default style is used instead.
        """
        test_m1 = G(test_models.TestModel)
        test_m2 = G(test_models.TestModel)
        test_m3 = G(test_models.TestModel)
        test_fk_m1 = G(test_models.TestFKModel)
        test_fk_m2 = G(test_models.TestFKModel)
        s1 = G(models.Source)
        s2 = G(models.Source)
        rs1 = G(models.RenderingStyle, name='short')
        rs2 = G(models.RenderingStyle)
        medium1 = G(models.Medium, rendering_style=rs1)
        medium2 = G(models.Medium, rendering_style=rs2)

        cr1 = G(models.ContextRenderer, rendering_style=rs1, source=s1, context_hints={
            'key': {
                'model_name': 'TestModel',
                'app_name': 'tests',
            }
        })
        cr2 = G(models.ContextRenderer, rendering_style=rs1, source=s2, context_hints={
            'key': {
                'model_name': 'TestModel',
                'app_name': 'tests',
            },
            'key2': {
                'model_name': 'TestFKModel',
                'app_name': 'tests',
            }
        })

        e1 = G(models.Event, context={'key': test_m1.id, 'key2': 'haha'}, source=s1)
        e2 = G(models.Event, context={'key': [test_m2.id, test_m3.id]}, source=s1)
        e3 = G(models.Event, context={'key2': test_fk_m1.id, 'key': test_m1.id}, source=s2)
        e4 = G(models.Event, context={'key2': test_fk_m2.id}, source=s2)

        context_loader.load_contexts_and_renderers([e1, e2, e3, e4], [medium1, medium2])
        self.assertEquals(e1.context, {'key': test_m1, 'key2': 'haha'})
        self.assertEquals(e2.context, {'key': [test_m2, test_m3]})
        self.assertEquals(e3.context, {'key2': test_fk_m1, 'key': test_m1})
        self.assertEquals(e4.context, {'key2': test_fk_m2})

        # Verify context renderers are put into the events properly
        self.assertEquals(e1._context_renderers, {
            medium1: cr1,
            medium2: cr1,
        })
        self.assertEquals(e2._context_renderers, {
            medium1: cr1,
            medium2: cr1,
        })
        self.assertEquals(e3._context_renderers, {
            medium1: cr2,
            medium2: cr2,
        })
        self.assertEquals(e4._context_renderers, {
            medium1: cr2,
            medium2: cr2,
        })

    def test_optimal_queries(self):
        fk1 = G(test_models.TestFKModel)
        fk11 = G(test_models.TestFKModel)
        fk2 = G(test_models.TestFKModel2)
        test_m1 = G(test_models.TestModel, fk=fk1, fk2=fk2)
        test_m1.fk_m2m.add(fk1, fk11)
        test_m2 = G(test_models.TestModel, fk=fk1, fk2=fk2)
        test_m2.fk_m2m.add(fk1, fk11)
        test_m3 = G(test_models.TestModel, fk=fk1, fk2=fk2)
        test_fk_m1 = G(test_models.TestFKModel)
        test_fk_m2 = G(test_models.TestFKModel)
        s1 = G(models.Source)
        s2 = G(models.Source)
        rg1 = G(models.RenderingStyle)
        rg2 = G(models.RenderingStyle)
        medium1 = G(models.Medium, source=s1, rendering_style=rg1)
        medium2 = G(models.Medium, source=s2, rendering_style=rg2)

        G(models.ContextRenderer, rendering_style=rg1, source=s1, context_hints={
            'key': {
                'model_name': 'TestModel',
                'app_name': 'tests',
                'select_related': ['fk'],
            }
        })
        G(models.ContextRenderer, rendering_style=rg2, source=s2, context_hints={
            'key': {
                'model_name': 'TestModel',
                'app_name': 'tests',
                'select_related': ['fk2'],
                'prefetch_related': ['fk_m2m'],
            },
            'key2': {
                'model_name': 'TestFKModel',
                'app_name': 'tests',
            }
        })

        e1 = G(models.Event, context={'key': test_m1.id, 'key2': 'haha'}, source=s1)
        e2 = G(models.Event, context={'key': [test_m2.id, test_m3.id]}, source=s1)
        e3 = G(models.Event, context={'key2': test_fk_m1.id, 'key': test_m1.id}, source=s2)
        e4 = G(models.Event, context={'key2': test_fk_m2.id}, source=s2)

        with self.assertNumQueries(6):
            context_loader.load_contexts_and_renderers([e1, e2, e3, e4], [medium1, medium2])
            self.assertEquals(e1.context['key'].fk, fk1)
            self.assertEquals(e2.context['key'][0].fk, fk1)
            self.assertEquals(e1.context['key'].fk2, fk2)
            self.assertEquals(e2.context['key'][0].fk2, fk2)
            self.assertEquals(set(e1.context['key'].fk_m2m.all()), set([fk1, fk11]))
            self.assertEquals(set(e2.context['key'][0].fk_m2m.all()), set([fk1, fk11]))
            self.assertEquals(e3.context['key'].fk, fk1)
