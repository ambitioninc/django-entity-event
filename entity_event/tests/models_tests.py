from datetime import datetime

from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.test import TestCase, SimpleTestCase
from django_dynamic_fixture import N, G
from entity.models import Entity, EntityKind, EntityRelationship
from freezegun import freeze_time
from six import text_type

from entity_event.models import (
    Medium, Source, SourceGroup, Unsubscription, Subscription, Event, EventActor, EventSeen
)


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


def basic_context_loader(context):
    return {'hello': 'hello'}


class SourceGetContextLoaderTest(SimpleTestCase):
    def test_loads_context_loader(self):
        template = Source(context_loader='entity_event.tests.models_tests.basic_context_loader')
        loader_func = template.get_context_loader_function()
        self.assertEqual(loader_func, basic_context_loader)

    def test_invalid_context_loader(self):
        template = Source(context_loader='entity_event.tests.models_tests.invalid_context_loader')
        with self.assertRaises(ImproperlyConfigured):
            template.get_context_loader_function()


class SourceCleanTest(SimpleTestCase):
    def test_invalid_context_path_does_not_validate(self):
        with self.assertRaises(ValidationError):
            Source(context_loader='invalid_path').clean()


class EventGetContext(SimpleTestCase):
    def test_without_context_loader(self):
        event = N(
            Event, context={'hi': 'hi'}, persist_dependencies=False, source=N(
                Source, context_loader='entity_event.tests.models_tests.basic_context_loader',
                persist_dependencies=False))
        self.assertEqual(event.get_context(), {'hello': 'hello'})

    def test_with_context_loader(self):
        event = N(Event, context={'hi': 'hi'}, persist_dependencies=False)
        self.assertEqual(event.get_context(), {'hi': 'hi'})


class EventManagerTest(TestCase):
    def test_mark_seen(self):
        event = G(Event, context={})
        medium = G(Medium)
        Event.objects.mark_seen(medium)
        self.assertEqual(EventSeen.objects.count(), 1)
        self.assertTrue(EventSeen.objects.filter(event=event, medium=medium).exists())


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

    def test_start_time(self):
        filters = self.medium.get_event_filters(datetime(2014, 1, 16), None, None, True)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 3)

    def test_end_time(self):
        filters = self.medium.get_event_filters(None, datetime(2014, 1, 16), None, True)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 2)

    def test_is_seen(self):
        filters = self.medium.get_event_filters(None, None, True, True)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 1)

    def test_is_not_seen(self):
        filters = self.medium.get_event_filters(None, None, False, True)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 4)

    def test_include_expires(self):
        filters = self.medium.get_event_filters(None, None, None, True)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 5)

    def test_dont_include_expires(self):
        filters = self.medium.get_event_filters(None, None, None, False)
        events = Event.objects.filter(*filters)
        self.assertEqual(events.count(), 4)


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


# Note: The following freeze_time a few more minutes than what we
# want, in order to work around a strange off by a few seconds bug in
# freezegun. I'm not sure what other way to fix it. Since we're only
# testing unicode representations here, it isn't terribly important.
@freeze_time(datetime(2014, 1, 1, 0, 10))
class UnicodeTest(TestCase):
    def setUp(self):
        self.medium = N(Medium, display_name='Test Medium')
        self.source = N(Source, display_name='Test Source')
        self.source_group = N(SourceGroup, display_name='Test Source Group')
        self.entity = N(Entity, display_name='Test Entity')
        self.entity_string = text_type(self.entity)
        self.unsubscription = N(Unsubscription, entity=self.entity, medium=self.medium, source=self.source)
        self.subscription = N(Subscription, entity=self.entity, source=self.source, medium=self.medium)
        self.event = N(Event, source=self.source, context={}, id=1)
        self.event_actor = N(EventActor, event=self.event, entity=self.entity)
        self.event_seen = N(EventSeen, event=self.event, medium=self.medium, time_seen=datetime(2014, 1, 2))

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
        self.assertEqual(s, '{0} from Test Source by Test Medium'.format(self.entity_string))

    def test_subscription_formats(self):
        s = text_type(self.subscription)
        self.assertEqual(s, '{0} to Test Source by Test Medium'.format(self.entity_string))

    def test_event_formats(self):
        s = text_type(self.event)
        self.assertTrue(s.startswith('Test Source event at 201'))

    def test_eventactor_formats(self):
        s = text_type(self.event_actor)
        self.assertEqual(s, 'Event 1 - {0}'.format(self.entity_string))

    def test_event_seenformats(self):
        s = text_type(self.event_seen)
        self.assertEqual(s, 'Seen on Test Medium at 2014-01-02::00:00:00')
