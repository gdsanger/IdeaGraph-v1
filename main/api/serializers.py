"""
Serializers for Actions API
"""
from rest_framework import serializers
from main.models import Item, Task, Milestone, ItemFile, TaskFile, Tag, User


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class FileRefSerializer(serializers.ModelSerializer):
    """Serializer for file references (ItemFile/TaskFile)"""
    
    file_id = serializers.SerializerMethodField()
    
    class Meta:
        model = ItemFile
        fields = ['id', 'filename', 'file_id', 'file_size', 'content_type', 'created_at']
    
    def get_file_id(self, obj):
        """Return the file ID for Weaviate lookup"""
        # For ItemFile, use sharepoint_file_id or the id itself
        if hasattr(obj, 'sharepoint_file_id') and obj.sharepoint_file_id:
            return obj.sharepoint_file_id
        return str(obj.id)


class TaskFileRefSerializer(FileRefSerializer):
    """Serializer for TaskFile references"""
    
    class Meta:
        model = TaskFile
        fields = ['id', 'filename', 'file_id', 'file_size', 'content_type', 'created_at']


class ItemSerializer(serializers.ModelSerializer):
    """Serializer for Item model"""
    
    tags = TagSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Item
        fields = [
            'id', 'title', 'description', 'status', 'github_repo',
            'section_name', 'tags', 'created_by', 'created_at', 'updated_at'
        ]


class ItemDetailSerializer(ItemSerializer):
    """Detailed serializer for Item model"""
    
    file_count = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()
    milestone_count = serializers.SerializerMethodField()
    
    class Meta(ItemSerializer.Meta):
        fields = ItemSerializer.Meta.fields + ['file_count', 'task_count', 'milestone_count']
    
    def get_file_count(self, obj):
        return obj.files.count()
    
    def get_task_count(self, obj):
        return obj.tasks.count()
    
    def get_milestone_count(self, obj):
        return obj.milestones.count()


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model"""
    
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    item_id = serializers.UUIDField(required=False, allow_null=True)
    milestone_id = serializers.UUIDField(required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'type',
            'item_id', 'milestone_id', 'tags', 'tag_ids',
            'assigned_to', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def create(self, validated_data):
        """Create task with tags"""
        tag_ids = validated_data.pop('tag_ids', [])
        task = Task.objects.create(**validated_data)
        
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            task.tags.set(tags)
        
        return task
    
    def update(self, instance, validated_data):
        """Update task with tags"""
        tag_ids = validated_data.pop('tag_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if tag_ids is not None:
            tags = Tag.objects.filter(id__in=tag_ids)
            instance.tags.set(tags)
        
        return instance


class MilestoneSerializer(serializers.ModelSerializer):
    """Serializer for Milestone model"""
    
    item_id = serializers.UUIDField(source='item.id', read_only=True)
    item_title = serializers.CharField(source='item.title', read_only=True)
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Milestone
        fields = [
            'id', 'name', 'description', 'due_date', 'status',
            'item_id', 'item_title', 'task_count', 'summary',
            'created_at', 'updated_at'
        ]
    
    def get_task_count(self, obj):
        return obj.tasks.count()


class ContextHitSerializer(serializers.Serializer):
    """Serializer for semantic search results"""
    
    id = serializers.UUIDField()
    type = serializers.CharField()
    title = serializers.CharField()
    excerpt = serializers.CharField()
    score = serializers.FloatField()
    metadata = serializers.DictField()
    
    class Meta:
        fields = ['id', 'type', 'title', 'excerpt', 'score', 'metadata']


class FileContentSerializer(serializers.Serializer):
    """Serializer for file content from Weaviate"""
    
    file_id = serializers.CharField()
    filename = serializers.CharField()
    content_type = serializers.CharField()
    content = serializers.CharField()
    size = serializers.IntegerField()
    excerpt = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    
    class Meta:
        fields = ['file_id', 'filename', 'content_type', 'content', 'size', 'excerpt', 'created_at']
