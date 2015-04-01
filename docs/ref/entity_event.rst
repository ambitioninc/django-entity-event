.. _ref-entity_event:

Code documentation
==================

.. automodule:: entity_event.models

.. autoclass:: Medium()

   .. automethod:: events(self, **event_filters)

   .. automethod:: entity_events(self, entity, **event_filters)

   .. automethod:: events_targets(self, entity_kind, **event_filters)

   .. automethod:: followed_by(self, entities)

   .. automethod:: followers_of(self, entities)

   .. automethod:: render(self, events)


.. autoclass:: Source()

.. autoclass:: SourceGroup()

.. autoclass:: Unsubscription()

.. autoclass:: Subscription()

   .. automethod:: subscribed_entities(self)

.. autoclass:: EventQuerySet()

   .. automethod:: mark_seen(self, medium)

.. autoclass:: EventManager()

   .. automethod:: create_event(self, source, context, uuid, time_expires, actors, ignore_duplicates)

   .. automethod:: mark_seen(self, medium)

.. autoclass:: EventActor()

.. autoclass:: EventSeen()

.. autoclass:: RenderingStyle()

.. autoclass:: ContextRenderer()