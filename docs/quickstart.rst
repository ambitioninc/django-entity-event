.. _quickstart:

Quickstart and Basic Usage
==========================

Django Entity Event is a great way to collect events that your users
care about into a unified location. The parts of your code base that
create these events are probably totally separate from the parts that
display them, which are also separate from the parts that manage
subscriptions to notifications. Django Entity Event makes separating
these concerns as simple as possible, and provides convenient
abstractions at each of these levels.

This quickstart guide handles the three parts of managing events and
notifications.

1. Creating, and categorizing events.
2. Defining mediums and subscriptions.
3. Querying events and presenting them to users.

If you are not already using Django Entity, this event framework won't
be particularly useful, and you should probably start by integrating
Django Entity into your application.


Creating and Categorizing Events
--------------------------------

Django Entity Event is structured such that all events come from a
:py:class:`~entity_event.models.Source`, and can be displayed to the
user from a variety of mediums. When we're creating events, we
don't need to worry much about what
:py:class:`~entity_event.models.Medium` the event will be displayed
on, we do need to know what the
:py:class:`~entity_event.models.Source` of the events are.

:py:class:`~entity_event.models.Source` objects are used to categorize
events. Categorizing events allows different types of events to be
consumed differently. So, before we can create an event, we need to
create a :py:class:`~entity_event.models.Source` object. It is a good
idea to use sources to do fine grained categorization of events. To
provide higher level groupings, all sources must reference a
:py:class:`~entity_event.models.SourceGroup` object. These objects are
very simple to create. Here we will make a single source group and two
different sources

.. code-block:: python

    from entity_event import Source, SourceGroup

    yoursite_group = SourceGroup.objects.create(
        name='yoursite',
        display_name='Yoursite',
        description='Events on Yoursite'
    )

    photo_source = Source.objects.create(
        group=yoursite_group,
        name='photo-tag',
        display_name='Photo Tag',
        description='You have been tagged in a photo'
    )

    product_source = Source.objects.create(
        group=yoursite_group,
        name='new-product',
        display_name='New Product',
        description='There is a new product on YourSite'
    )

As seen above, the information required for these sources is fairly
minimal. It is worth noting that while we only defined a single
:py:class:`~entity_event.models.SourceGroup` object, it will often
make sense to define more logical
:py:class:`~entity_event.models.SourceGroup` objects.

Once we have sources defined, we can begin creating events. To create
an event we use the :py:meth:`Event.objects.create_event
<entity_event.models.EventManager.create_event>` method. To create an
event for the "photo-tag" group, we just need to know the source of
the event, what entities are involved, and some information about what
happened

.. code-block:: python

    from entity_event import Event

    # Assume we're within the photo tag processing code, and we'll
    # have access to variables entities_tagged, photo_owner, and
    # photo_location

    Event.objects.create_event(
        source=photo_source,
        actors=entities_tagged,
        context={
            'photo_owner': photo_owner
            'photo_location': photo_location
        }
    )

The code above is all that's required to store an event. While this is
a fairly simple interface for creating events, in some applications it
may be easier to read, and less intrusive in application code to use
django-signals in the application code, and create events in signal
handlers. In either case, We're ready to discuss subscription
management.


Managing Mediums and Subscriptions to Events
--------------------------------------------

Once the events are created, we need to define how the users of our
application are going to interact with the events. There are a large
number of possible ways to notify users of events. Email, newsfeeds,
notification bars, are all examples. Django Entity Event doesn't
handle the display logic for notifying users, but it does handle the
subscription and event routing/querying logic that determines which
events go where.

To start, we must define a :py:class:`~entity_event.models.Medium`
object for each method our users will consume events from. Storing
:py:class:`~entity_event.models.Medium` objects in the database has
two purposes. First, it is referenced when subscriptions are
created. Second the :py:class:`~entity_event.models.Medium` objects
provide an entry point to query for events and have all the
subscription logic and filtering taken care of for you.

Like :py:class:`~entity_event.models.Source` objects,
:py:class:`~entity_event.models.Medium` objects are simple to create

.. code-block:: python

    from entity_event import Medium

    email_medium = Medium.objects.create(
        name="email",
        display_name="Email",
        description="Email Notifications"
    )

    newsfeed_medium = Medium.objects.create(
        name="newsfeed",
        display_name="NewsFeed",
        description="Your personal feed of events"
    )

At first, none of the events we have been creating are accessible by
either of these mediums. In order for the mediums to have access to
the events, an appropriate
:py:class:`~entity_event.models.Subscription` object needs to be
created. Creating a :py:class:`~entity_event.models.Subscription`
object encodes that an entity, or group of entities, wants to receive
notifications of events from a given source, by a given medium. For
example, we can create a subscription so that all the sub-entities of
an ``all_users`` entity will receive notifications of new products in
their newsfeed

.. code-block:: python

    from entity import EntityKind
    from entity_event import Subscription

    Subscription.objects.create(
        medium=newsfeed_medium,
        source=product_source,
        entity=all_users,
        sub_entity_kind=EntityKind.objects.get(name='user'),
        only_following=False
    )

With this :py:class:`~entity_event.models.Subscription` object
defined, all events from the new product source will be available to
the newsfeed medium.

If we wanted to create a subscription for users to get email
notifications when they've been tagged in a photo, we will also create
a :py:class:`~entity_event.models.Subscription` object. However,
unlike the new product events, not every event from the photos source
is relevant to every user. We want to limit the events they receive
emails about to the events where they are tagged in the photo.

