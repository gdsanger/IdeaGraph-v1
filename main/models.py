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
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    password_hash = models.CharField(max_length=128)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    ai_classification = models.CharField(max_length=255, blank=True, default='')
    
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
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_items')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # AI-related fields
    ai_enhanced = models.BooleanField(default=False)
    ai_tags_generated = models.BooleanField(default=False)
    similarity_checked = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
    
    def __str__(self):
        return self.title


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


class Task(models.Model):
    """Task model for managing action items derived from Ideas"""
    
    STATUS_CHOICES = [
        ('new', 'Neu'),
        ('working', 'Working'),
        ('review', 'Review'),
        ('ready', 'Ready'),
        ('done', 'Erledigt'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')  # Markdown content
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Relations
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tasks')
    
    # GitHub Integration
    github_issue_id = models.IntegerField(null=True, blank=True)
    github_issue_url = models.URLField(max_length=500, blank=True, default='')
    github_synced_at = models.DateTimeField(null=True, blank=True)
    
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
