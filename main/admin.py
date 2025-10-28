from django.contrib import admin
from .models import Tag, User, Settings, Section, Item, Task, Relation, Milestone, MilestoneContextObject, MilestoneSummaryVersion, ItemQuestionAnswer, Provider, ProviderModel


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'created_at', 'updated_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active', 'created_at', 'last_login']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['id', 'password_hash', 'created_at', 'last_login']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'username', 'first_name', 'last_name', 'email', 'role', 'is_active')
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


@admin.register(MilestoneSummaryVersion)
class MilestoneSummaryVersionAdmin(admin.ModelAdmin):
    list_display = ['milestone', 'version_number', 'optimized_by_ai', 'agent_name', 'created_by', 'created_at']
    list_filter = ['optimized_by_ai', 'agent_name', 'model_name', 'created_at']
    search_fields = ['milestone__name', 'summary_text']
    readonly_fields = ['id', 'created_at']
    fieldsets = (
        ('Version Information', {
            'fields': ('id', 'milestone', 'version_number')
        }),
        ('Content', {
            'fields': ('summary_text',)
        }),
        ('AI Metadata', {
            'fields': ('optimized_by_ai', 'agent_name', 'model_name')
        }),
        ('User Information', {
            'fields': ('created_by', 'created_at')
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


@admin.register(ItemQuestionAnswer)
class ItemQuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ['get_short_question', 'item', 'asked_by', 'relevance_score', 'saved_as_knowledge_object', 'created_at']
    list_filter = ['saved_as_knowledge_object', 'created_at']
    search_fields = ['question', 'answer', 'item__title']
    readonly_fields = ['id', 'sources', 'weaviate_uuid', 'created_at', 'updated_at']
    fieldsets = (
        ('Question & Answer', {
            'fields': ('id', 'item', 'question', 'answer')
        }),
        ('Sources & Relevance', {
            'fields': ('sources', 'relevance_score')
        }),
        ('Weaviate Sync', {
            'fields': ('saved_as_knowledge_object', 'weaviate_uuid')
        }),
        ('User Information', {
            'fields': ('asked_by', 'created_at', 'updated_at')
        }),
    )
    
    # Display configuration constants
    MAX_QUESTION_DISPLAY_LENGTH = 100
    
    def get_short_question(self, obj):
        """Return shortened question for list display"""
        if len(obj.question) > self.MAX_QUESTION_DISPLAY_LENGTH:
            return obj.question[:self.MAX_QUESTION_DISPLAY_LENGTH] + '...'
        return obj.question
    get_short_question.short_description = 'Question'


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider_type', 'is_active', 'created_at', 'updated_at']
    list_filter = ['provider_type', 'is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'provider_type', 'is_active')
        }),
        ('API Configuration', {
            'fields': ('api_key', 'api_base_url', 'api_timeout')
        }),
        ('Provider-specific Settings', {
            'fields': ('openai_org_id', 'extra_config')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ProviderModel)
class ProviderModelAdmin(admin.ModelAdmin):
    list_display = ['get_display_name', 'model_id', 'provider', 'is_active', 'last_synced_at']
    list_filter = ['provider', 'is_active', 'last_synced_at']
    search_fields = ['model_id', 'display_name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_synced_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'provider', 'model_id', 'display_name', 'is_active')
        }),
        ('Model Details', {
            'fields': ('description', 'capabilities', 'context_length')
        }),
        ('Metadata', {
            'fields': ('metadata',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_synced_at')
        }),
    )
    
    def get_display_name(self, obj):
        """Return display name or model_id"""
        return obj.display_name or obj.model_id
    get_display_name.short_description = 'Display Name'

