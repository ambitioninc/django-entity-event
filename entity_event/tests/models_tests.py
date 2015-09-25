from datetime import datetime

from django.template import Template
from django.test import TestCase, SimpleTestCase
from django_dynamic_fixture import N, G
from entity.models import Entity, EntityKind, EntityRelationship
from freezegun import freeze_time
from mock import patch, call, Mock
from six import text_type

from entity_event.models import (
    Medium, Source, SourceGroup, Unsubscription, Subscription, Event, EventActor, EventSeen,
    RenderingStyle, ContextRenderer, _unseen_event_ids, SubscriptionQuerySet,
    EventQuerySet, EventManager
)
from entity_event.tests.models import TestFKModel


class EventRenderTest(TestCase):
    """
    Does an entire integration test for rendering events relative to mediums.
    """
    def test_one_context_renderer_one_medium_w_additional_context(self):
        rg = G(RenderingStyle)
        s = G(Source)
        G(
            ContextRenderer, source=s, rendering_style=rg, text_template_path='test_template.txt',
            html_template_path='test_template.html', context_hints={
                'fk_model': {
                    'app_name': 'tests',
                    'model_name': 'TestFKModel',
                }
            })
        m = G(Medium, rendering_style=rg, additional_context={'suppress_value': True})

        fkm = G(TestFKModel, value=100)
        G(Event, source=s, context={'fk_model': fkm.id})

        events = Event.objects.all().load_contexts_and_renderers(m)
        txt, html = events[0].render(m)

        self.assertEquals(txt, 'Test text template with value 100')
        self.assertEquals(html, 'Test html template with value suppressed')

    def test_one_context_renderer_one_medium(self):
        rg = G(RenderingStyle)
        s = G(Source)
        G(
            ContextRenderer, source=s, rendering_style=rg, text_template_path='test_template.txt',
            html_template_path='test_template.html', context_hints={
                'fk_model': {
                    'app_name': 'tests',
                    'model_name': 'TestFKModel',
                }
            })
        m = G(Medium, rendering_style=rg)

        fkm = G(TestFKModel, value=100)
        G(Event, source=s, context={'fk_model': fkm.id})

        events = Event.objects.all().load_contexts_and_renderers(m)
        txt, html = events[0].render(m)

        self.assertEquals(txt, 'Test text template with value 100')
        self.assertEquals(html, 'Test html template with value 100')

    def test_wo_fetching_contexts(self):
        rg = G(RenderingStyle)
        s = G(Source)
        G(
            ContextRenderer, source=s, rendering_style=rg, text_template_path='test_template.txt',
            html_template_path='test_template.html', context_hints={
                'fk_model': {
                    'app_name': 'tests',
                    'model_name': 'TestFKModel',
                }
            })
        m = G(Medium, rendering_style=rg)

        fkm = G(TestFKModel, value=100)
        e = G(Event, source=s, context={'fk_model': fkm.id})

        with self.assertRaises(RuntimeError):
            e.render(m)

    def test_get_serialized_context(self):
        rg = G(RenderingStyle)
        s = G(Source)
        G(
            ContextRenderer, source=s, rendering_style=rg, text_template_path='test_template.txt',
            html_template_path='test_template.html', context_hints={
                'fk_model': {
                    'app_name': 'tests',
                    'model_name': 'TestFKModel',
                }
            })
        m = G(Medium, rendering_style=rg, additional_context={'suppress_value': True})

        fkm = G(TestFKModel, value='100')
        G(Event, source=s, context={'fk_model': fkm.id})
        event = Event.objects.all().load_contexts_and_renderers(m)[0]

        # Call the method
        response = event.get_serialized_context(m)

        # Assert we have a proper response
        self.assertEqual(
            response,
            {
                'suppress_value': True,
                'fk_model': {
                    'id': fkm.id,
                    'value': fkm.value
                }
            }
        )

    def test_get_serialized_context_wo_fetching_context(self):
        rg = G(RenderingStyle)
        s = G(Source)
        G(
            ContextRenderer, source=s, rendering_style=rg, text_template_path='test_template.txt',
            html_template_path='test_template.html', context_hints={
                'fk_model': {
                    'app_name': 'tests',
                    'model_name': 'TestFKModel',
                }
            })
        m = G(Medium, rendering_style=rg, additional_context={'suppress_value': True})

        fkm = G(TestFKModel, value='100')
        event = G(Event, source=s, context={'fk_model': fkm.id})

        with self.assertRaises(RuntimeError):
            event.get_serialized_context(m)


