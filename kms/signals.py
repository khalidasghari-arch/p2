from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector

from .models import KnowledgeItem, KnowledgeItemVersion


@receiver(pre_save, sender=KnowledgeItem)
def create_version_before_change(sender, instance, **kwargs):
    if not instance.pk:
        return  # new item, no old version yet
    try:
        old = KnowledgeItem.objects.get(pk=instance.pk)
    except KnowledgeItem.DoesNotExist:
        return

    fields = ["title", "content", "author", "source", "category_id"]
    changed = any(getattr(old, f) != getattr(instance, f) for f in fields)
    if changed:
        KnowledgeItemVersion.objects.create(
            knowledge_item=old,
            title=old.title,
            content=old.content,
            author=old.author,
            source=old.source,
            category=old.category,
            created_at=old.created_at,
            updated_at=old.updated_at,
            # changed_by set in admin via instance._updated_by if available
            changed_by=getattr(instance, "_updated_by", None),
        )


@receiver(post_save, sender=KnowledgeItem)
def update_search_vector(sender, instance, **kwargs):
    KnowledgeItem.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector("title", weight="A")
            + SearchVector("content", weight="B")
            + SearchVector("source", weight="C")
        )
    )
