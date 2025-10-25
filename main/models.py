import uuid
import random
import bcrypt
import secrets
from django.db import models
from django.utils import timezone


class User(models.Model):
    """User model for authentication and authorization"""
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('developer', 'Developer'),
        ('user', 'User'),
        ('viewer', 'Viewer'),
    ]
    
    AUTH_TYPE_CHOICES = [
        ('local', 'Local Authentication'),
        ('msauth', 'Microsoft Authentication'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    password_hash = models.CharField(max_length=128, blank=True, default='')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    is_active = models.BooleanField(default=True)
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    ai_classification = models.CharField(max_length=255, blank=True, default='')
    
    # Microsoft SSO fields
    auth_type = models.CharField(max_length=20, choices=AUTH_TYPE_CHOICES, default='local')
    ms_user_id = models.CharField(max_length=255, blank=True, default='', help_text='Microsoft User ID (OID)')
    avatar_url = models.URLField(max_length=500, blank=True, default='', help_text='URL to user avatar image')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.username
    
    def set_password(self, raw_password):
        """Hash and set the user's password using bcrypt"""
        password_bytes = raw_password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        self.password_hash = hashed.decode('utf-8')
    
    def check_password(self, raw_password):
        """Verify a password against the stored hash"""
        password_bytes = raw_password.encode('utf-8')
        hashed_bytes = self.password_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    
    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])


class PasswordResetToken(models.Model):
    """Token model for password reset functionality"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
    
    def __str__(self):
        return f"Reset token for {self.user.username}"
    
    def is_valid(self):
        """Check if token is still valid"""
        if self.used:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True
    
    def mark_as_used(self):
        """Mark token as used"""
        self.used = True
        self.save(update_fields=['used'])
    
    @classmethod
    def generate_token(cls, user):
        """Generate a new password reset token for a user"""
        # Invalidate all existing tokens for this user
        cls.objects.filter(user=user, used=False).update(used=True)
        
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        
        # Token expires in 30 minutes
        expires_at = timezone.now() + timezone.timedelta(minutes=30)
        
        # Create and return new token
        reset_token = cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        return reset_token


class Tag(models.Model):
    """Tag model for categorizing and labeling items"""
    
    # Color palette for tag colors
    COLOR_PALETTE = [
        '#ef4444',  # Red
        '#f97316',  # Orange
        '#f59e0b',  # Amber
        '#eab308',  # Yellow
        '#84cc16',  # Lime
        '#22c55e',  # Green
        '#10b981',  # Emerald
        '#14b8a6',  # Teal
        '#06b6d4',  # Cyan
        '#0ea5e9',  # Sky
        '#3b82f6',  # Blue
        '#6366f1',  # Indigo
        '#8b5cf6',  # Violet
        '#a855f7',  # Purple
        '#d946ef',  # Fuchsia
        '#ec4899',  # Pink
        '#f43f5e',  # Rose
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')  # Tag description for semantic search
    color = models.CharField(max_length=7, default='#3b82f6')  # Hex color code
    usage_count = models.IntegerField(default=0)  # Count of items/tasks using this tag
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Assign a random color from the palette if no color is set
        if not self.color or self.color == '#3b82f6':
            self.color = random.choice(self.COLOR_PALETTE)
        super().save(*args, **kwargs)
    
    def calculate_usage_count(self):
        """Calculate and update the usage count of this tag"""
        count = self.items.count() + self.tasks.count()
        self.usage_count = count
        self.save(update_fields=['usage_count'])
        return count
class Client(models.Model):
    """Client model for managing customers/clients"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        
    def __str__(self):
        return self.name


