# flake8: noqa
from .version import __version__

from .models import (
    Event, Medium, Source, SourceGroup, Subscription, Unsubscription
)

default_app_config = 'entity_event.apps.EntityEventConfig'
