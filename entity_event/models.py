from collections import defaultdict
from datetime import datetime
from operator import or_

from cached_property import cached_property
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db import models, transaction
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils.encoding import python_2_unicode_compatible
from django.utils.module_loading import import_by_path
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
        """Readable representation of ``Medium`` objects."""
        return self.display_name

    @transaction.atomic
    def events(self, start_time=None, end_time=None, seen=None, include_expired=False, mark_seen=False):
        """Return subscribed events, with basic filters.

        This method of getting events is useful when you want to
        display events for your medium, independent of what entities
        were involved in those events. For example, this method can be
        used to display a list of site-wide events that happend in the
        past 24 hours:

        .. code-block:: python

            TEMPLATE = '''
                <html><body>
                <h1> Yoursite's Events </h1>
                <ul>
                {% for event in events %}
                    <li> {{ event.context.event_text }} </li>
                {% endfor %}
                </ul>
                </body></html>
            '''

            def site_feed(request):
                site_feed_medium = Medium.objects.get(name='site_feed')
                start_time = datetime.utcnow() - timedelta(days=1)
                context = {}
                context['events'] = site_feed_medium.events(start_time=start_time)
                return HttpResponse(TEMPLATE.render(context))

        While the `events` method does not filter events based on what
        entities are involved, filtering based on the properties of the events
        themselves is supported, through the following arguments, all
        of which are optional.

        :type start_time: datetime.datetime (optional)
        :param start_time: Only return events that occured after the
            given time. If no time is given for this argument, no
            filtering is done.

        :type end_time: datetime.datetime (optional)
        :param end_time: Only return events that occured before the
            given time. If no time is given for this argument, no
            filtering is done

        :type seen: Boolean (optional)
        :param seen: This flag controls whether events that have
            marked as seen are included. By default, both events that
            have and have not been marked as seen are included. If
            ``True`` is given for this parameter, only events that
            have been marked as seen will be included. If ``False`` is
            given, only events that have not been marked as seen will
            be included.

        :type include_expired: Boolean (optional)
        :param include_expired: By default, events that have a
            expiration time, which has passed, are not included in the
            results. Passing in ``True`` to this argument causes
            expired events to be returned as well.

        :type mark_seen: Boolean (optional)
        :param mark_seen: Create a side effect in the database that
            marks all the returned events as having been seen by this
            medium.

        """
        events = self.get_filtered_events(start_time, end_time, seen, include_expired, mark_seen)
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

    @transaction.atomic
    def entity_events(self, entity, start_time=None, end_time=None, seen=None, include_expired=False, mark_seen=False):
        """Return subscribed events for a given entity.

        This method of getting events is useful when you want to see
        only the events relevant to a single entity. The events
        returned are events that the given entity is subscribed to,
        either directly as an individual entity, or because they are
        part of a group subscription. As an example, the
        `entity_events` method can be used to implement a newsfeed for
        a individual entity:

        .. code-block:: python

            TEMPLATE = '''
                <html><body>
                <h1> {entity}'s Events </h1>
                <ul>
                {% for event in events %}
                    <li> {{ event.context.event_text }} </li>
                {% endfor %}
                </ul>
                </body></html>
            '''

            def newsfeed(request):
                newsfeed_medium = Medium.objects.get(name='newsfeed')
                entity = Entity.get_for_obj(request.user)
                context = {}
                context['entity'] = entity
                context['events'] = site_feed_medium.entity_events(entity, seen=False, mark_seen=True)
                return HttpResponse(TEMPLATE.render(context))


        The only required argument for this method is the entity to
        get events for. Filtering based on the properties of the
        events themselves is supported, through the rest of the
        following arguments, which are optional.

        :type_entity: Entity
        :param entity: The entity to get events for.

        :type start_time: datetime.datetime (optional)
        :param start_time: Only return events that occured after the
            given time. If no time is given for this argument, no
            filtering is done.

        :type end_time: datetime.datetime (optional)
        :param end_time: Only return events that occured before the
            given time. If no time is given for this argument, no
            filtering is done

        :type seen: Boolean (optional)
        :param seen: This flag controls whether events that have
            marked as seen are included. By default, both events that
            have and have not been marked as seen are included. If
            ``True`` is given for this parameter, only events that
            have been marked as seen will be included. If ``False`` is
            given, only events that have not been marked as seen will
            be included.

        :type include_expired: Boolean (optional)
        :param include_expired: By default, events that have a
            expiration time, which has passed, are not included in the
            results. Passing in ``True`` to this argument causes
            expired events to be returned as well.

        :type mark_seen: Boolean (optional)
        :param mark_seen: Create a side effect in the database that
            marks all the returned events as having been seen by this
            medium.

        """
        events = self.get_filtered_events(start_time, end_time, seen, include_expired, mark_seen)

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

        return [
            event for event in events.filter(reduce(or_, subscription_q_objects))
            if self.filter_source_targets_by_unsubscription(event.source_id, [entity])
        ]

    @transaction.atomic
    def events_targets(
            self, entity_kind=None, start_time=None, end_time=None,
            seen=None, include_expired=False, mark_seen=False):
        """Return all events for this medium, with who each event is for.

        This method is useful for individually notifying every
        entity concerned with a collection of events, while
        still respecting subscriptions and usubscriptions. For
        example, ``events_targets`` can be used to send email
        notifications, by retrieving all unseen events (and marking
        them as now having been seen), and then processing the
        emails. In code, this could look like:

        .. code-block:: python

            email = Medium.objects.get(name='email')
            new_emails = email.events_targets(seen=False, mark_seen=True)

            for event, targets in new_emails:
                django.core.mail.send_mail(
                    subject = event.context["subject"]
                    message = event.context["message"]
                    recipient_list = [t.entity_meta["email"] for t in targets]
                )

        This ``events_targets`` method attempts to make bulk
        processing of push-style notifications straightforward. This
        sort of processing should normally occur in a separate thread
        from any request/response cycle.

        Filtering based on the properties of the events themselves is
        supported, through the rest of the following arguments, which
        are optional.

        :type entity_kind: EntityKind
        :param entity_kind: Only include targets of the given kind in
            each targets list.

        :type start_time: datetime.datetime (optional)
        :param start_time: Only return events that occured after the
            given time. If no time is given for this argument, no
            filtering is done.

        :type end_time: datetime.datetime (optional)
        :param end_time: Only return events that occured before the
            given time. If no time is given for this argument, no
            filtering is done

        :type seen: Boolean (optional)
        :param seen: This flag controls whether events that have
            marked as seen are included. By default, both events that
            have and have not been marked as seen are included. If
            ``True`` is given for this parameter, only events that
            have been marked as seen will be included. If ``False`` is
            given, only events that have not been marked as seen will
            be included.

        :type include_expired: Boolean (optional)
        :param include_expired: By default, events that have a
            expiration time, which has passed, are not included in the
            results. Passing in ``True`` to this argument causes
            expired events to be returned as well.

        :type mark_seen: Boolean (optional)
        :param mark_seen: Create a side effect in the database that
            marks all the returned events as having been seen by this
            medium.

        """
        events = self.get_filtered_events(start_time, end_time, seen, include_expired, mark_seen)
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

            targets = self.filter_source_targets_by_unsubscription(event.source_id, targets)

            if entity_kind:
                targets = [t for t in targets if t.entity_kind == entity_kind]
            if targets:
                event_pairs.append((event, targets))

        return event_pairs

    def subset_subscriptions(self, subscriptions, entity=None):
        """Return only subscriptions the given entity is a part of.

        An entity is "part of a subscription" if either:

        1. The subscription is for that entity, with no
        sub-entity-kind. That is, it is not a group subscription.

        2. The subscription is for a super-entity of the given entity,
        and the subscriptions's sub-entity-kind is the same as that of
        the entity's.
        """
        if entity is None:
            return subscriptions
        super_entities = EntityRelationship.objects.filter(
            sub_entity=entity).values_list('super_entity')
        subscriptions = subscriptions.filter(
            Q(entity=entity, sub_entity_kind=None) |
            Q(entity__in=super_entities, sub_entity_kind=entity.entity_kind)
        )

        return subscriptions

    @cached_property
    def unsubscriptions(self):
        """Returns the unsubscribed entity IDs for each source as a dict,
        keyed on source_id.
        """
        unsubscriptions = defaultdict(list)
        for unsub in Unsubscription.objects.filter(medium=self).values('entity', 'source'):
            unsubscriptions[unsub['source']].append(unsub['entity'])
        return unsubscriptions

    def filter_source_targets_by_unsubscription(self, source_id, targets):
        """Given a source id and targets, filter the targets by
        unsubscriptions. Return the filtered list of targets.
        """
        unsubscriptions = self.unsubscriptions
        return [t for t in targets if t.id not in unsubscriptions[source_id]]

    def get_event_filters(self, start_time, end_time, seen, include_expired):
        """Return Q objects to filter events table to relevant events.
        """
        now = datetime.utcnow()
        filters = []
        if start_time is not None:
            filters.append(Q(time__gte=start_time))
        if end_time is not None:
            filters.append(Q(time__lte=end_time))
        if not include_expired:
            filters.append(Q(Q(time_expires__gte=now) | Q(time_expires__isnull=True)))

        # Check explicitly for True and False as opposed to None
        #   - `seen==False` gets unseen notifications
        #   - `seen is None` does no seen/unseen filtering
        if seen is True:
            filters.append(Q(eventseen__medium=self))
        elif seen is False:
            filters.append(~Q(eventseen__medium=self))
        return filters

    def get_filtered_events(self, start_time, end_time, seen, include_expired, mark_seen):
        """Retrieves events, filters by event level filters, and marks them as
        seen if necessary.
        """
        event_filters = self.get_event_filters(start_time, end_time, seen, include_expired)
        events = Event.objects.filter(*event_filters)
        if seen is False and mark_seen:
            # Evaluate the event qset here and create a new queryset that is no longer filtered by
            # if the events are marked as seen. We do this because we want to mark the events
            # as seen in the next line of code. If we didn't evaluate the qset here first, it result
            # in not returning unseen events since they are marked as seen.
            events = Event.objects.filter(id__in=list(e.id for e in events))
            events.mark_seen(self)

        return events

    def followed_by(self, entities):
        """Define what entities are followed by the entities passed to this
        method.

        This method can be overridden by a class that concretely
        inherits ``Medium``, to define custom sematics for the
        ``only_following`` flag on relevant ``Subscription``
        objects. Overriding this method, and ``followers_of`` will be
        sufficient to define that behavior. This method is not useful
        to call directly, but is used by the methods that filter
        events and targets.

        This implementation attempts to provide a sane default. In
        this implementation, the entities followed by the ``entities``
        argument are the entities themselves, and their super entities.

        That is, individual entities follow themselves, and the groups
        they are a part of. This works as a default implementation,
        but, for example, an alternate medium may wish to define the
        opposite behavior, where an individual entity follows
        themselves and all of their sub-entities.

        Return a queyset of the entities that the given entities are
        following. This needs to be the inverse of ``followers_of``.
        """
        if isinstance(entities, Entity):
            entities = Entity.objects.filter(id=entities.id)
        super_entities = EntityRelationship.objects.filter(
            sub_entity__in=entities).values_list('super_entity')
        followed_by = Entity.objects.filter(
            Q(id__in=entities) | Q(id__in=super_entities))
        return followed_by

    def followers_of(self, entities):
        """Define what entities are followers of the entities passed to this
        method.

        This method can be overridden by a class that concretely
        inherits ``Medium``, to define custom sematics for the
        ``only_following`` flag on relevant ``Subscription``
        objects. Overriding this method, and ``followed_by`` will be
        sufficient to define that behavior. This method is not useful
        to call directly, but is used by the methods that filter
        events and targets.

        This implementation attempts to provide a sane default. In
        this implementation, the followers of the entities passed in
        are defined to be the entities themselves, and their
        subentities.

        That is, the followers of individual entities are themselves,
        and if the entity has sub-entities, those sub-entities. This
        works as a default implementation, but, for example, an
        alternate medium may wish to define the opposite behavior,
        where an the followers of an individual entity are themselves
        and all of their super-entities.

        Return a querset of the entities that follow the given
        entities. This needs to be the inverse of ``followed_by``.
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
    # An optional function path that loads the context of an event and performs
    # any additional application-specific context fetching before rendering
    context_loader = models.CharField(max_length=256, default='', blank=True)

    def get_context_loader_function(self):
        """Returns an imported, callable context loader function.
        """
        return import_by_path(self.context_loader)

    def get_context(self, context):
        """Gets the context for this source by loading it through the source's
        context loader (if it has one).
        """
        if self.context_loader:
            return self.get_context_loader_function()(context)
        else:
            return context

    def clean(self):
        """Validatition for the model.

        Check that:
        - the context loader provided maps to an actual loadable function.
        """
        if self.context_loader:
            try:
                self.get_context_loader_function()
            except ImproperlyConfigured:
                raise ValidationError('Must provide a loadable context loader')

    def save(self, *args, **kwargs):
        """Save the instance to the database after validation.
        """
        self.clean()
        return super(Source, self).save(*args, **kwargs)

    def __str__(self):
        """Readable representation of ``Source`` objects."""
        return self.display_name


@python_2_unicode_compatible
class SourceGroup(models.Model):
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()

    def __str__(self):
        """Readable representation of ``SourceGroup`` objects."""
        return self.display_name


@python_2_unicode_compatible
class Unsubscription(models.Model):
    entity = models.ForeignKey(Entity)
    medium = models.ForeignKey('Medium')
    source = models.ForeignKey('Source')

    def __str__(self):
        """Readable representation of ``Unsubscription`` objects."""
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
    sub_entity_kind = models.ForeignKey(EntityKind, null=True, related_name='+', default=None)
    only_following = models.BooleanField(default=True)

    def __str__(self):
        """Readable representation of ``Subscription`` objects."""
        s = '{entity} to {source} by {medium}'
        entity = self.entity.__str__()
        source = self.source.__str__()
        medium = self.medium.__str__()
        return s.format(entity=entity, source=source, medium=medium)

    def subscribed_entities(self):
        """Return a queryset of all subscribed entities.

        This will be a single entity in the case of an individual
        subscription, otherwise it will be all the entities in the
        group subscription.
        """
        if self.sub_entity_kind is not None:
            sub_entities = self.entity.sub_relationships.filter(
                sub_entity__entity_kind=self.sub_entity_kind).values_list('sub_entity')
            entities = Entity.objects.filter(id__in=sub_entities)
        else:
            entities = Entity.objects.filter(id=self.entity.id)
        return entities


class EventQuerySet(QuerySet):
    def mark_seen(self, medium):
        """Creates EventSeen objects for the provided medium for every event
        in the queryset.

        Creating these EventSeen objects ensures they will not be
        returned when passing ``seen=False`` to any of the medium
        event retrieval functions, ``events``, ``entity_events``, or
        ``events_targets``.
        """
        EventSeen.objects.bulk_create([
            EventSeen(event=event, medium=medium) for event in self
        ])


class EventManager(models.Manager):
    def get_queryset(self):
        """Return the EventQuerySet.
        """
        return EventQuerySet(self.model)

    def mark_seen(self, medium):
        """Creates EventSeen objects for the provided medium for every event
        in the queryset.

        Creating these EventSeen objects ensures they will not be
        returned when passing ``seen=False`` to any of the medium
        event retrieval functions, ``events``, ``entity_events``, or
        ``events_targets``.
        """
        return self.get_queryset().mark_seen(medium)

    @transaction.atomic
    def create_event(self, ignore_duplicates=False, actors=None, **kwargs):
        """Create events with actors.
        """
        if ignore_duplicates and self.filter(uuid=kwargs.get('uuid', '')).exists():
            return None

        event = self.create(**kwargs)

        # Allow user to pass pks for actors
        actors = [
            a.id if isinstance(a, Entity) else a
            for a in actors
        ] if actors else []

        EventActor.objects.bulk_create([EventActor(entity_id=actor, event=event) for actor in actors])
        return event


@python_2_unicode_compatible
class Event(models.Model):
    source = models.ForeignKey('Source')
    context = jsonfield.JSONField()
    time = models.DateTimeField(auto_now_add=True)
    time_expires = models.DateTimeField(null=True, default=None)
    uuid = models.CharField(max_length=128, unique=True)

    objects = EventManager()

    def get_context(self):
        """Retrieves and populates the context for this event.

        At the minimum, whatever context was stored in the event is
        returned. If the source of the event provides a
        ``context_loader``, any additional context created by that
        function will be included.
        """
        return self.source.get_context(self.context)

    def __str__(self):
        """Readable representation of ``Event`` objects."""
        s = '{source} event at {time}'
        source = self.source.__str__()
        time = self.time.strftime('%Y-%m-%d::%H:%M:%S')
        return s.format(source=source, time=time)


class AdminEvent(Event):
    class Meta:
        proxy = True


@python_2_unicode_compatible
class EventActor(models.Model):
    event = models.ForeignKey('Event')
    entity = models.ForeignKey(Entity)

    def __str__(self):
        """Readable representation of ``EventActor`` objects."""
        s = 'Event {eventid} - {entity}'
        eventid = self.event.id
        entity = self.entity.__str__()
        return s.format(eventid=eventid, entity=entity)


@python_2_unicode_compatible
class EventSeen(models.Model):
    event = models.ForeignKey('Event')
    medium = models.ForeignKey('Medium')
    time_seen = models.DateTimeField(default=datetime.utcnow)

    class Meta:
        unique_together = ('event', 'medium')

    def __str__(self):
        """Readable representation of ``EventSeen`` objects."""
        s = 'Seen on {medium} at {time}'
        medium = self.medium.__str__()
        time = self.time_seen.strftime('%Y-%m-%d::%H:%M:%S')
        return s.format(medium=medium, time=time)
