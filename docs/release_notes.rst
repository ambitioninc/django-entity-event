Release Notes
=============

v0.4.4
------

* Added some optimizations during event fetching to select and prefetch some related objects

v0.4.3
------

* Added ability to get a serialized version of an events context data

v0.4.0
------

* Added 1.8 support and dropped 1.6 support for Django

v0.3.4
------

* Fixed django-entity migration dependency for Django 1.6

v0.3.3
------

* Added Django 1.7 compatibility and app config

v0.3.2
------

* Added an additional_context field in the Medium object that allows passing of additional context to event renderings.
* Added ability to define a default rendering style for all sources or source groups if a context renderer is not defined for a particular rendering style.

v0.3.1
------

* Fixes a bug where contexts can have any numeric type as a pk

v0.3.0
------

* Adds a template and context rendering system to entity event

v0.2
----

* This release provides the core features of django-entity-event
  - Event Creation
  - Subscription Management
  - Event Querying
  - Admin Panel
  - Documentation

v0.1
----

* This is the initial release of django-entity-event.
