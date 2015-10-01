from collections import defaultdict
from datetime import datetime
from operator import or_
from six.moves import reduce

from cached_property import cached_property
from django.db import models, transaction
from django.db.models import Q
from django.db.models.query import QuerySet
from django.template.loader import render_to_string
from django.template import Context, Template
from django.utils.encoding import python_2_unicode_compatible
from entity.models import Entity, EntityKind, EntityRelationship
import jsonfield
from entity_event.context_serializer import DefaultContextSerializer


@python_2_unicode_compatible
class Medium(models.Model):
    """A ``Medium`` is an object in the database that defines the method
    by which users will view events. The actual objects in the
    database are fairly simple, only requiring a ``name``,
    ``display_name`` and ``description``. Mediums can be created with
    ``Medium.objects.create``, using the following parameters:

    :type name: str
    :param name: A short, unique name for the medium.

    :type display_name: str
    :param display_name: A short, human readable name for the medium.
        Does not need to be unique.

    :type description: str
    :param description: A human readable description of the
        medium.

    Encoding a ``Medium`` object in the database serves two
    purposes. First, it is referenced when subscriptions are
    created. Second the ``Medium`` objects provide an entry point to
    query for events and have all the subscription logic and filtering
    taken care of for you.

    Any time a new way to display events to a user is created, a
    corresponding ``Medium`` should be created. Some examples could
    include a medium for sending email notifications, a medium for
    individual newsfeeds, or a medium for a site wide notification
    center.

    Once a medium object is created, and corresponding subscriptions
    are created, there are three methods on the medium object that can
    be used to query for events. They are ``events``,
    ``entity_events`` and ``events_targets``. The differences between
    these methods are described in their corresponding documentation.

    A medium can use a ``RenderingStyle`` to use a configured style of rendering
    with the medium. Any associated ``ContextRenderer`` models defined with
    that rendering style will be used to render events in the ``render`` method
    of the medium. This is an optional part of Entity Event's built-in
    rendering system. If a rendering style is not set up for a particular source or
    source group, it will try to use the default rendering style specified
    in settings.

    A medium can also provided ``additional_context`` that will always be passed
    to the templates of its rendered events. This allows for medium-specific rendering
    styles to be used. For example, perhaps a medium wishes to display a short description
    of an event but does not wish to display the names of the event actors since those
    names are already displayed in other places on the page. In this case, the medium
    can always pass additional context to suppress rendering of names.
    """
    # A name and display name for the medium along with a description for any
    # application display
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()

    # The rendering style determines the primary way the medium will try to render events.
    # If a context loader has been defined for this rendering style along with the appropriate
    # source, the renderer will be used. If a context renderer has not been set up with this
    # rendering style, it will try to use the default style configured in settings.
    rendering_style = models.ForeignKey('RenderingStyle', null=True)

    # These values are passed in as additional context to whatever event is being rendered.
    additional_context = jsonfield.JSONField(null=True, default=None)

    def __str__(self):
        """Readable representation of ``Medium`` objects."""
        return self.display_name

    @transaction.atomic
    def events(self, **event_filters):
        """Return subscribed events, with basic filters.

        This method of getting events is useful when you want to
        display events for your medium, independent of what entities
        were involved in those events. For example, this method can be
        used to display a list of site-wide events that happened in the
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
        :param start_time: Only return events that occurred after the
            given time. If no time is given for this argument, no
            filtering is done.

        :type end_time: datetime.datetime (optional)
        :param end_time: Only return events that occurred before the
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

        :type actor: Entity (optional)
        :param actor: Only include events with the given entity as an
            actor.

        :type mark_seen: Boolean (optional)
        :param mark_seen: Create a side effect in the database that
            marks all the returned events as having been seen by this
            medium.

        :rtype: EventQuerySet
        :returns: A queryset of events.
        """
        events = self.get_filtered_events(**event_filters)
        subscriptions = Subscription.objects.cache_related().filter(
            medium=self
        )

        subscription_q_objects = [
            Q(
                eventactor__entity__in=self.followed_by(sub.subscribed_entities()),
                source=sub.source
            )
            for sub in subscriptions if sub.only_following
        ]
        subscription_q_objects.append(
            Q(source__in=[sub.source for sub in subscriptions if not sub.only_following]))

        events = events.cache_related().filter(reduce(or_, subscription_q_objects))
        return events

    @transaction.atomic
    def entity_events(self, entity, **event_filters):
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
        :param start_time: Only return events that occurred after the
            given time. If no time is given for this argument, no
            filtering is done.

        :type end_time: datetime.datetime (optional)
        :param end_time: Only return events that occurred before the
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

        :type actor: Entity (optional)
        :param actor: Only include events with the given entity as an
            actor.

        :type mark_seen: Boolean (optional)
        :param mark_seen: Create a side effect in the database that
            marks all the returned events as having been seen by this
            medium.

        :rtype: EventQuerySet
        :returns: A queryset of events.
        """
        events = self.get_filtered_events(**event_filters)

        subscriptions = Subscription.objects.filter(medium=self)
        subscriptions = self.subset_subscriptions(subscriptions, entity)

        subscription_q_objects = [
            Q(
                eventactor__entity__in=self.followed_by(entity),
                source=sub.source
            )
            for sub in subscriptions if sub.only_following
        ]
        subscription_q_objects.append(
            Q(source__in=[sub.source for sub in subscriptions if not sub.only_following])
        )

        return [
            event for event in events.filter(reduce(or_, subscription_q_objects))
            if self.filter_source_targets_by_unsubscription(event.source_id, [entity])
        ]

    @transaction.atomic
    def events_targets(self, entity_kind=None, **event_filters):
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
        :param start_time: Only return events that occurred after the
            given time. If no time is given for this argument, no
            filtering is done.

        :type end_time: datetime.datetime (optional)
        :param end_time: Only return events that occurred before the
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

        :type actor: Entity (optional)
        :param actor: Only include events with the given entity as an
            actor.

        :type mark_seen: Boolean (optional)
        :param mark_seen: Create a side effect in the database that
            marks all the returned events as having been seen by this
            medium.

        :rtype: List of tuples
        :returns: A list of tuples in the form ``(event, targets)``
            where ``targets`` is a list of entities.
        """
        events = self.get_filtered_events(**event_filters)
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
        and the subscription's sub-entity-kind is the same as that of
        the entity's.

        :type subscriptions: QuerySet
        :param subscriptions: A QuerySet of subscriptions to subset.

        :type entity: (optional) Entity
        :param entity: Subset subscriptions to only those relevant for
            this entity.

        :rtype: QuerySet
        :returns: A queryset of filtered subscriptions.
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

        :rtype: Dictionary
        :returns: A dictionary of the form ``{source_id: entities}``
            where ``entities`` is a list of entities unsubscribed from
            that source for this medium.
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

    def get_filtered_events_queries(self, start_time, end_time, seen, include_expired, actor):
        """Return Q objects to filter events table to relevant events.

        The filters that are applied are those passed in from the
        method that is querying the events table: One of ``events``,
        ``entity_events`` or ``events_targets``. The arguments have
        the behavior documented in those methods.

        :rtype: List of Q objects
        :returns: A list of Q objects, which can be used as arguments
            to ``Event.objects.filter``.
        """
        now = datetime.utcnow()
        filters = []
        if start_time is not None:
            filters.append(Q(time__gte=start_time))
        if end_time is not None:
            filters.append(Q(time__lte=end_time))
        if not include_expired:
            filters.append(Q(time_expires__gte=now))

        # Check explicitly for True and False as opposed to None
        #   - `seen==False` gets unseen notifications
        #   - `seen is None` does no seen/unseen filtering
        if seen is True:
            filters.append(Q(eventseen__medium=self))
        elif seen is False:
            unseen_ids = _unseen_event_ids(medium=self)
            filters.append(Q(id__in=unseen_ids))

        # Filter by actor
        if actor is not None:
            filters.append(Q(eventactor__entity=actor))

        return filters

    def get_filtered_events(
            self, start_time=None, end_time=None, seen=None, mark_seen=False, include_expired=False, actor=None):
        """Retrieves events, filters by event level filters, and marks them as
        seen if necessary.

        :rtype: EventQuerySet
        :returns: All events which match the given filters.
        """
        filtered_events_queries = self.get_filtered_events_queries(start_time, end_time, seen, include_expired, actor)
        events = Event.objects.filter(*filtered_events_queries)
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
        inherits ``Medium``, to define custom semantics for the
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

        Return a queryset of the entities that the given entities are
        following. This needs to be the inverse of ``followers_of``.

        :type entities: Entity or EntityQuerySet
        :param entities: The Entity, or QuerySet of Entities of interest.

        :rtype: EntityQuerySet
        :returns: A QuerySet of all the entities followed by any of
            those given.
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
        inherits ``Medium``, to define custom semantics for the
        ``only_following`` flag on relevant ``Subscription``
        objects. Overriding this method, and ``followed_by`` will be
        sufficient to define that behavior. This method is not useful
        to call directly, but is used by the methods that filter
        events and targets.

        This implementation attempts to provide a sane default. In
        this implementation, the followers of the entities passed in
        are defined to be the entities themselves, and their
        sub-entities.

        That is, the followers of individual entities are themselves,
        and if the entity has sub-entities, those sub-entities. This
        works as a default implementation, but, for example, an
        alternate medium may wish to define the opposite behavior,
        where an the followers of an individual entity are themselves
        and all of their super-entities.

        Return a queryset of the entities that follow the given
        entities. This needs to be the inverse of ``followed_by``.

        :type entities: Entity or EntityQuerySet
        :param entities: The Entity, or QuerySet of Entities of interest.

        :rtype: EntityQuerySet
        :returns: A QuerySet of all the entities who are followers of
            any of those given.
        """
        if isinstance(entities, Entity):
            entities = Entity.objects.filter(id=entities.id)
        sub_entities = EntityRelationship.objects.filter(
            super_entity__in=entities).values_list('sub_entity')
        followers_of = Entity.objects.filter(
            Q(id__in=entities) | Q(id__in=sub_entities))
        return followers_of

    def render(self, events):
        """
        Renders a list of events for this medium. The events first have their contexts loaded.
        Afterwards, the rendered events are returned as a dictionary keyed on the event itself.
        The key points to a tuple of (txt, html) renderings of the event.

        :type events: list
        :param events: A list or queryset of Event models.

        :rtype: dict
        :returns: A dictionary of rendered text and html tuples keyed on the provided events.
        """
        from entity_event import context_loader
        context_loader.load_contexts_and_renderers(events, [self])
        return {e: e.render(self) for e in events}


@python_2_unicode_compatible
class Source(models.Model):
    """A ``Source`` is an object in the database that represents where
    events come from. These objects only require a few fields,
    ``name``, ``display_name`` ``description``, and ``group``.
    Source objects categorize events
    based on where they came from, or what type of information they
    contain. Each source should be fairly fine grained, with broader
    categorizations possible through ``SourceGroup`` objects. Sources
    can be created with ``Source.objects.create`` using the following
    parameters:

    :type name: str
    :param name: A short, unique name for the source.

    :type display_name: str
    :param display_name: A short, human readable name for the source.
        Does not need to be unique.

    :type description: str
    :param description: A human readable description of the source.

    :type group: SourceGroup
    :param group: A SourceGroup object. A broad grouping of where the
        events originate.

    Storing source objects in the database servers two purposes. The
    first is to provide an object that Subscriptions can reference,
    allowing different categories of events to be subscribed to over
    different mediums. The second is to allow source instances to
    store a reference to a function which can populate event contexts
    with additional information that is relevant to the source. This
    allows ``Event`` objects to be created with minimal data
    duplication.

    Once sources are created, they will primarily be used to
    categorize events, as each ``Event`` object requires a reference
    to a source. Additionally they will be referenced by
    ``Subscription`` objects to route events of the given source to be
    handled by a given medium.
    """
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()
    group = models.ForeignKey('SourceGroup')

    def __str__(self):
        """Readable representation of ``Source`` objects."""
        return self.display_name


@python_2_unicode_compatible
class SourceGroup(models.Model):
    """A ``SourceGroup`` object is a high level categorization of
    events. Since ``Source`` objects are meant to be very fine
    grained, they are collected into ``SourceGroup`` objects. There is
    no additional behavior associated with the source groups other
    than further categorization. Source groups can be created with
    ``SourceGroup.objects.create``, which takes the following
    arguments:

    :type name: str
    :param name: A short, unique name for the source group.

    :type display_name: str
    :param display_name: A short, human readable name for the source
        group. Does not need to be unique.

    :type description: str
    :param description: A human readable description of the source
        group.
    """
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()

    def __str__(self):
        """Readable representation of ``SourceGroup`` objects."""
        return self.display_name


@python_2_unicode_compatible
class Unsubscription(models.Model):
    """Because django-entity-event allows for whole groups to be
    subscribed to events at once, unsubscribing an entity is not as
    simple as removing their subscription object. Instead, the
    Unsubscription table provides a simple way to ensure that an
    entity does not see events if they don't want to.

    Unsubscriptions are created for a single entity at a time, where
    they are unsubscribed for events from a source on a medium. This
    is stored as an ``Unsubscription`` object in the database, which
    can be created using ``Unsubscription.objects.create`` using the
    following arguments:

    :type entity: Entity
    :param entity: The entity to unsubscribe.

    :type medium: Medium
    :param medium: The ``Medium`` object representing where they don't
        want to see the events.

    :type source: Source
    :param source: The ``Source`` object representing what category
        of event they no longer want to see.

    Once an ``Unsubscription`` object is created, all of the logic to
    ensure that they do not see events form the given source by the
    given medium is handled by the methods used to query for events
    via the ``Medium`` object. That is, once the object is created, no
    more work is needed to unsubscribe them.
    """
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


class SubscriptionQuerySet(QuerySet):
    """A custom QuerySet for Subscriptions.
    """

    def cache_related(self):
        """
        Cache any related objects that we may use
        :return:
        """
        return self.select_related('medium', 'source', 'entity', 'sub_entity_kind')


@python_2_unicode_compatible
class Subscription(models.Model):
    """Which types of events are available to which mediums is controlled
    through ``Subscription`` objects. By creating a ``Subscription``
    object in the database, you are storing that events from a given
    ``Source`` object should be available to a given ``Medium``
    object.

    Each ``Subscription`` object can be one of two levels, either an
    individual subscription or a group subscription. Additionally,
    each ``Subscription`` object can be one of two types of
    subscription, either a global subscription, or an "only following"
    subscription. ``Subscription`` objects are created using
    ``Subscription.objects.create`` which takes the following
    arguments:

    :type medium: Medium
    :param medium: The ``Medium`` object to make events available to.

    :type source: Source
    :param source: The ``Source`` object that represents the category
        of events to make available.

    :type entity: Entity
    :param entity: The entity to subscribe in the case of an
        individual subscription, or in the case of a group
        subscription, the super-entity of the group.

    :type sub_entity_kind: (optional) EntityKind
    :param sub_entity_kind: When creating a group subscription, this
        is a foreign key to the ``EntityKind`` of the sub-entities to
        subscribe. In the case of an individual subscription, this should
        be ``None``.

    :type only_following: Boolean
    :param only_following: If ``True``, events will be available to
        entities through the medium only if the entities are following
        the actors of the event. If ``False``, the events will all
        be available to all the entities through the medium.

    When a ``Medium`` object is used to query for events, only the
    events that have a subscription for their source to that medium
    will ever be returned. This is an extremely useful property that
    allows complex subscription logic to be handled simply by storing
    subscription objects in the database.

    Storing subscriptions is made simpler by the ability to subscribe
    groups of entities with a single subscription object.  Groups of
    entities of a given kind can be subscribed by subscribing their
    super-entity and providing the ``sub_entity_kind`` argument.

    Subscriptions further are specified to be either an "only following"
    subscription or not. This specification controls what
    events will be returned when ``Medium.entity_events`` is called,
    and controls what targets are returned when
    ``Medium.events_targets`` is called.

    For example, if events are created for a new photo being uploaded
    (from a single source called, say "photos"), and we want to provide
    individuals with a notification in their newsfeed (through a
    medium called "newsfeed"), we want to be able to display only the
    events where the individual is tagged in the photo. By setting
    ``only_following`` to true the following code would only return
    events where the individual was included in the ``EventActor`` s,
    rather than returning all "photos" events:

    .. code-block:: python

        user_entity = Entity.objects.get_for_obj(user)
        newsfeed_medium = Medium.objects.get(name='newsfeed')
        newsfeed.entity_events(user)

    The behavior of what constitutes "following" is controlled by the
    Medium class. A default implementation of following is provided
    and documented in the ``Medium.followers_of`` and
    ``Medium.followed_by`` methods, but could be extended by
    subclasses of Medium.
    """
    medium = models.ForeignKey('Medium')
    source = models.ForeignKey('Source')
    entity = models.ForeignKey(Entity, related_name='+')
    sub_entity_kind = models.ForeignKey(EntityKind, null=True, related_name='+', default=None)
    only_following = models.BooleanField(default=True)

    objects = SubscriptionQuerySet.as_manager()

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

        :rtype: EntityQuerySet
        :returns: A QuerySet of all the entities that are a part of
            this subscription.
        """
        if self.sub_entity_kind is not None:
            sub_entities = self.entity.sub_relationships.filter(
                sub_entity__entity_kind=self.sub_entity_kind).values_list('sub_entity')
            entities = Entity.objects.filter(id__in=sub_entities)
        else:
            entities = Entity.objects.filter(id=self.entity.id)
        return entities