class EventManagerCreateEventTest(TestCase):
    def test_create_event_no_actors(self):
        source = G(Source)
        e = Event.objects.create_event(context={'hi': 'hi'}, source=source)
        self.assertEqual(e.source, source)
        self.assertEqual(e.context, {'hi': 'hi'})
        self.assertEqual(e.uuid, '')
        self.assertFalse(EventActor.objects.exists())

    def test_create_event_multiple_actor_pks(self):
        source = G(Source)
        actors = [G(Entity), G(Entity)]
        e = Event.objects.create_event(context={'hi': 'hi'}, source=source, actors=[a.id for a in actors], uuid='hi')
        self.assertEqual(e.source, source)
        self.assertEqual(e.context, {'hi': 'hi'})
        self.assertEqual(e.uuid, 'hi')
        self.assertEqual(
            set(EventActor.objects.filter(event=e).values_list('entity', flat=True)), set([a.id for a in actors]))

    def test_create_event_multiple_actors(self):
        source = G(Source)
        actors = [G(Entity), G(Entity)]
        e = Event.objects.create_event(context={'hi': 'hi'}, source=source, actors=actors, uuid='hi')
        self.assertEqual(e.source, source)
        self.assertEqual(e.context, {'hi': 'hi'})
        self.assertEqual(e.uuid, 'hi')
        self.assertEqual(
            set(EventActor.objects.filter(event=e).values_list('entity', flat=True)), set([a.id for a in actors]))

    def test_ignore_duplicates_w_uuid_doesnt_already_exist(self):
        source = G(Source)
        e = Event.objects.create_event(context={'hi': 'hi'}, source=source, uuid='1', ignore_duplicates=True)
        self.assertIsNotNone(e)

    def test_ignore_duplicates_w_uuid_already_exist(self):
        source = G(Source)
        Event.objects.create_event(context={'hi': 'hi'}, source=source, uuid='1', ignore_duplicates=True)
        e = Event.objects.create_event(context={'hi': 'hi'}, source=source, uuid='1', ignore_duplicates=True)
        self.assertIsNone(e)

    def test_ignore_duplicates_wo_uuid_already_exist(self):
        source = G(Source)
        Event.objects.create_event(context={'hi': 'hi'}, source=source, ignore_duplicates=True)
        e = Event.objects.create_event(context={'hi': 'hi'}, source=source, ignore_duplicates=True)
        self.assertIsNone(e)


class EventManagerQuerySetTest(TestCase):
    def setUp(self):
        # Call the super setup
        super(EventManagerQuerySetTest, self).setUp()

        # Create a query set reference
        self.queryset = EventQuerySet()

        # Create a manager reference
        self.manager = EventManager()

    def test_mark_seen(self):
        event = G(Event, context={})
        medium = G(Medium)
        Event.objects.mark_seen(medium)
        self.assertEqual(EventSeen.objects.count(), 1)
        self.assertTrue(EventSeen.objects.filter(event=event, medium=medium).exists())

    @patch('entity_event.context_loader.load_contexts_and_renderers', spec_set=True)
    def test_load_contexts_and_renderers(self, mock_load_contexts_and_renderers):
        e = G(Event, context={})
        medium = G(Medium)
        Event.objects.load_contexts_and_renderers(medium)
        self.assertEquals(mock_load_contexts_and_renderers.call_count, 1)
        self.assertEquals(list(mock_load_contexts_and_renderers.call_args_list[0][0][0]), [e])
        self.assertEquals(mock_load_contexts_and_renderers.call_args_list[0][0][1], [medium])

    @patch.object(EventManager, 'get_queryset', autospec=True)
    def test_cache_related(self, mock_get_queryset):
        # Setup some mock return values
        mock_get_queryset.return_value = Mock(EventQuerySet(), autospec=True)

        # Call the method
        self.manager.cache_related()

        # Assert that we called get queryset
        mock_get_queryset.assert_called_once_with(self.manager)


