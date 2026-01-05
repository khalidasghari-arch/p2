# km_dashboard/admin.py
from django.contrib import admin
from .models import KMDocument, KMRecommendation
from django.utils import timezone

@admin.register(KMDocument)
class KMDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "doc_type", "theme", "year", "month", "province", "facility", "created_by", "created_at", "updated_by", "updated_at")
    readonly_fields = ('created_by', 'created_at', 'updated_by', 'updated_at')
    list_filter = ("doc_type", "theme", "year", "province")
    search_fields = ("title", "notes")

    def save_model(self, request, obj, form, change):
        # On create
        if not obj.pk:
            obj.created_by = request.user
            obj.created_at = timezone.now()
        # On update
        else:
            obj.updated_by = request.user
            obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(KMRecommendation)
class KMRecommendationAdmin(admin.ModelAdmin):
    list_display = ("theme", "year", "month", "province", "facility", "status", "due_date", "implemented_on", "created_by", "created_at", "updated_by", "updated_at")
    readonly_fields = ('created_by', 'created_at', 'updated_by', 'updated_at')
    list_filter = ("theme", "status", "year", "province")
    search_fields = ("recommendation", "evidence_notes", "responsible_person")

    def save_model(self, request, obj, form, change):
        # On create
        if not obj.pk:
            obj.created_by = request.user
            obj.created_at = timezone.now()
        # On update
        else:
            obj.updated_by = request.user
            obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)
