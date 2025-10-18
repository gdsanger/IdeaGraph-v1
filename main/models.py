import uuid
import random
from django.db import models


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
