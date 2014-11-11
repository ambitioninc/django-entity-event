from django.db import models


class Medium(models.Model):
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()

    def __unicode__(self):
        return self.display_name


class Source(models.Model):
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()

    def __unicode__(self):
        return self.display_name


class Subscription(models.Model):
    medium = models.ForeignKey('Medium')
    source = models.ForeignKey('Source')
    entity = models.ForeignKey(Entity)
    subentity_type = models.ForeignKey(ContentType, null=True)

    def __unicode__(self):
        s = '{entity} to {source} by {medium}'
        entity = self.entity.__unicode__()
        source = self.source.__unicode__()
        medium = self.medium.__unicode__()
        return s.format(entity=entity, source=source, medium=medium)


class Unsubscription(models.Model):
    entity = models.ForeignKey(Entity)
    medium = models.ForeignKey('Medium')
    source = models.ForeignKey('Source')

    def __unicode__(self):
        s = '{entity} from {source} by {medium}'
        entity = self.entity.__unicode__()
        source = self.source.__unicode__()
        medium = self.medium.__unicode__()
        return s.format(entity=entity, source=source, medium=medium)


class Event(models.Model):
    entity = models.ForeignKey(Entity)
    subentity_type = models.ForeignKey(ContentType, null=True)
    source = models.ForeignKey(Source)
    context = jsonfield.JSONField()
    time = models.DateTimeField(auto_add_now=True)
    time_expires = models.DateTimeField(null=True, default=None)
    uuid = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        s = '{source} event at {time}'
        source = self.source.__unicode__()
        time = self.time.strftime('%Y-%m-%d::%H:%M:%S')
        return s.format(source=source, time=time)


class EventSeen(models.Model):
    event = models.ForeignKey('Event')
    medium = models.ForeignKey(Medium)
    time_seen = models.DateTimeField(null=True, default=None)

    def __unicode__(self):
        s = 'seen by {medium} at {time}'
        medium = self.medium.__unicode__()
        time = self.time_seen.strftime('%Y-%m-%d::%H:%M:%S')
        return s.format(medium=medium, time=time)
