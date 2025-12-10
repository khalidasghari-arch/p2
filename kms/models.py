from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.search import SearchVector
from django.contrib.postgres.indexes import GinIndex
from taggit.managers import TaggableManager
from datetime import datetime
# --------------------------------------------------------
# Proxy model to show Taggit Tags inside the KMS app
# --------------------------------------------------------
from taggit.models import Tag as BaseTag

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class KnowledgeItem(models.Model):
    title       = models.CharField(max_length=255)
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="knowledge_items")
    content     = models.TextField()

    # Full-text search vector (Postgres)
    search_vector = SearchVectorField(null=True, blank=True)

    tags        = TaggableManager(blank=True)

    author      = models.CharField(max_length=120, blank=True, null=True)
    source      = models.CharField(max_length=250, blank=True, null=True)

    created_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_knowledge_items"
    )
    updated_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="updated_knowledge_items"
    )

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # OPTIONAL: simple linkage to mentorship system
    # adapt this field to match your existing models/table
    mentorship_topic = models.CharField(max_length=200, blank=True, null=True)
    # OR: ForeignKey to your MentorshipVisit model if in another app
    # mentorship_visit = models.ForeignKey("mentorship.MentorshipVisit", ...)

    # in models.py (add within KnowledgeItem class)
    def save(self, *args, **kwargs):
        # First save (to ensure PK exists)
        super_save = super(KnowledgeItem, self).save

        # call super.save() first if this is new (no id yet)
        if self.pk is None:
            super_save(*args, **kwargs)
        # update search_vector
        from django.db.models import F
        from django.contrib.postgres.search import SearchVector

        type(self).objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector("title", weight="A") +
                SearchVector("content", weight="B") +
                SearchVector("source", weight="C")
            )
        )
        # refresh from db so instance has updated search_vector
        super_save(update_fields=["search_vector"])

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["search_vector"]),
        ]
        permissions = [
            ("can_publish_knowledge", "Can publish knowledge items"),
        ]

    def __str__(self):
        return self.title


class KnowledgeFile(models.Model):
    """Multiple attachments per knowledge item."""
    knowledge_item = models.ForeignKey(
        KnowledgeItem, on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(upload_to="kms_files/")
    description = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.knowledge_item.title} – {self.file.name}"


class KnowledgeItemVersion(models.Model):
    """Keeps history of changes."""
    knowledge_item = models.ForeignKey(
        KnowledgeItem, on_delete=models.CASCADE, related_name="versions"
    )
    title       = models.CharField(max_length=255)
    content     = models.TextField()
    author      = models.CharField(max_length=120, blank=True, null=True)
    source      = models.CharField(max_length=250, blank=True, null=True)
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField()
    updated_at  = models.DateTimeField()
    changed_at  = models.DateTimeField(default=datetime.utcnow)
    changed_by  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Version of {self.knowledge_item.title} at {self.changed_at}"


class Comment(models.Model):
    knowledge_item = models.ForeignKey(
        KnowledgeItem, on_delete=models.CASCADE, related_name="comments"
    )
    author      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    text        = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.knowledge_item}"


class KMSTag(BaseTag):
    """
    Proxy so Tag appears under the KMS app in admin.
    This does NOT create a new database table.
    """
    class Meta:
        proxy = True
        app_label = "kms"
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