class EventQuerySet(QuerySet):
    """A custom QuerySet for Events.
    """

    def cache_related(self):
        """
        Cache any related objects that we may use
        :return:
        """
        return self.select_related(
            'source'
        ).prefetch_related(
            'source__group'
        )

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

    def load_contexts_and_renderers(self, medium):
        """
        Loads context data into the event ``context`` variable. This method
        destroys the queryset and returns a list of events.
        """
        from entity_event import context_loader
        return context_loader.load_contexts_and_renderers(self, [medium])


class EventManager(models.Manager):
    """A custom Manager for Events.
    """
    def get_queryset(self):
        """Return the EventQuerySet.
        """
        return EventQuerySet(self.model)

    def cache_related(self):
        """
        Return a queryset with prefetched values
        :return:
        """
        return self.get_queryset().cache_related()

    def mark_seen(self, medium):
        """Creates EventSeen objects for the provided medium for every event
        in the queryset.

        Creating these EventSeen objects ensures they will not be
        returned when passing ``seen=False`` to any of the medium
        event retrieval functions, ``events``, ``entity_events``, or
        ``events_targets``.
        """
        return self.get_queryset().mark_seen(medium)

    def load_contexts_and_renderers(self, medium):
        """
        Loads context data into the event ``context`` variable. This method
        destroys the queryset and returns a list of events.
        """
        return self.get_queryset().load_contexts_and_renderers(medium)

    @transaction.atomic
    def create_event(self, actors=None, ignore_duplicates=False, **kwargs):
        """Create events with actors.

        This method can be used in place of ``Event.objects.create``
        to create events, and the appropriate actors. It takes all the
        same keywords as ``Event.objects.create`` for the event
        creation, but additionally takes a list of actors, and can be
        told to not attempt to create an event if a duplicate event
        exists.

        :type source: Source
        :param source: A ``Source`` object representing where the
            event came from.

        :type context: dict
        :param context: A dictionary containing relevant
            information about the event, to be serialized into
            JSON. It is possible to load additional context
            dynamically  when events are fetched. See the
            documentation on the ``ContextRenderer`` model.

        :type uuid: str
        :param uuid: A unique string for the event. Requiring a
            ``uuid`` allows code that creates events to ensure they do
            not create duplicate events. This id could be, for example
            some hash of the ``context``, or, if the creator is
            unconcerned with creating duplicate events a call to
            python's ``uuid1()`` in the ``uuid`` module.

        :type time_expires: datetime (optional)
        :param time_expires: If given, the default methods for
            querying events will not return this event after this time
            has passed.

        :type actors: (optional) List of entities or list of entity ids.
        :param actors: An ``EventActor`` object will be created for
            each entity in the list. This allows for subscriptions
            which are only following certain entities to behave
            appropriately.

        :type ignore_duplicates: (optional) Boolean
        :param ignore_duplicates: If ``True``, a check will be made to
            ensure that an event with the give ``uuid`` does not exist
            before attempting to create the event. Setting this to
            ``True`` allows the creator of events to gracefully ensure
            no duplicates are created.

        :rtype: Event
        :returns: The created event. Alternatively if a duplicate
            event already exists and ``ignore_duplicates`` is
            ``True``, it will return ``None``.
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
    """``Event`` objects store information about events. By storing
    events, from a given source, with some context, they are made
    available to any ``Medium`` object with an appropriate
    subscription. Events can be created with
    ``Event.objects.create_event``, documented above.

    When creating an event, the information about what occurred is
    stored in a JSON blob in the ``context`` field. This context can
    be any type of information that could be useful for displaying
    events on a given Medium. It is entirely the role of the
    application developer to ensure that there is agreement between
    what information is stored in ``Event.context`` and what
    information the code the processes and displays events on each
    medium expects.

    Events will usually be created by code that also created, or knows
    about the ``Source`` object that is required to create the event.
    To prevent storing unnecessary data in the context, this code can
    define a context loader function when creating this source, which
    can be used to dynamically fetch more data based on whatever
    limited amount of data makes sense to store in the context. This
    is further documented in the ``Source`` documentation.
    """
    source = models.ForeignKey('Source')
    context = jsonfield.JSONField()
    time = models.DateTimeField(auto_now_add=True, db_index=True)
    time_expires = models.DateTimeField(default=datetime.max, db_index=True)
    uuid = models.CharField(max_length=128, unique=True)

    objects = EventManager()

    def __init__(self, *args, **kwargs):
        super(Event, self).__init__(*args, **kwargs)
        # A dictionary that is populated with renderers after the contexts have been
        # properly loaded. When renderers are available, the 'render' method may be
        # called with a medium and optional observer
        self._context_renderers = {}

    def _merge_medium_additional_context_with_context(self, medium):
        """
        If the medium has additional context properties, merge those together here in the
        main context before rendering.
        """
        if medium.additional_context:
            context = self.context.copy()
            context.update(medium.additional_context)
            return context
        else:
            return self.context

    def render(self, medium, observing_entity=None):
        """
        Returns the rendered event as a tuple of text and html content. This information
        is filled out with respect to which medium is rendering the event, what context
        renderers are available with the prefetched context, and which optional entity
        may be observing the rendered event.
        """
        if medium not in self._context_renderers:
            raise RuntimeError('Context and renderer for medium {0} has not or cannot been fetched'.format(medium))
        else:
            context = self._merge_medium_additional_context_with_context(medium)
            return self._context_renderers[medium].render_context_to_text_html_templates(context)

    def get_serialized_context(self, medium):
        """
        Returns the serialized context of the event for a specific medium
        :param medium:
        :return:
        """
        if medium not in self._context_renderers:
            raise RuntimeError('Context and renderer for medium {0} has not or cannot been fetched'.format(medium))
        else:
            context = self._merge_medium_additional_context_with_context(medium)
            return self._context_renderers[medium].get_serialized_context(context)

    def __str__(self):
        """Readable representation of ``Event`` objects."""
        s = '{source} event at {time}'
        source = self.source.__str__()
        time = self.time.strftime('%Y-%m-%d::%H:%M:%S')
        return s.format(source=source, time=time)


class AdminEvent(Event):
    """A proxy model used to provide a separate interface for event
    creation through the django-admin interface.
    """
    class Meta:
        proxy = True


@python_2_unicode_compatible
class EventActor(models.Model):
    """``EventActor`` objects encode what entities were involved in an
    event. They provide the information necessary to create "only
    following" subscriptions which route events only to the entities
    that are involved in the event.

    ``EventActor`` objects should not be created directly, but should
    be created as part of the creation of ``Event`` objects, using
    ``Event.objects.create_event``.
    """
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
    """``EventSeen`` objects store information about where and when an
    event was seen. They store the medium that the event was seen on,
    and what time it was seen. This information is used by the event
    querying methods on ``Medium`` objects to filter events by whether
    or not they have been seen on that medium.

    ``EventSeen`` objects should not be created directly, but should
    be created by using the ``EventQuerySet.mark_seen`` method,
    available on the QuerySets returned by the event querying methods.
    """
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


def _unseen_event_ids(medium):
    """Return all events that have not been seen on this medium.
    """
    query = '''
    SELECT event.id
    FROM entity_event_event AS event
        LEFT OUTER JOIN (SELECT *
                         FROM entity_event_eventseen AS seen
                         WHERE seen.medium_id=%s) AS eventseen
            ON event.id = eventseen.event_id
    WHERE eventseen.medium_id IS NULL
    '''
    unseen_events = Event.objects.raw(query, params=[medium.id])
    ids = [e.id for e in unseen_events]
    return ids


@python_2_unicode_compatible
class RenderingStyle(models.Model):
    """
    Defines a rendering style. This is used to group together mediums that have
    similar rendering styles and allows context renderers to be used across
    mediums.
    """
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64, default='')

    def __str__(self):
        return self.display_name


@python_2_unicode_compatible
class ContextRenderer(models.Model):
    """``ContextRenderer`` objects store information about how
    a source or source group is rendered with a particular rendering style, along with
    information for loading the render context in a database-efficient
    manner.

    Of the four template fields: `text_template_path`, 'html_template_path',
    `text_template`, and `html_template`, at least one must be
    non-empty. Both a text and html template may be provided, either
    through a path to the template, or a raw template object.
    If both are provided, the template given in the path will be used and
    the text template will be ignored.

    This object is linked to a `RenderingStyle` object. This is how the
    context renderer is associated with various `Medium` objects. It also
    provides the `source` that uses the renderer. If a `source_group` is specified,
    all sources under that group use this context renderer for the rendering style.

    The `context_hints` provide the ability to fetch model IDs of an event context that
    are stored in the database. For example, if an event context has a `user` key that
    points to the PK of a Django `User` model, the context hints for it would be specified
    as follows:

    .. code-block:: python

        {
            'user': {
                'app_name': 'auth',
                'model_name': 'User',
            }
        }

    With these hints, the 'user' field in the event context will be treated as a PK in the
    database and fetched appropriately. If one wishes to perform and prefetch or select_related
    calls, the following options can be added:

    .. code-block:: python

        {
            'user': {
                'app_name': 'auth',
                'model_name': 'User',
                'select_related': ['foreign_key_field', 'one_to_one_field'],
                'prefetch_related': ['reverse_foreign_key_field', 'many_to_many_field'],
            }
        }

    Note that as many keys can be defined that have corresponding keys in the event context for
    the particular source or source group. Also note that the keys in the event context can
    be embedded anywhere in the context and can also point to a list of PKs. For example:

    .. code-block:: python

        {
            'my_context': {
                'user': [1, 3, 5, 10],
                'other_context_info': 'other_info_string',
            },
            'more_context': {
                'hello': 'world',
            }
        }

    In the above case, `User` objects with the PKs 1, 3, 5, and 10 will be fetched and loaded into
    the event context whenever rendering is performed.
    """
    name = models.CharField(max_length=64, unique=True)

    # The various templates that can be used for rendering
    text_template_path = models.CharField(max_length=256, default='')
    html_template_path = models.CharField(max_length=256, default='')
    text_template = models.TextField(default='')
    html_template = models.TextField(default='')

    # The source or source group of the event. It can only be one or the other
    source = models.ForeignKey(Source, null=True)
    source_group = models.ForeignKey(SourceGroup, null=True)

    # The rendering style. Used to associated it with a medium
    rendering_style = models.ForeignKey(RenderingStyle)

    # Contains hints on how to fetch the context from the database
    context_hints = jsonfield.JSONField(null=True, default=None)

    class Meta:
        unique_together = ('source', 'rendering_style')

    def get_sources(self):
        return [self.source] if self.source_id else self.source_group.source_set.all()

    def __str__(self):
        return self.name

    def get_serialized_context(self, context):
        """
        Serializes the context using the serializer class.
        """
        return DefaultContextSerializer(context).data

    def render_text_or_html_template(self, context, is_text=True):
        """
        Renders a text or html template based on either the template path or the
        stored template.
        """
        template_path = getattr(self, '{0}_template_path'.format('text' if is_text else 'html'))
        template = getattr(self, '{0}_template'.format('text' if is_text else 'html'))
        if template_path:
            return render_to_string(template_path, context)
        elif template:
            return Template(template).render(Context(context))
        else:
            return ''

    def render_context_to_text_html_templates(self, context):
        """Render the templates with the provided context.

        Args:
          A loaded context.

        Returns:
          A tuple of (rendered_text, rendered_html). Either, but not both
          may be an empty string.
        """
        # Process text template:
        return (
            self.render_text_or_html_template(context, is_text=True).strip(),
            self.render_text_or_html_template(context, is_text=False).strip(),
        )
