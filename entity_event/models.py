from datetime import datetime
from operator import or_

from django.db import models
from django.db.models import Q
from django.utils.encoding import python_2_unicode_compatible
import jsonfield
from six.moves import reduce

from entity.models import Entity, EntityKind, EntityRelationship


# TODO: add mark_seen function
@python_2_unicode_compatible
class Medium(models.Model):
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()

    def __str__(self):
        return self.display_name

    def events(self, start_time=None, end_time=None, seen=None):
        """Return subscribed events, with basic filters.
        """
        event_filters = self.get_event_filters(start_time, end_time, seen)
        events = Event.objects.filter(*event_filters)
        subscriptions = Subscription.objects.filter(medium=self)

        subscription_q_objects = []
        for sub in subscriptions:
            if sub.only_following:
                entities = sub.subscribed_entities()
                followed_by = self.followed_by(entities)
                subscription_q_objects.append(
                    Q(eventactor__entity__in=followed_by, source=sub.source)
                )
            else:
                subscription_q_objects.append(
                    Q(source=sub.source)
                )
        events = events.filter(reduce(or_, subscription_q_objects))
        return events

    def entity_events(self, entity, start_time=None, end_time=None, seen=None):
        """Return subscribed events for a given entity.
        """
        event_filters = self.get_event_filters(start_time, end_time, seen)
        events = Event.objects.filter(*event_filters)

        subscriptions = Subscription.objects.filter(medium=self)
        subscriptions = self.subset_subscriptions(subscriptions, entity)

        subscription_q_objects = []
        for sub in subscriptions:
            if sub.only_following:
                followed_by = self.followed_by(entity)
                subscription_q_objects.append(
                    Q(eventactor__entity__in=followed_by, source=sub.source)
                )
            else:
                subscription_q_objects.append(
                    Q(source=sub.source)
                )
        events = events.filter(reduce(or_, subscription_q_objects))
        return events

    def events_targets(self, entity_kind=None, start_time=None, end_time=None, seen=None):
        """Return all events for this medium, with who is the event is for.
        """
        event_filters = self.get_event_filters(start_time, end_time, seen)
        events = Event.objects.filter(*event_filters)
        subscriptions = Subscription.objects.filter(medium=self)

        event_pairs = []
        for event in events:
            targets = []
            for sub in subscriptions:
                if event.source != sub.source:
                    continue
                subscribed = sub.subscribed_entities()
                if sub.only_following:
                    potential_targets = self.followers_of(
                        event.eventactor_set.values_list('entity__id', flat=True)
                    )
                    subscription_targets = list(Entity.objects.filter(
                        Q(id__in=subscribed), Q(id__in=potential_targets)))
                else:
                    subscription_targets = list(subscribed)
                targets.extend(subscription_targets)
            unsubed = Unsubscription.objects.filter(
                source=event.source, medium=self).values_list('entity', flat=True)
            targets = [t for t in targets if t not in unsubed]
            if entity_kind:
                targets = [t for t in targets if t.entity_kind == entity_kind]
            if targets:
                event_pairs.append((event, targets))
        return event_pairs

    def subset_subscriptions(self, subscriptions, entity=None):
        """Return only subscriptions the given entity is a part of.
        """
        if entity is None:
            return subscriptions
        super_entities = EntityRelationship.objects.filter(
            sub_entity=entity).values_list('super_entity')
        subscriptions = subscriptions.filter(
            Q(entity=entity, sub_entity_kind=None) |
            Q(entity__in=super_entities, sub_entity_kind=entity.entity_kind)
        )
        # Todo: add unsubscription checking
        return subscriptions

    def get_event_filters(self, start_time, end_time, seen):
        """Return Q objects to filter events table.
        """
        filters = []
        if start_time is not None:
            filters.append(Q(time__gte=start_time))
        if end_time is not None:
            filters.append(Q(time__lte=end_time))

        # Check explicitly for True and False as opposed to None
        #   - `seen==False` gets unseen notifications
        #   - `seen is None` does no seen/unseen filtering
        if seen is True:
            filters.append(Q(eventseen__medium=self))
        elif seen is False:
            filters.append(~Q(eventseen__medium=self))
        return filters

    def followed_by(self, entities):
        """Return a queyset of the entities that the given entities are following.

        Entities follow themselves, and their super entities.
        """
        if isinstance(entities, Entity):
            entities = Entity.objects.filter(id=entities.id)
        super_entities = EntityRelationship.objects.filter(
            sub_entity__in=entities).values_list('super_entity')
        followed_by = Entity.objects.filter(
            Q(id__in=entities) | Q(id__in=super_entities))
        return followed_by

    def followers_of(self, entities):
        """Return a querset of the entities that follow the given entities.

        The followers of an entity are themselves and their sub entities.
        """
        if isinstance(entities, Entity):
            entities = Entity.objects.filter(id=entities.id)
        sub_entities = EntityRelationship.objects.filter(
            super_entity__in=entities).values_list('sub_entity')
        followers_of = Entity.objects.filter(
            Q(id__in=entities) | Q(id__in=sub_entities))
        return followers_of


