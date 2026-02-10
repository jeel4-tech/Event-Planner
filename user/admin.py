from django.contrib import admin

# Register your models here.
from .models import Profile, Event


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'phone', 'is_active')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	list_display = ('title', 'owner', 'date', 'status', 'guests')
	list_filter = ('status', 'event_type')
	search_fields = ('title', 'owner__username')
