from django.contrib import admin
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Count
from django.utils.timezone import now, timedelta
from taggit.models import Tag as TaggitTag
from .models import KMSTag
from django.contrib import admin

from .models import (
    Category,
    KnowledgeItem,
    KnowledgeFile,
    KnowledgeItemVersion,
    Comment,
)

class KnowledgeFileInline(admin.TabularInline):
    model = KnowledgeFile
    extra = 1


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("author", "text", "created_at", "is_resolved")
    readonly_fields = ("author", "created_at")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "description")

@admin.register(KnowledgeItemVersion)
class KnowledgeItemVersionAdmin(admin.ModelAdmin):
    list_display = ("knowledge_item", "changed_at", "changed_by")
    readonly_fields = (
        "knowledge_item",
        "title",
        "content",
        "author",
        "source",
        "category",
        "created_at",
        "updated_at",
        "changed_at",
        "changed_by",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # make versions read-only in admin
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("knowledge_item", "author", "created_at", "is_resolved")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("knowledge_item__title", "text", "author__username")


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "created_at", "updated_at")
    list_filter = ("category", "tags", "created_at")
    search_fields = ("title", "content", "source", "mentorship_topic")

    inlines = [KnowledgeFileInline, CommentInline]

    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    fields = (
        "title",
        "category",
        "content",
        "tags",
        "author",
        "source",
        "mentorship_topic",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj._updated_by = request.user  # used by signals for versioning
        super().save_model(request, obj, form, change)

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        if search_term:
            try:
                query = SearchQuery(search_term)
                qs_fulltext = (
                    queryset.annotate(
                        rank=SearchRank(F("search_vector"), query)
                    )
                    .filter(search_vector=query)
                    .order_by("-rank")
                )
                return qs_fulltext, use_distinct
            except Exception:
                # fallback to default search if full-text fails
                pass
        return queryset, use_distinct
class KnowledgeItemAdmin(admin.ModelAdmin):
    # ...
    def has_view_permission(self, request, obj=None):
        # Example: only staff in a KMS group can view
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name__in=["KMS Editors", "KMS Viewers"]).exists()

class KmsDashboardAdmin(admin.ModelAdmin):
    change_list_template = "admin/kms_dashboard.html"

    def changelist_view(self, request, extra_context=None):
        # simple stats
        per_category = (
            Category.objects.annotate(count=Count("knowledge_items"))
            .values("name", "count")
            .order_by("-count")
        )
        recent_items = KnowledgeItem.objects.filter(
            created_at__gte=now() - timedelta(days=30)
        ).count()
        most_commented = (
            KnowledgeItem.objects.annotate(comment_count=Count("comments"))
            .order_by("-comment_count")[:10]
        )

        context = {
            "per_category": per_category,
            "recent_items": recent_items,
            "most_commented": most_commented,
            **(extra_context or {}),
        }
        return TemplateResponse(request, "admin/kms_dashboard.html", context)

# register a fake model only for dashboard, OR just use CategoryAdmin override
# easiest hack: add a dummy model:
from django.db import models as dj_models

class KmsDashboardDummy(dj_models.Model):
    class Meta:
        managed = False
        verbose_name = "KMS Dashboard"
        verbose_name_plural = "KMS Dashboard"

admin.site.register(KmsDashboardDummy, KmsDashboardAdmin)

try:
    admin.site.unregister(TaggitTag)
except admin.sites.NotRegistered:
    pass

@admin.register(KMSTag)
class KMSTagAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name",)

from taggit.models import Tag as TaggitTag  # original taggit Tag

from .models import (
    Category,
    KnowledgeItem,
    KnowledgeFile,
    KnowledgeItemVersion,
    Comment,
    KMSTag,     # ✅ our proxy model from models.py
)