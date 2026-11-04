from django.contrib import admin

from .models import CurriculumEntry, Program, Subject


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'units', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)


@admin.register(CurriculumEntry)
class CurriculumEntryAdmin(admin.ModelAdmin):
    list_display = ('program', 'year_level', 'subject')
    list_filter = ('program', 'year_level')
