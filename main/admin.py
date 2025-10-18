from django.contrib import admin
from .models import Tag, User, Settings, Section


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'created_at', 'updated_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_active', 'created_at', 'last_login']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['username', 'email']
    readonly_fields = ['id', 'password_hash', 'created_at', 'last_login']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'username', 'email', 'role', 'is_active')
        }),
        ('Security', {
            'fields': ('password_hash',)
        }),
        ('Additional Information', {
            'fields': ('ai_classification',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_login')
        }),
    )


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'updated_at']
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
