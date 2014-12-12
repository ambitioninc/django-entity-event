from datetime import datetime
from uuid import uuid1

from django import forms
from django.contrib import admin
from django.forms.extras.widgets import SelectDateWidget

from entity_event.models import (
    AdminEvent, Event, EventActor, EventSeen, Medium, Source, SourceGroup, Subscription, Unsubscription
)


class AdminEventForm(forms.ModelForm):
    source = forms.ModelChoiceField(queryset=Source.objects.all())  # initial = Source.objects.get(name='admin')
    text = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'cols': '60'}))
    expires_date = forms.DateField(widget=SelectDateWidget(), required=False)
    expires_time = forms.TimeField(label='Expires time (UTC 24 hr) E.g. 18:25', required=False)

    class Meta:
        model = AdminEvent
        fields = ['source', 'text', 'expires_date', 'expires_time']

    def save(self, *args, **kwargs):
        self.clean()
        expires_date = self.cleaned_data['expires_date']
        expires_time = self.cleaned_data['expires_time']
        expires_datetime = (
            datetime.combine(expires_date, expires_time) if expires_date and expires_time else datetime.max)
        context = {'text': self.cleaned_data['text']}
        event = Event.objects.create(
            source=self.cleaned_data['source'],
            context=context,
            time_expires=expires_datetime,
            uuid=uuid1().hex
        )
        return event

    def save_m2m(self, *args, **kwargs):
        pass


class AdminEventAdmin(admin.ModelAdmin):
    list_display = ('time', 'source')
    form = AdminEventForm


class EventActorInline(admin.TabularInline):
    model = EventActor


class EventSeenInline(admin.TabularInline):
    model = EventSeen


class EventAdmin(admin.ModelAdmin):
    list_display = ('time', 'source')
    inlines = [
        EventActorInline,
        EventSeenInline
    ]


class MediumAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'description')


class SourceAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'description')


class SourceGroupAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'description')


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('entity', 'source', 'medium', 'sub_entity_kind', 'only_following')


class UnsubscriptionAdmin(admin.ModelAdmin):
    list_display = ('entity', 'medium', 'source')


admin.site.register(AdminEvent, AdminEventAdmin)
admin.site.register(Medium, MediumAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Source, SourceAdmin)
admin.site.register(SourceGroup, SourceGroupAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Unsubscription, UnsubscriptionAdmin)