class Section(models.Model):
    """Section model for categorizing items by their fundamental type
    
    Sections classify items into domains such as:
    - Software projects
    - DIY/Home improvement items
    - Problems
    - Visions
    - Action items
    etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name


class Item(models.Model):
    """Item model for managing ideas and concepts"""
    
    STATUS_CHOICES = [
        ('new', 'Neu'),
        ('spec_review', 'Spezifikation Review'),
        ('working', 'Working'),
        ('ready', 'Ready'),
        ('done', 'Erledigt'),
        ('rejected', 'Verworfen'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')  # Markdown content
    github_repo = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    tags = models.ManyToManyField(Tag, blank=True, related_name='items')
    clients = models.ManyToManyField('Client', blank=True, related_name='items')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_items')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Hierarchical fields for parent-child relationships
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    is_template = models.BooleanField(default=False, help_text='Kennzeichnet, ob das Item als Vorlage dient')
    inherit_context = models.BooleanField(default=False, help_text='Steuert, ob Beschreibung, Tags, Milestones vom Parent geerbt werden')
    
    # AI-related fields
    ai_enhanced = models.BooleanField(default=False)
    ai_tags_generated = models.BooleanField(default=False)
    similarity_checked = models.BooleanField(default=False)
    
    # Microsoft Teams Integration
    channel_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Teams Channel ID',
        help_text='Channel ID aus dem Teams Workspace'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
    
    def __str__(self):
        return self.title
    
    def get_all_children(self):
        """Get all child items recursively"""
        children = list(self.children.all())
        for child in list(children):
            children.extend(child.get_all_children())
        return children
    
    def get_all_parents(self):
        """Get all parent items up to the root"""
        parents = []
        current = self.parent
        while current:
            parents.append(current)
            current = current.parent
        return parents
    
    def get_inherited_context(self):
        """Get combined context from parent if inheritance is enabled"""
        if not self.inherit_context or not self.parent:
            return {
                'description': self.description,
                'tags': list(self.tags.all()),
                'has_parent': False
            }
        
        # Combine parent and own context
        parent_description = self.parent.description or ''
        own_description = self.description or ''
        
        combined_description = f"{parent_description}\n\n{own_description}".strip()
        
        # Combine tags (parent + own, deduplicated)
        parent_tags = set(self.parent.tags.all())
        own_tags = set(self.tags.all())
        combined_tags = list(parent_tags | own_tags)
        
        return {
            'description': combined_description,
            'tags': combined_tags,
            'has_parent': True,
            'parent_id': str(self.parent.id),
            'parent_title': self.parent.title
        }


class ItemFile(models.Model):
    """ItemFile model for managing file uploads associated with items"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='files')
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()  # Size in bytes
    sharepoint_file_id = models.CharField(max_length=255, blank=True, default='')
    sharepoint_url = models.URLField(max_length=1000, blank=True, default='')
    content_type = models.CharField(max_length=100, blank=True, default='')
    weaviate_synced = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_files')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Item File'
        verbose_name_plural = 'Item Files'
    
    def __str__(self):
        return f"{self.filename} ({self.item.title})"


class TaskFile(models.Model):
    """TaskFile model for managing file uploads associated with tasks"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='files')
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()  # Size in bytes
    file_path = models.CharField(max_length=500, blank=True, default='', help_text='Local file path')
    sharepoint_file_id = models.CharField(max_length=255, blank=True, default='')
    sharepoint_url = models.URLField(max_length=1000, blank=True, default='')
    content_type = models.CharField(max_length=100, blank=True, default='')
    weaviate_synced = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_task_files')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task File'
        verbose_name_plural = 'Task Files'
    
    def __str__(self):
        return f"{self.filename} ({self.task.title})"


class MilestoneFile(models.Model):
    """MilestoneFile model for managing file uploads associated with milestones (e.g., generated changelogs)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    milestone = models.ForeignKey('Milestone', on_delete=models.CASCADE, related_name='files')
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()  # Size in bytes
    file_path = models.CharField(max_length=500, blank=True, default='', help_text='Local file path')
    sharepoint_file_id = models.CharField(max_length=255, blank=True, default='')
    sharepoint_url = models.URLField(max_length=1000, blank=True, default='')
    content_type = models.CharField(max_length=100, blank=True, default='')
    weaviate_synced = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_milestone_files')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Milestone File'
        verbose_name_plural = 'Milestone Files'
    
    def __str__(self):
        return f"{self.filename} ({self.milestone.name})"