In code above, you may notice the ``only_following=False``
argument. This argument controls whether all events are relevant for
the subscription, or if the events are only relevant if they are
related to the entities being subscribed. Since new products are
relevant to all users, we set this to ``False``. To create a
subscription for users to receive emails about photos they're tagged
in, we'll define the subscription as follows

.. code-block:: python

    Subscription.objects.create(
        medium=email_medium,
        source=photo_source,
        entity=all_users,
        sub_entity_kind=EntityKind.objects.get(name='user'),
        only_following=True
    )

This will only notify users if an entity they're following is tagged
in a photo. By default, entities follow themselves and their super
entities.

Creating subscriptions for a whole group of people with a single entry
into the database is very powerful. However, some users may wish to
opt out of certain types of notifications. To accommodate this, we can
create an :py:class:`~entity_event.models.Unsubscription`
object. These are used to unsubscribe a single entity from receiving
notifications of a given source on a given medium. For example if a
user wants to opt out of new product notifications in their newsfeed,
we can create an :py:class:`~entity_event.models.Unsubscription`
object for them

.. code-block:: python

    from entity_event import Unsubscription

    # Assume we have an entity, unsubscriber who wants to unsubscribe
    Unsubscription.objects.create(
        entity=unsubscriber,
        source=product_source,
        medium=newsfeed_medium
    )

Once this object is stored in the database, this user will no longer
receive this type of notification.

Once we have :py:class:`~entity_event.models.Medium` objects set up
for the methods of sending notifications, and we have our entities
subscribed to sources of events on those mediums, we can use the
:py:class:`~entity_event.models.Medium` objects to query for events,
which we can then display to our users.


Querying Events
---------------

Once we've got events being created, and subscriptions to them for a
given medium, we'll want to display those events to our users. When
there are a large variety of events coming into the system from many
different sources, it would be very difficult to query the
:py:class:`~entity_event.models.Event` model directly while still
respecting all the :py:class:`~entity_event.models.Subscription` logic
that we hope to maintain.

For this reason, Django Entity Event provides three methods to make
querying for events` to display extremely simple. Since the
:py:class:`~entity_event.models.Medium` objects you've created should
correspond directly to a means by which you want to display events to
users, there are three methods of the
:py:class:`~entity_event.models.Medium` class to perform queries.

1. :py:meth:`Medium.events <entity_event.models.Medium.events>`
2. :py:meth:`Medium.entity_events <entity_event.models.Medium.entity_events>`
3. :py:meth:`Medium.events_targets <entity_event.models.Medium.events_targets>`

Each of these methods return somewhat different views into the events
that are being stored in the system. In each case, though, you will
call these methods from an instance of
:py:class:`~entity_event.models.Medium`, and the events returned will
only be events for which there is a corresponding
:py:class:`~entity_event.models.Subscription` object.

The :py:meth:`Medium.events <entity_event.models.Medium.events>`
method can be used to return all the events for that medium. This
method is useful for mediums that want to display events without any
particular regard for who performed the events. For example, we could
have a medium that aggregated all of the events from the new products
source. If we had a medium, ``all_products_medium``, with the
appropriate subscriptions set up, getting all the new product events
is as simple as

.. code-block:: python

    all_products_medium.events()

The :py:meth:`Medium.entity_events
<entity_event.models.Medium.entity_events>` method can be used to get
all the events for a given entity on that medium. It takes a single
entity as an argument, and returns all the events for that entity on
that medium. We could use this method to get events for an individual
entity's newsfeed. If we have a large number of sources creating
events, with subscriptions between those sources and the newsfeed,
aggregating them into one QuerySet of events is as simple as

.. code-block:: python

   newsfeed_medium.entity_events(user_entity)

There are some mediums that notify users of events independent of a
pageview's request/response cycle. For example, an email medium will
want to process batches of events, and need information about who to
send the events to. For this use case, the
:py:meth:`Medium.events_targets
<entity_event.models.Medium.events_targets>` method can be
used. Instead of providing a ``EventQueryset``, it provides a list of
tuples in the form ``(event, targets)``, where ``targets`` is a list
of the entities that should receive that notification. We could use
this function to send emails about events as follows

.. code-block:: python

    from django.core.mail import send_mail

    new_emails = email_medium.events_targets(seen=False, mark_seen=True)

    for event, targets in new_emails:
        send_mail(
            subject = event.context["subject"]
            message = event.context["message"]
            recipient_list = [t.entity_meta["email"] for t in targets]
        )

As seen in the last example, these methods also support a number of
arguments for filtering the events based on properties of the events
themselves. All three methods support the following arguments:

- ``start_time``: providing a datetime object to this parameter will
  filter the events to only those that occurred at or after this time.
- ``end_time``: providing a datetime object to this parameter will
  filter the events to only those that occurred at or before this time.
- ``seen``: passing ``False`` to this argument will filter the events
  to only those which have not been marked as having been seen.
- ``include_expired``: defaults to ``False``, passing ``True`` to this
  argument will include events that are expired. Events with
  expiration are discussed in
  :py:meth:`~entity_event.models.EventManager.create_event`.
- ``actor``: providing an entity to this parameter will filter the
  events to only those that include the given entity as an actor.

Finally, all of these methods take an argument ``mark_seen``. Passing
``True`` to this argument will mark the events as having been seen by
that medium so they will not show up if ``False`` is passed to the
``seen`` filtering argument.

Using these three methods with any combination of the event filters
should make virtually any event querying task simple.
