from django.contrib import admin

from entity_event.models import Medium, Event, Source, SourceGroup, Subscription, Unsubscription


class EventAdmin(admin.ModelAdmin):
    list_display = ('time', 'source')


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


admin.site.register(Medium, MediumAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Source, SourceAdmin)
admin.site.register(SourceGroup, SourceGroupAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Unsubscription, UnsubscriptionAdmin)