class MediumEventsInterfacesTest(TestCase):
    def setUp(self):
        # Set Up Entities and Relationships
        everyone_kind = G(EntityKind, name='all', display_name='all')
        group_kind = G(EntityKind, name='group', display_name='Group')
        self.person_kind = G(EntityKind, name='person', display_name='Person')

        self.p1 = G(Entity, entity_kind=self.person_kind, display_name='p1')
        self.p2 = G(Entity, entity_kind=self.person_kind, display_name='p2')
        self.p3 = G(Entity, entity_kind=self.person_kind, display_name='p3')
        p4 = G(Entity, entity_kind=self.person_kind, display_name='p4')

        g1 = G(Entity, entity_kind=group_kind)
        g2 = G(Entity, entity_kind=group_kind)

        everyone = G(Entity, entity_kind=everyone_kind)

        for sup, sub in [(g1, self.p1), (g1, self.p2), (g2, self.p3), (g2, p4)]:
            G(EntityRelationship, super_entity=sup, sub_entity=sub)
        for p in [self.p1, self.p2, self.p3, p4]:
            G(EntityRelationship, super_entity=everyone, sub_entity=p)

        # Set up Mediums, Sources, Subscriptions, Events
        self.medium_x = G(Medium, name='x', display_name='x')
        self.medium_y = G(Medium, name='y', display_name='y')
        self.medium_z = G(Medium, name='z', display_name='z')
        self.source_a = G(Source, name='a', display_name='a')
        self.source_b = G(Source, name='b', display_name='b')
        self.source_c = G(Source, name='c', display_name='c')

        e1 = G(Event, source=self.source_a, context={})
        G(Event, source=self.source_a, context={})
        e3 = G(Event, source=self.source_b, context={})
        e4 = G(Event, source=self.source_c, context={})

        G(EventActor, event=e1, entity=self.p1)
        G(EventActor, event=e3, entity=self.p2)
        G(EventActor, event=e4, entity=self.p2)
        G(EventActor, event=e4, entity=self.p3)

        G(Subscription, source=self.source_a, medium=self.medium_x, only_following=False,
          entity=everyone, sub_entity_kind=self.person_kind)
        G(Subscription, source=self.source_a, medium=self.medium_y, only_following=True,
          entity=everyone, sub_entity_kind=self.person_kind)
        G(Subscription, source=self.source_c, medium=self.medium_z, only_following=True,
          entity=g1, sub_entity_kind=self.person_kind)

    def test_events_basic(self):
        events = self.medium_x.events()
        self.assertEqual(events.count(), 2)

    def test_events_only_following(self):
        events = self.medium_y.events()
        self.assertEqual(events.count(), 1)

    def test_entity_events_basic(self):
        events = self.medium_x.entity_events(entity=self.p1)
        self.assertEqual(len(events), 2)

    def test_entity_events_basic_mark_seen(self):
        events = self.medium_x.entity_events(entity=self.p1, seen=False, mark_seen=True)
        self.assertEqual(len(events), 2)
        # All unseen events should have been marked as seen, even if they werent related
        # to the entity
        self.assertEqual(len(EventSeen.objects.all()), 4)

    def test_entity_events_basic_unsubscribed(self):
        G(Unsubscription, entity=self.p1, source=self.source_a, medium=self.medium_x)
        G(Event, source=self.source_b, context={})
        G(Subscription, source=self.source_b, medium=self.medium_x, only_following=False,
          entity=self.p1, sub_entity_kind=None)
        events = self.medium_x.entity_events(entity=self.p1)
        self.assertEqual(len(events), 2)
        for event in events:
            self.assertEqual(event.source, self.source_b)

    def test_entity_events_only_following(self):
        events = self.medium_z.entity_events(entity=self.p2)
        self.assertEqual(len(events), 1)

    def test_entity_targets_basic(self):
        events_targets = self.medium_x.events_targets()
        self.assertEqual(len(events_targets), 2)

    def test_entity_targets_target_count(self):
        events_targets = self.medium_x.events_targets(entity_kind=self.person_kind)
        self.assertEqual(len(events_targets[0][1]), 4)

    def test_entity_targets_only_following(self):
        events_targets = self.medium_z.events_targets(entity_kind=self.person_kind)
        self.assertEqual(len(events_targets[0][1]), 1)