class Relation(models.Model):
    """Relation model for managing relationships between items"""
    
    TYPE_CHOICES = [
        ('dependency', 'Abhängigkeit'),
        ('similar', 'Ähnlich'),
        ('synergy', 'Synergieeffekt'),
        ('parent', 'Parent'),
        ('child', 'Child'),
        ('other', 'Sonstige'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='relations_from')
    target = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='relations_to')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Relation'
        verbose_name_plural = 'Relations'
        unique_together = [['source', 'target', 'type']]
    
    def __str__(self):
        return f"{self.source.title} -> {self.target.title} ({self.get_type_display()})"


class Milestone(models.Model):
    """Milestone model for tracking important deadlines within items"""
    
    STATUS_CHOICES = [
        ('planned', 'Geplant'),
        ('in_progress', 'In Arbeit'),
        ('completed', 'Abgeschlossen'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='', help_text='Manuelle oder KI-basierte Beschreibung')
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='milestones')
    
    # AI-generated summary from all context objects
    summary = models.TextField(blank=True, default='', help_text='KI-Zusammenfassung über alle Kontextobjekte')
    
    # ChangeLog field with markdown content
    changelog = models.TextField(blank=True, default='', help_text='Markdown ChangeLog für den Milestone')
    
    # Weaviate integration
    weaviate_id = models.UUIDField(null=True, blank=True, help_text='Verweis auf das Embedding im Vektorspeicher')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['due_date']
        verbose_name = 'Milestone'
        verbose_name_plural = 'Milestones'
    
    def __str__(self):
        return self.name


class MilestoneContextObject(models.Model):
    """Context object associated with a milestone (file, email, transcript, note)"""
    
    TYPE_CHOICES = [
        ('file', 'Datei'),
        ('email', 'E-Mail'),
        ('transcript', 'Transkript'),
        ('note', 'Notiz'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='context_objects')
    
    # Context object metadata
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    source_id = models.CharField(max_length=255, blank=True, default='', help_text='GUID oder Pfad')
    url = models.URLField(max_length=1000, blank=True, default='', help_text='URL zum Dokument')
    content = models.TextField(blank=True, default='', help_text='Textinhalt des Objekts')
    
    # AI-generated metadata
    summary = models.TextField(blank=True, default='', help_text='KI-generierte Zusammenfassung')
    tags = models.JSONField(default=list, blank=True, help_text='Automatisch extrahierte Tags')
    derived_tasks = models.JSONField(default=list, blank=True, help_text='Abgeleitete Aufgaben (JSON)')
    
    # Processing status
    analyzed = models.BooleanField(default=False, help_text='Wurde bereits von KI analysiert')
    
    # User who added the context
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_context_objects')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Milestone Context Object'
        verbose_name_plural = 'Milestone Context Objects'
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.title}"


