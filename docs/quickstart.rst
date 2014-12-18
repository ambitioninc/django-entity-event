Quickstart and Basic Usage
==========================

Django Entity Event is a great way to collect events that your users
care about into a unified location. The parts of your code base that
create these events are probably totally separate from the parts that
display them, which are also separate from the parts that manage
subscriptions to notifications. Django Entity Event makes separating
these concers as simple as possible, and provides convenient
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
``Source``, and can be displayed to the user from a variety of
``Mediums``. When we're creating events, we don't need to worry much
about what ``Medium`` the event will be displayed on, we do need to
know what the ``Source`` of the events are.

``Source`` objects are used to categorize events. Categorizing events
allows different types of events to be consumed differently. So,
before we can create an event, we need to create a ``Source``
object. It is a good idea to use sources to do fine grained
categorization of events. To provide higher level groupings, all
sources must reference a ``SourceGroup`` object. These objects are
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
``SourceGroup`` object, it will often make sense to define more
logical ``SourceGroup`` objects.

Once we have sources defined, we can begin creating events. To create
an event we use the ``Event.objects.create_event`` method. To create
an event for the "photo-tag" group, we just need to know the source of
the event, what entities are involved, and some information about what
happened.

..code-block:: python

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

To start, we must define a ``Medium`` object for each method our users
will consume events from. Storing ``Medium`` objects in the database
has two purposes. First, it is referenced when subscriptions are
created. Second the ``Medium`` objects provide an entry point to query
for events and have all the subscription logic and filtering taken
care of for you.

Like ``Source`` objects, ``Medium`` objects are simple to
create

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
the events, an appropriate ``Subscription`` object needs to be
created. Creating a ``Subscription`` object encodes that an entity, or
group of entities, wants to recieve notifications of events from a
given source, by a given medium. For example, we can create a
subscription so that all the sub-entities of an ``all_users`` entity
will recieve notifications of new products in their newsfeed

.. code-block:: python

    from entity import EntityKind
    from entity_event import Subscription

    Subscription.objects.create(
        medium=newsfeed_medium,
        source=product_source,
        entity=all_users,
        subentity_kind=EntityKind.objects.get(name='user'),
        only_following=False
    )

With this ``Subscription`` object defined, all events from the new
product source will be available to the newsfeed medium.

If we wanted to create a subscription for users to get email
notifications when they've been tagged in a photo, we will also create
a ``Subscription`` object. However, unlike the new product events, not
every event from the photos source is relevant to every user. We want
to limit the events they recieve emails about to the events where they
are tagged in the photo.

In code above, you may notice the ``only_following=False``
argument. This argument controls whether all events are relevant for
the subscription, or if the events are only relevant if they are
related to the entities being subscribed. Since new products are
relevant to all users, we set this to ``False``. To create a
subscription for users to recieve emails about photos they're tagged
in, we'll define the subscription as follows

.. code-block:: python

    Subscription.objects.create(
        medium=email_medium,
        source=photo_source,
        entity=all_users,
        subentity_kind=EntityKind.objects.get(name='user'),
        only_following=True
    )

This will only notify users if an entity they're following is tagged
in a photo. By default, entities follow themselves and their super
entities.

Creating subscriptions for a whole group of people with a single entry
into the database is very powerful. However, some users may wish to
opt out of certain types of notifications. To accomodate this, we can
create an ``Unsubscription`` object. These are used to unsubscribe a
single entity from recieving notifications of a given source on a
given medium. For example if a user wants to opt out of new product
notifications in their newsfeed, we can create an ``Unsubscription``
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
recieve this type of notification.

Once we have ``Medium`` objects set up for the methods of sending
notifications, and we have our entities subscribed to sources of
events on those mediums, we can use the ``Medium`` objects to query
for events, which we can then display to our users.


Querying and Events
-------------------
