from django.contrib import admin
from .models import Tag, User, Settings, Section, Item, Task, Relation, Milestone, MilestoneContextObject


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


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'created_by', 'github_repo', 'ai_enhanced', 'created_at', 'updated_at']
    list_filter = ['section', 'ai_enhanced', 'ai_tags_generated', 'similarity_checked', 'created_at']
    search_fields = ['title', 'description', 'github_repo']
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['tags']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'description', 'section')
        }),
        ('GitHub Integration', {
            'fields': ('github_repo',)
        }),
        ('Categorization', {
            'fields': ('tags',)
        }),
        ('AI Features', {
            'fields': ('ai_enhanced', 'ai_tags_generated', 'similarity_checked')
        }),
        ('Meta Information', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'due_date', 'item', 'created_at', 'updated_at']
    list_filter = ['status', 'due_date', 'created_at']
    search_fields = ['name', 'description', 'item__title']
    readonly_fields = ['id', 'weaviate_id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'status', 'due_date')
        }),
        ('AI Features', {
            'fields': ('summary', 'weaviate_id')
        }),
        ('Relations', {
            'fields': ('item',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(MilestoneContextObject)
class MilestoneContextObjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'milestone', 'analyzed', 'uploaded_by', 'created_at']
    list_filter = ['type', 'analyzed', 'created_at']
    search_fields = ['title', 'content', 'summary', 'milestone__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'type', 'title', 'content')
        }),
        ('Source Information', {
            'fields': ('source_id', 'url', 'uploaded_by')
        }),
        ('AI Analysis', {
            'fields': ('analyzed', 'summary', 'tags', 'derived_tasks')
        }),
        ('Relations', {
            'fields': ('milestone',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'item', 'milestone', 'assigned_to', 'github_issue_id', 'ai_generated', 'created_at', 'updated_at']
    list_filter = ['status', 'ai_enhanced', 'ai_generated', 'created_at']
    search_fields = ['title', 'description', 'github_issue_url']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at', 'github_synced_at']
    filter_horizontal = ['tags']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'description', 'status')
        }),
        ('Relations', {
            'fields': ('item', 'milestone', 'assigned_to', 'created_by')
        }),
        ('GitHub Integration', {
            'fields': ('github_issue_id', 'github_issue_url', 'github_synced_at')
        }),
        ('Categorization', {
            'fields': ('tags',)
        }),
        ('AI Features', {
            'fields': ('ai_enhanced', 'ai_generated')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )


@admin.register(Relation)
class RelationAdmin(admin.ModelAdmin):
    list_display = ['source', 'target', 'type', 'created_at', 'updated_at']
    list_filter = ['type', 'created_at']
    search_fields = ['source__title', 'target__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Relationship Information', {
            'fields': ('id', 'source', 'target', 'type')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