class MediumRenderTest(SimpleTestCase):
    @patch('entity_event.context_loader.load_contexts_and_renderers', spec_set=True)
    def test_render(self, mock_load_contexts_and_renderers):
        medium = N(Medium)
        e1 = Mock(render=Mock(return_value=('e1.txt', 'e1.html')))
        e2 = Mock(render=Mock(return_value=('e2.txt', 'e2.html')))

        events = [e1, e2]
        res = medium.render(events)

        mock_load_contexts_and_renderers.assert_called_once_with(events, [medium])
        self.assertEquals(res, {
            e1: ('e1.txt', 'e1.html'),
            e2: ('e2.txt', 'e2.html'),
        })
        e1.render.assert_called_once_with(medium)
        e2.render.assert_called_once_with(medium)


class MediumSubsetSubscriptionsTest(TestCase):
    def setUp(self):
        person = G(EntityKind, name='person', display_name='Person')
        self.super_e = G(Entity)
        self.sub_e = G(Entity, entity_kind=person)
        random = G(Entity)
        G(EntityRelationship, super_entity=self.super_e, sub_entity=self.sub_e)

        self.medium = G(Medium)
        self.group_sub = G(Subscription, entity=self.super_e, sub_entity_kind=person)
        self.indiv_sub = G(Subscription, entity=self.sub_e, sub_entity_kind=None)
        self.random_sub = G(Subscription, entity=random)

    def test_no_entity(self):
        all_subs = Subscription.objects.all()
        subs = self.medium.subset_subscriptions(all_subs)
        self.assertEqual(subs, all_subs)

    def test_sub_entity(self):
        all_subs = Subscription.objects.all()
        subs = self.medium.subset_subscriptions(all_subs, self.sub_e)
        self.assertEqual(subs.count(), 2)

    def test_super_not_included(self):
        all_subs = Subscription.objects.all()
        subs = self.medium.subset_subscriptions(all_subs, self.super_e)
        self.assertEqual(subs.count(), 0)


class MediumGetFilteredEventsTest(TestCase):
    def setUp(self):
        self.medium = G(Medium)

    def test_get_unseen_events_some_seen_some_not(self):
        seen_e = G(Event, context={})
        G(EventSeen, event=seen_e, medium=self.medium)
        unseen_e = G(Event, context={})

        events = self.medium.get_filtered_events(seen=False)
        self.assertEquals(list(events), [unseen_e])

    def test_get_unseen_events_some_seen_from_other_mediums(self):
        seen_from_other_medium_e = G(Event, context={})
        G(EventSeen, event=seen_from_other_medium_e)
        unseen_e = G(Event, context={})

        events = self.medium.get_filtered_events(seen=False)
        self.assertEquals(set(events), set([unseen_e, seen_from_other_medium_e]))