class MilestoneSummaryVersion(models.Model):
    """Version history for milestone summary optimizations"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='summary_versions')
    summary_text = models.TextField(help_text='Snapshot of the summary text')
    version_number = models.IntegerField(default=1, help_text='Sequential version number')
    
    # Optimization metadata
    optimized_by_ai = models.BooleanField(default=False, help_text='Whether this version was AI-optimized')
    agent_name = models.CharField(max_length=255, blank=True, default='', help_text='Name of the AI agent used')
    model_name = models.CharField(max_length=255, blank=True, default='', help_text='AI model used for optimization')
    
    # User tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='milestone_summary_versions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-version_number']
        verbose_name = 'Milestone Summary Version'
        verbose_name_plural = 'Milestone Summary Versions'
        unique_together = ['milestone', 'version_number']
    
    def __str__(self):
        return f"Version {self.version_number} - {self.milestone.name}"


class Task(models.Model):
    """Task model for managing action items derived from Ideas"""
    
    STATUS_CHOICES = [
        ('new', 'Neu'),
        ('working', 'Working'),
        ('review', 'Review'),
        ('ready', 'Ready'),
        ('done', 'Erledigt'),
    ]
    
    TYPE_CHOICES = [
        ('task', 'Task'),
        ('feature', 'Feature'),
        ('bug', 'Bug'),
        ('ticket', 'Ticket'),
        ('maintenance', 'Maintenance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')  # Markdown content
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='task', help_text='Task type classification')
    
    # Relations
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks', help_text='Direct section assignment for tickets')
    milestone = models.ForeignKey(Milestone, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    tags = models.ManyToManyField(Tag, blank=True, related_name='tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tasks')
    requester = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_tasks')
    
    # External Integration (Zammad, GitHub, etc.)
    external_id = models.CharField(max_length=255, blank=True, default='', help_text='External system ID (Zammad ticket ID, etc.)')
    external_url = models.URLField(max_length=500, blank=True, default='', help_text='URL to external system resource')
    
    # GitHub Integration (kept for backward compatibility)
    github_issue_id = models.IntegerField(null=True, blank=True)
    github_issue_url = models.URLField(max_length=500, blank=True, default='')
    github_synced_at = models.DateTimeField(null=True, blank=True)
    
    # Microsoft Teams Integration
    message_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Teams Message ID',
        help_text='ID of the Teams channel message that triggered this task'
    )
    
    # AI-related fields
    ai_enhanced = models.BooleanField(default=False)
    ai_generated = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        indexes = [
            models.Index(fields=['message_id'], name='task_message_id_idx'),
        ]
    
    def __str__(self):
        return self.title
    
    def mark_as_done(self):
        """Mark task as completed"""
        self.status = 'done'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])


class Settings(models.Model):
    """
    Settings model to store system configuration and API keys.
    Only accessible to Admin users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # OpenAI API Configuration
    openai_api_enabled = models.BooleanField(
        default=False,
        verbose_name='Enable OpenAI API',
        help_text='Enable OpenAI API integration'
    )
    openai_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='OPENAI_API_KEY'
    )
    openai_org_id = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='OPENAI_ORG_ID',
        help_text='OpenAI Organisation ID'
    )
    openai_default_model = models.CharField(
        max_length=100,
        blank=True,
        default='gpt-4',
        verbose_name='Default OpenAI Model',
        help_text='Default model for OpenAI API (e.g., gpt-4, gpt-3.5-turbo)'
    )
    openai_api_base_url = models.CharField(
        max_length=255,
        blank=True,
        default='https://api.openai.com/v1',
        verbose_name='OpenAI API Base URL',
        help_text='OpenAI API base URL'
    )
    openai_api_timeout = models.IntegerField(
        default=30,
        verbose_name='OpenAI API Timeout',
        help_text='Timeout for OpenAI API requests in seconds'
    )
    openai_max_tokens = models.IntegerField(
        default=10000,
        verbose_name='OpenAI Max Tokens per Request',
        help_text='Maximum number of tokens to send per OpenAI API request (content will be chunked if larger)'
    )
    
    # Graph API Credentials
    client_id = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CLIENT_ID',
        help_text='GraphAPI Client ID'
    )
    client_secret = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CLIENT_SECRET',
        help_text='GraphAPI Client Secret'
    )
    tenant_id = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='TENANT_ID',
        help_text='GraphAPI Tenant'
    )
    
    # GitHub Credentials
    github_token = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='GITHUB_TOKEN',
        help_text='GitHub PAT Key'
    )
    
    # GitHub API Settings
    github_api_enabled = models.BooleanField(
        default=False,
        verbose_name='Enable GitHub API',
        help_text='Enable GitHub API integration'
    )
    github_api_base_url = models.CharField(
        max_length=255,
        blank=True,
        default='https://api.github.com',
        verbose_name='GitHub API Base URL',
        help_text='GitHub API base URL'
    )
    github_default_owner = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Default GitHub Owner',
        help_text='Default owner for GitHub operations'
    )
    github_default_repo = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Default GitHub Repository',
        help_text='Default repository for GitHub operations'
    )
    github_copilot_username = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='GitHub Copilot Username',
        help_text='GitHub username to assign issues to (e.g., copilot)'
    )
    
    # ChromaDB Configuration
    chroma_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CHROMA_API_KEY',
        help_text='ChromaDB Api Key (Cloud)'
    )
    chroma_database = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CHROMA_DATABASE',
        help_text='ChromaDB Api Key (DATABASE)'
    )
    chroma_tenant = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CHROMA_TENANT',
        help_text='ChromaDB Api Key (TENANT)'
    )
    
    # KiGate Configuration
    kigate_api_enabled = models.BooleanField(
        default=False,
        verbose_name='Enable KiGate API',
        help_text='Enable KiGate API integration'
    )
    kigate_api_base_url = models.CharField(
        max_length=255,
        blank=True,
        default='http://localhost:8000',
        verbose_name='KiGate API Base URL',
        help_text='KiGate API base URL'
    )
    kigate_api_token = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='KiGate API Token',
        help_text='KiGate API authentication token (client_id:client_secret)'
    )
    kigate_api_timeout = models.IntegerField(
        default=30,
        verbose_name='KiGate API Timeout',
        help_text='Timeout for KiGate API requests in seconds'
    )
    kigate_max_tokens = models.IntegerField(
        default=10000,
        verbose_name='KiGate Max Tokens per Request',
        help_text='Maximum number of tokens to send per KiGate API request (content will be chunked if larger)'
    )
    
    # Weaviate Configuration
    weaviate_cloud_enabled = models.BooleanField(
        default=False,
        verbose_name='Cloud',
        help_text='Enable Weaviate Cloud (if disabled, local configuration is used)'
    )
    weaviate_url = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='WEAVIATE_URL',
        help_text='Weaviate Cloud URL'
    )
    weaviate_api_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='WEAVIATE_API_KEY',
        help_text='Weaviate Cloud API Key'
    )
    
    # Additional Settings
    max_tags_per_idea = models.IntegerField(
        default=5,
        verbose_name='MAX_TAGS_PER_IDEA',
        help_text='Anzahl der Tags die bei Items durch die KI gesucht werden sollen'
    )
    
    # Graph API Settings
    graph_api_enabled = models.BooleanField(
        default=False,
        verbose_name='Enable Graph API',
        help_text='Enable Microsoft Graph API integration'
    )
    graph_api_base_url = models.CharField(
        max_length=255,
        blank=True,
        default='https://graph.microsoft.com/v1.0',
        verbose_name='Graph API Base URL',
        help_text='Microsoft Graph API base URL'
    )
    graph_api_scopes = models.TextField(
        blank=True,
        default='https://graph.microsoft.com/.default',
        verbose_name='Graph API Scopes',
        help_text='Comma-separated list of Graph API scopes'
    )
    sharepoint_site_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='SharePoint Site ID',
        help_text='SharePoint site ID for document operations'
    )
    default_mail_sender = models.EmailField(
        max_length=254,
        blank=True,
        default='',
        verbose_name='Default Mail Sender',
        help_text='Default sender email for Graph API mail operations'
    )
    
    # Microsoft SSO Authentication Settings
    ms_sso_enabled = models.BooleanField(
        default=False,
        verbose_name='Enable Microsoft SSO',
        help_text='Enable Microsoft Identity SSO authentication'
    )
    ms_sso_client_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='MS SSO Client ID',
        help_text='Microsoft Azure AD Application (Client) ID for SSO'
    )
    ms_sso_tenant_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='MS SSO Tenant ID',
        help_text='Microsoft Azure AD Tenant ID for SSO'
    )
    ms_sso_client_secret = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='MS SSO Client Secret',
        help_text='Microsoft Azure AD Client Secret for SSO (optional for some flows)'
    )
    
    # Zammad Configuration
    zammad_enabled = models.BooleanField(
        default=False,
        verbose_name='Enable Zammad Integration',
        help_text='Enable Zammad ticket synchronization'
    )
    zammad_api_url = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Zammad API URL',
        help_text='Base URL of the Zammad instance'
    )
    zammad_api_token = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Zammad API Token',
        help_text='API token for authentication'
    )
    zammad_groups = models.TextField(
        blank=True,
        default='',
        verbose_name='Zammad Groups',
        help_text='Comma-separated list of group names to monitor'
    )
    zammad_sync_interval = models.IntegerField(
        default=15,
        verbose_name='Zammad Sync Interval',
        help_text='Interval in minutes for periodic synchronization'
    )
    
    # Google PSE Configuration
    google_pse_enabled = models.BooleanField(
        default=False,
        verbose_name='Enable Google PSE',
        help_text='Enable Google Programmable Search Engine integration'
    )
    google_search_api_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Google Search API Key',
        help_text='Google Custom Search API Key'
    )
    google_search_cx = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Google Search CX',
        help_text='Google Custom Search Engine ID (CX)'
    )
    
    # Microsoft Teams Integration
    teams_enabled = models.BooleanField(
        default=False,
        verbose_name='Enable Teams Integration',
        help_text='Aktiviert/Deaktiviert die Teams-Integration'
    )
    teams_team_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Teams Team ID',
        help_text='ID des Teams (Workspace), das beobachtet wird'
    )
    team_welcome_post = models.TextField(
        blank=True,
        default='Willkommen im Channel für {{Item}}! Hier können Sie Nachrichten zu diesem Item senden und diskutieren.',
        verbose_name='Teams Welcome Post Template',
        help_text='Vorlage für einen Begrüßungspost. Verwenden Sie {{Item}} als Platzhalter für den Item-Titel.'
    )
    graph_poll_interval = models.IntegerField(
        default=60,
        verbose_name='Graph Poll Interval',
        help_text='Interval in seconds for polling Teams channels for new messages'
    )
    
    # Delegated Authentication for Teams (Device Code Flow)
    teams_use_delegated_auth = models.BooleanField(
        default=True,
        verbose_name='Use Delegated Auth for Teams',
        help_text='Use delegated user authentication (device code flow) for Teams channel posting. Required for posting messages.'
    )
    teams_delegated_user_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Delegated User ID',
        help_text='User ID (UPN or email) for delegated authentication'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Settings'
        verbose_name_plural = 'Settings'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Settings - {self.id}"


