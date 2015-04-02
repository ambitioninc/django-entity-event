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


Rendering Events
----------------

Django Entity Event comes complete with a rendering system for events. This is accomplished
by the setup of two different models:

1. :py:class:`~entity_event.models.RenderingStyle`: Defines a style of rendering.
2. :py:class:`~entity_event.models.ContextRenderer`: Defines the templates used
   for rendering, which rendering style it is, which source or source group it renders,
   and hints for fetching model PKs that are in event contexts.

When these models are in place, :py:class:`~entity_event.models.Medium` models can be configured
to point to a ``rendering_style`` of their choice. Events that have sources or source groups that
match those configured in associated :py:class:`~entity_event.models.ContextRenderer` models
can then be rendered using the ``render`` method on the medium.

The configuration and rendering is best explained using a complete example. First, let's
imagine that we are storing events that have contexts with information about Django User models.
These events have a source called ``user_logged_in`` and track every time a user logs in. An
example context is as follows:

.. code-block:: python

    {
        'user': 1, # The PK of the Django User model
        'login_time': 'Jan 10, 2014', # The time the user logged in
    }

Now let's say we have a Django template, ``user_logged_in.html`` that looks like the following:

.. code-block:: python

    User {{ user.username }} logged in at {{ login_time }}

In order to render the event with this template, we first set up a rendering style. This rendering
style is pretty short and could probably be displayed in many places that want to display short
messages (like a notification bar). So, we can make a ``short`` rendering style as followings:

.. code-block:: python

    short_rendering_style = RenderingStyle.objects.create(
        name='short',
        display_name='Short Rendering Style')

Now that we have our rendering style, we need to create a context renderer that has information about
what templates, source, rendering style, and context hints to use when rendering the event. In our case,
it would look like the following:

.. code-block:: python

    context_renderer = ContextRenderer.objects.create(
        render_style=RenderingStyle.objects.get(name='short'),
        name='short_login_renderer',
        html_template_path='my_template_dir/user_logged_in.html',
        source=Source.objects.get(name='user_logged_in'),
        context_hints={
            'user': {
                'app_name': 'auth',
                'model_name': 'User',
            }
        }
    )

In the above, we set up the context renderer to use the short rendering style, pointed it to our html template
that we created, and also pointed it to the source of the event. As you can see from the html template, we
want to reach inside of the Django User object and display the ``username`` field. In order to retrieve this
information, we have told our context renderer to treat the ``user`` key from the event context as a PK
to a Django ``User`` model that resides in the ``auth`` app.

With this information, we can now render the event using whatever medium we have set up in Django Entity
Event.

.. code-block:: python

    notification_medium = Medium.objects.get(name='notification')
    events = notification_medium.events()

    # Assume that two events were returned that have the following contexts
    # e1.context = {
    #    'user': 1, # Points to Jeff's user object
    #    'login_time': 'January 1, 2015',
    # }
    # e1.context = {
    #     'user': 2, # Points to Wes's user object
    #     'login_time': 'February 28, 2015',
    # }
    #
    # Pass the events into the medium's render method
    rendered_events = notification_medium.render(events)

    # The results are a dictionary keyed on each event. The keys point to a tuple
    # of text and html renderings.
    print(rendered_events[0][1])
    'jeff logged in at January 1, 2015'
    print(rendered_events[1][1])
    'wes logged in at February 28, 2015'

With the notion of rendering styles, the notification medium and any medium that can display short
messages can utilize the renderings of the events. Other rendering styles can still be made for
more complex renderings such as emails with special styling.

For more advanced options on how to perform prefetch and select_relateds in the fetched contexts,
view :py:class:`~entity_event.models.ContextRenderer`.

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