class MediumGetEventFiltersTest(TestCase):
    def setUp(self):
        self.medium = G(Medium)
        with freeze_time('2014-01-15'):
            e1 = G(Event, context={})
            G(Event, context={}, time_expires=datetime(5000, 1, 1))
        with freeze_time('2014-01-17'):
            G(Event, context={}), G(Event, context={})
            G(Event, context={}, time_expires=datetime(2014, 1, 17))
        G(EventSeen, event=e1, medium=self.medium)

        self.actor = G(Entity)
        G(EventActor, event=e1, entity=self.actor)

    def test_start_time(self):
        filters = self.medium.get_filtered_events_queries(datetime(2014, 1, 16), None, None, True, None)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 3)

    def test_end_time(self):
        filters = self.medium.get_filtered_events_queries(None, datetime(2014, 1, 16), None, True, None)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 2)

    def test_is_seen(self):
        filters = self.medium.get_filtered_events_queries(None, None, True, True, None)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 1)

    def test_is_not_seen(self):
        filters = self.medium.get_filtered_events_queries(None, None, False, True, None)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 4)

    def test_include_expires(self):
        filters = self.medium.get_filtered_events_queries(None, None, None, True, None)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 5)

    def test_dont_include_expires(self):
        filters = self.medium.get_filtered_events_queries(None, None, None, False, None)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 4)

    def test_actor(self):
        filters = self.medium.get_filtered_events_queries(None, None, None, True, self.actor)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 1)


class MediumFollowedByTest(TestCase):
    def setUp(self):
        self.medium = N(Medium)
        self.superentity = G(Entity)
        self.sub1, self.sub2 = G(Entity), G(Entity)
        G(EntityRelationship, super_entity=self.superentity, sub_entity=self.sub1)
        G(EntityRelationship, super_entity=self.superentity, sub_entity=self.sub2)

    def test_self_in(self):
        followers = self.medium.followed_by(self.sub1)
        super_entity_in = followers.filter(id=self.sub1.id).exists()
        self.assertTrue(super_entity_in)

    def test_super_entities_in(self):
        followers = self.medium.followed_by(self.sub1)
        sub_entity_in = followers.filter(id=self.superentity.id).exists()
        self.assertTrue(sub_entity_in)

    def test_others_not_in(self):
        followers = self.medium.followed_by(self.sub1)
        random_entity_in = followers.filter(id=self.sub2.id).exists()
        self.assertFalse(random_entity_in)

    def test_multiple_inputs_list(self):
        followers = self.medium.followed_by([self.sub1.id, self.sub2.id])
        self.assertEqual(followers.count(), 3)

    def test_multiple_inputs_qs(self):
        entities = Entity.objects.filter(id__in=[self.sub1.id, self.sub2.id])
        followers = self.medium.followed_by(entities)
        self.assertEqual(followers.count(), 3)


class MediumFollowersOfTest(TestCase):
    def setUp(self):
        self.medium = N(Medium)
        self.superentity = G(Entity)
        self.sub1, self.sub2 = G(Entity), G(Entity)
        self.random_entity = G(Entity)
        G(EntityRelationship, super_entity=self.superentity, sub_entity=self.sub1)
        G(EntityRelationship, super_entity=self.superentity, sub_entity=self.sub2)

    def test_self_in(self):
        followers = self.medium.followers_of(self.superentity)
        super_entity_in = followers.filter(id=self.superentity.id).exists()
        self.assertTrue(super_entity_in)

    def test_sub_entities_in(self):
        followers = self.medium.followers_of(self.superentity)
        sub_entity_in = followers.filter(id=self.sub1.id).exists()
        self.assertTrue(sub_entity_in)

    def test_others_not_in(self):
        followers = self.medium.followers_of(self.superentity)
        random_entity_in = followers.filter(id=self.random_entity.id).exists()
        self.assertFalse(random_entity_in)

    def test_multiple_inputs_list(self):
        followers = self.medium.followers_of([self.sub1.id, self.sub2.id])
        self.assertEqual(followers.count(), 2)

    def test_multiple_inputs_qs(self):
        entities = Entity.objects.filter(id__in=[self.sub1.id, self.sub2.id])
        followers = self.medium.followers_of(entities)
        self.assertEqual(followers.count(), 2)


