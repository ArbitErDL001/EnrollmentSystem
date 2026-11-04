from django.contrib import admin

from .models import ClassOffering, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'building', 'capacity', 'is_active')
    list_filter = ('is_active', 'building')


@admin.register(ClassOffering)
class ClassOfferingAdmin(admin.ModelAdmin):
    list_display = ('curriculum_entry', 'section', 'term', 'meeting_days', 'room', 'instructor', 'is_active')
    list_filter = ('term', 'is_active', 'curriculum_entry__program')
    search_fields = ('section', 'curriculum_entry__subject__code', 'instructor__username')
