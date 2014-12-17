.. _ref-entity_event:

Code documentation
==================

.. automodule:: entity_event.models

.. autoclass:: Medium
    :members: events, entity_events, events_targets, followed_by, followers_of

.. autoclass:: Source
    :members: get_context

.. autoclass:: SourceGroup

.. autoclass:: Unsubscription

.. autoclass:: Subscription
    :members: subscribed_entities

.. autoclass:: EventQuerySet
    :members: mark_seen

.. autoclass:: EventManager
    :members: create_event, mark_seen

.. autoclass:: Event
    :members: get_context

.. autoclass:: EventActor

.. autoclass:: EventSeen
