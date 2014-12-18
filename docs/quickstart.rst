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

1. Creating, categorizing, and storing events.
2. Managing which events go where, and who are subscribed to them.
3. Displaying events to users in different ways.


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

    update_source = Source.objects.create(
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


Managing Subscriptions to Events
--------------------------------


Querying and Displaying Events
------------------------------