class SubscriptionSubscribedEntitiesTest(TestCase):
    def setUp(self):
        person_kind = G(EntityKind, name='person', display_name='person')
        superentity = G(Entity)
        sub1, sub2 = G(Entity, entity_kind=person_kind), G(Entity, entity_kind=person_kind)
        G(EntityRelationship, super_entity=superentity, sub_entity=sub1)
        G(EntityRelationship, super_entity=superentity, sub_entity=sub2)

        self.group_sub = N(Subscription, entity=superentity, sub_entity_kind=person_kind)
        self.indiv_sub = N(Subscription, entity=superentity, sub_entity_kind=None)

    def test_both_branches_return_queryset(self):
        group_qs = self.group_sub.subscribed_entities()
        indiv_qs = self.indiv_sub.subscribed_entities()
        self.assertEqual(type(group_qs), type(indiv_qs))

    def test_length_group(self):
        group_qs = self.group_sub.subscribed_entities()
        self.assertEqual(group_qs.count(), 2)

    def test_length_indiv(self):
        indiv_qs = self.indiv_sub.subscribed_entities()
        self.assertEqual(indiv_qs.count(), 1)


class ContextRendererRenderTextOrHtmlTemplateTest(SimpleTestCase):
    @patch('entity_event.models.render_to_string', spec_set=True)
    def test_w_html_template_path(self, mock_render_to_string):
        cr = N(ContextRenderer, html_template_path='html_path')
        c = {'context': 'context'}
        cr.render_text_or_html_template(c, is_text=False)
        mock_render_to_string.assert_called_once_with('html_path', c)

    @patch('entity_event.models.render_to_string', spec_set=True)
    def test_w_text_template_path(self, mock_render_to_string):
        cr = N(ContextRenderer, text_template_path='text_path')
        c = {'context': 'context'}
        cr.render_text_or_html_template(c, is_text=True)
        mock_render_to_string.assert_called_once_with('text_path', c)

    @patch.object(Template, '__init__', spec_set=True, return_value=None)
    @patch.object(Template, 'render', spec_set=True)
    def test_w_html_template(self, mock_render, mock_init):
        cr = N(ContextRenderer, html_template='html_template')
        c = {'context': 'context'}
        cr.render_text_or_html_template(c, is_text=False)
        self.assertEqual(mock_render.call_count, 1)
        mock_init.assert_called_once_with('html_template')

    @patch.object(Template, '__init__', spec_set=True, return_value=None)
    @patch.object(Template, 'render', spec_set=True)
    def test_w_text_template(self, mock_render, mock_init):
        cr = N(ContextRenderer, text_template='text_template')
        c = {'context': 'context'}
        cr.render_text_or_html_template(c, is_text=True)
        self.assertEqual(mock_render.call_count, 1)
        mock_init.assert_called_once_with('text_template')

    def test_w_no_templates_text(self):
        cr = N(ContextRenderer)
        c = {'context': 'context'}
        self.assertEqual(cr.render_text_or_html_template(c, is_text=True), '')

    def test_w_no_templates_html(self):
        cr = N(ContextRenderer)
        c = {'context': 'context'}
        self.assertEqual(cr.render_text_or_html_template(c, is_text=False), '')


class ContextRendererRenderContextToTextHtmlTemplates(SimpleTestCase):
    @patch.object(ContextRenderer, 'render_text_or_html_template', spec_set=True)
    def test_render_context_to_text_html_templates(self, mock_render_text_or_html_template):
        c = {'context': 'context'}
        r = ContextRenderer().render_context_to_text_html_templates(c)
        self.assertEqual(
            r, (
                mock_render_text_or_html_template.return_value.strip(),
                mock_render_text_or_html_template.return_value.strip()
            ))
        self.assertEqual(
            mock_render_text_or_html_template.call_args_list, [call(c, is_text=True), call(c, is_text=False)])


class ContextRendererGetSerializedContextTests(SimpleTestCase):
    @patch('entity_event.models.DefaultContextSerializer')
    def test_get_serialized_context(self, mock_default_context_serializer):
        context = {'context': 'context'}
        response = ContextRenderer().get_serialized_context(context)

        # Assert we have a proper response
        self.assertEqual(response, mock_default_context_serializer.return_value.data)

        # Assert that we created the default serializer correctly
        mock_default_context_serializer.assert_called_once_with(context)


