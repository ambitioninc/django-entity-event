Advanced Features
=================

The :ref:`quickstart` guide covers the common use cases of Django Entity
Event. In addition to the basic uses for creating, storing, and
querying events, there are some more advanced uses supported for
making Django Entity Event more efficient and flexible.

This guide will cover the following advanced use cases:

- Dynamically loading context using ``context_loader``
- Customizing the behavior of ``only_following`` by sub-classing
  :py:class:`~entity_event.models.Medium`.


Custom Context Loaders
----------------------

When events are created, it is up to the creator of the event to
decide what information gets stored in the event's ``context``
field. In many cases it makes sense to persist all of the data
necessary to display the event to a user.

In some cases, however the ``context`` of the event can be very large,
and storing all of the information would mean duplicating a large
amount of data that exists elsewhere in your database. It's desirable
to have all this data available in the ``context`` field, but it isn't
desirable to repeatedly duplicate large amounts of information.

If the creator of the events can guarantee that some of the
information about the event will always be available in the database,
or computable from some subset of the data that could be stored in the
context, they can use the ``Source.context_loader`` field to provide a
path to an importable function to dynamically load the context when
the events are fetched.

If for example, we are creating events about photo tags, and we don't
want to persist a full path to the photo, we can simply store a ``id``
for the photo, and then use a context loader to load it
dynamically. The function we would write to load the context would
look something like

.. code-block:: python

    # In module apps.photos.loaders

    def load_photo_context(context):
        photo = Photo.objects.get(id=context['photo_id'])
        context['photo_path'] = photo.path
        return context

Then, when defining our source for this type of event we would include
a path to this function in the ``context_loader`` field.

.. code-block:: python

    from entity_event import Source

    photo_tag_source = Source.objects.create(
        name="photo-tag",
        display_name="Photo Tag",
        description="You are tagged in a photo",
        group=photo_group,
        context_loader='apps.photos.loaders.load_photo_path'
    )

With this setup, all of the additional information can by dynamically
loaded into events, simply by calling :py:meth:`Event.get_context
<entity_event.models.Event.get_context>`.

The ``Source`` model also uses django's ``clean`` method to ensure
that only valid importable functions get saved in the
database. However, if this function is removed from the codebase,
without a proper migration, attempting to load context for events with
this source will fail.

There are a number of trade-offs in using a context loader. If the
underlying data is subject to change, accessing historic events could
cause errors in the application. Additionally, a context loader that
requires many runs to the database could cause accessing events to be
a much more expensive operation. In either of these cases it makes
more sense to store copies of the data in the ``context`` field of the
event.


Customizing Only-Following Behavior
-----------------------------------

In the quickstart, we discussed the use of "only following"
subscriptions to ensure that users only see the events that they are
interested in. In this discussion, we mentioned that by default,
entities follow themselves, and their super entities. This following
relationship is defined in two methods on the
:py:class:`~entity_event.models.Medium` model:
:py:meth:`Medium.followers_of
<entity_event.models.Medium.followers_of>` and
:py:meth:`Medium.followed_by
<entity_event.models.Medium.followed_by>`. These two methods are
inverses of each other and are used by the code that fetches events to
determine the semantics of "only following" subscriptions.

It is possible to customize the behavior of these types of
subscriptions by concretely inheriting from
:py:class:`~entity_event.models.Medium`, and overriding these two
functions. For example, we could define a type of medium that provides
the opposite behavior, where entities follow themselves and their
sub-entities.

.. code-block:: python

    from entity import Entity, EntityRelationship
    from entity_event import Medium

    class FollowSubEntitiesMedium(Medium):
        def followers_of(self, entities):
            if isinstance(entities, Entity):
                entities = Entity.objects.filter(id=entities.id)
            super_entities = EntityRelationship.objects.filter(
                sub_entity__in=entities).values_list('super_entity')
            followed_by = Entity.objects.filter(
                Q(id__in=entities) | Q(id__in=super_entities))
            return followed_by

        def followed_by(self, entities):
            if isinstance(entities, Entity):
                entities = Entity.objects.filter(id=entities.id)
            sub_entities = EntityRelationship.objects.filter(
                super_entity__in=entities).values_list('sub_entity')
            followers_of = Entity.objects.filter(
                Q(id__in=entities) | Q(id__in=sub_entities))
            return followers_of

With these methods overridden, the behavior of the methods
``FollowsubEntitiesMedium.events``,
``FollowsubEntitiesMedium.entity_events``, and
``FollowsubEntitiesMedium.events_targets`` should all behave as
expected.

It is entirely possible to define more complex following
relationships, potentially drawing on different source of information
for what entities should follow what entities. The only important
consideration is that the ``followers_of`` method must be the inverse
of the ``followed_by`` method. That is, for any set of entities, it
must hold that

.. code-block:: python

    followers_of(followed_by(entities)) == entities

and

.. code-block:: python

    followed_by(followers_of(entities)) == entities