@python_2_unicode_compatible
class Source(models.Model):
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()
    group = models.ForeignKey('SourceGroup')

    def __str__(self):
        return self.display_name


@python_2_unicode_compatible
class SourceGroup(models.Model):
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()

    def __str__(self):
        return self.display_name


@python_2_unicode_compatible
class Unsubscription(models.Model):
    entity = models.ForeignKey(Entity)
    medium = models.ForeignKey('Medium')
    source = models.ForeignKey('Source')

    def __str__(self):
        s = '{entity} from {source} by {medium}'
        entity = self.entity.__str__()
        source = self.source.__str__()
        medium = self.medium.__str__()
        return s.format(entity=entity, source=source, medium=medium)


@python_2_unicode_compatible
class Subscription(models.Model):
    medium = models.ForeignKey('Medium')
    source = models.ForeignKey('Source')
    entity = models.ForeignKey(Entity, related_name='+')
    sub_entity_kind = models.ForeignKey(EntityKind, null=True, related_name='+')
    only_following = models.BooleanField(default=True)

    def __str__(self):
        s = '{entity} to {source} by {medium}'
        entity = self.entity.__str__()
        source = self.source.__str__()
        medium = self.medium.__str__()
        return s.format(entity=entity, source=source, medium=medium)

    def subscribed_entities(self):
        """Return a queryset of all subscribed entities.
        """
        if self.sub_entity_kind is not None:
            sub_entities = self.entity.sub_relationships.filter(
                sub_entity__entity_kind=self.sub_entity_kind).values_list('sub_entity')
            entities = Entity.objects.filter(
                Q(id__in=sub_entities) | Q(id=self.entity.id))
        else:
            entities = Entity.objects.filter(id=self.entity.id)
        return entities


@python_2_unicode_compatible
class Event(models.Model):
    source = models.ForeignKey('Source')
    context = jsonfield.JSONField()
    time = models.DateTimeField(auto_now_add=True)
    time_expires = models.DateTimeField(null=True, default=None)
    uuid = models.CharField(max_length=128, unique=True)

    def __str__(self):
        s = '{source} event at {time}'
        source = self.source.__str__()
        time = self.time.strftime('%Y-%m-%d::%H:%M:%S')
        return s.format(source=source, time=time)


@python_2_unicode_compatible
class EventActor(models.Model):
    event = models.ForeignKey('Event')
    entity = models.ForeignKey(Entity)

    def __str__(self):
        s = 'Event {eventid} - {entity}'
        eventid = self.event.id
        entity = self.entity.__str__()
        return s.format(eventid=eventid, entity=entity)


@python_2_unicode_compatible
class EventSeen(models.Model):
    event = models.ForeignKey('Event')
    medium = models.ForeignKey('Medium')
    time_seen = models.DateTimeField(default=datetime.utcnow)

    def __str__(self):
        s = 'Seen on {medium} at {time}'
        medium = self.medium.__str__()
        time = self.time_seen.strftime('%Y-%m-%d::%H:%M:%S')
        return s.format(medium=medium, time=time)