class UnseenEventIdsTest(TestCase):
    def test_filters_seen(self):
        m = G(Medium)
        e1 = G(Event, context={})
        e2 = G(Event, context={})
        Event.objects.filter(id=e2.id).mark_seen(m)
        unseen_ids = _unseen_event_ids(m)
        self.assertEqual(unseen_ids, [e1.id])

    def test_multiple_mediums(self):
        m1 = G(Medium)
        m2 = G(Medium)
        e1 = G(Event, context={})
        e2 = G(Event, context={})
        e3 = G(Event, context={})
        e4 = G(Event, context={})
        Event.objects.filter(id=e2.id).mark_seen(m1)
        Event.objects.filter(id=e3.id).mark_seen(m2)
        unseen_ids = _unseen_event_ids(m1)
        self.assertEqual(set(unseen_ids), set([e1.id, e3.id, e4.id]))


class UnicodeTest(SimpleTestCase):
    def setUp(self):
        self.rendering_style = N(RenderingStyle, display_name='Test Render Group')
        self.context_renderer = N(ContextRenderer, name='Test Context Renderer')
        self.medium = G(Medium, display_name='Test Medium')
        self.source = G(Source, display_name='Test Source')
        self.source_group = G(SourceGroup, display_name='Test Source Group')
        self.entity = G(Entity, display_name='Test Entity')
        self.unsubscription = N(
            Unsubscription, entity=self.entity, medium=self.medium, source=self.source)
        self.subscription = N(
            Subscription, entity=self.entity, source=self.source, medium=self.medium)
        self.event = N(Event, source=self.source, context={}, id=1)
        self.event_actor = N(EventActor, event=self.event, entity=self.entity)
        self.event_seen = N(
            EventSeen, event=self.event, medium=self.medium, time_seen=datetime(2014, 1, 2))

    def test_RenderingStyle_formats(self):
        s = text_type(self.rendering_style)
        self.assertEquals(s, 'Test Render Group')

    def test_contextrenderer_formats(self):
        s = text_type(self.context_renderer)
        self.assertEquals(s, 'Test Context Renderer')

    def test_medium_formats(self):
        s = text_type(self.medium)
        self.assertEqual(s, 'Test Medium')

    def test_source_formats(self):
        s = text_type(self.source)
        self.assertEqual(s, 'Test Source')

    def test_sourcegroup_formats(self):
        s = text_type(self.source_group)
        self.assertEqual(s, 'Test Source Group')

    def test_unsubscription_formats(self):
        s = text_type(self.unsubscription)
        self.assertEqual(s, '{0} from Test Source by Test Medium'.format(self.entity))

    def test_subscription_formats(self):
        s = text_type(self.subscription)
        self.assertEqual(s, '{0} to Test Source by Test Medium'.format(self.entity))

    def test_event_formats(self):
        s = text_type(self.event)
        self.assertTrue(s.startswith('Test Source event at 201'))

    def test_eventactor_formats(self):
        s = text_type(self.event_actor)
        self.assertEqual(s, 'Event 1 - {0}'.format(self.entity))

    def test_event_seenformats(self):
        s = text_type(self.event_seen)
        self.assertEqual(s, 'Seen on Test Medium at 2014-01-02::00:00:00')


class SubscriptionQuerySetTest(SimpleTestCase):
    """
    Test the subscription query set class
    """

    def setUp(self):
        # Call super
        super(SubscriptionQuerySetTest, self).setUp()

        # Create a query set to use
        self.queryset = SubscriptionQuerySet()

    @patch.object(SubscriptionQuerySet, 'select_related', autospec=True)
    def test_cache_related(self, mock_select_related):
        # Call the method
        self.queryset.cache_related()

        # Assert that we called select related with the correct args
        mock_select_related.assert_called_once_with(
            self.queryset,
            'medium',
            'source',
            'entity',
            'sub_entity_kind'
        )