class LogEntry(models.Model):
    """Model to store parsed log entries from local logs and Sentry"""
    
    SOURCE_CHOICES = [
        ('local', 'Local Log'),
        ('sentry', 'Sentry API'),
    ]
    
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    logger_name = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField()
    timestamp = models.DateTimeField()
    
    # Additional context
    exception_type = models.CharField(max_length=255, blank=True, default='')
    exception_value = models.TextField(blank=True, default='')
    stack_trace = models.TextField(blank=True, default='')
    file_path = models.CharField(max_length=500, blank=True, default='')
    line_number = models.IntegerField(null=True, blank=True)
    
    # Sentry specific fields
    sentry_event_id = models.CharField(max_length=100, blank=True, default='', unique=True, null=True)
    sentry_issue_id = models.CharField(max_length=100, blank=True, default='')
    
    # Processing metadata
    analyzed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Log Entry'
        verbose_name_plural = 'Log Entries'
        indexes = [
            models.Index(fields=['-timestamp', 'level']),
            models.Index(fields=['analyzed', 'level']),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.logger_name} - {self.message[:50]}"


class ErrorAnalysis(models.Model):
    """Model to store AI analysis results for log entries"""
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('task_created', 'Task Created'),
        ('issue_created', 'GitHub Issue Created'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    log_entry = models.ForeignKey(LogEntry, on_delete=models.CASCADE, related_name='analyses')
    
    # AI Analysis results
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    is_actionable = models.BooleanField(default=False)
    summary = models.TextField()
    root_cause = models.TextField(blank=True, default='')
    recommended_action = models.TextField(blank=True, default='')
    
    # AI metadata
    ai_model = models.CharField(max_length=100, blank=True, default='')
    ai_confidence = models.FloatField(default=0.0)  # 0.0 to 1.0
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_analyses')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='error_analyses')
    github_issue_url = models.URLField(max_length=500, blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Error Analysis'
        verbose_name_plural = 'Error Analyses'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['severity', 'is_actionable']),
        ]
    
    def __str__(self):
        return f"{self.get_severity_display()} - {self.summary[:50]}"
    
    def approve_and_create_task(self, user):
        """Approve the analysis and create a task"""
        if self.status != 'pending':
            return None
        
        self.status = 'approved'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save()
        
        return None  # Task creation will be handled by the service
