from .models import ReviewMerge

def archived_ids():
    return ReviewMerge.objects.filter(active=True).values_list('source_id', flat=True)

def current_mentees(queryset):
    return queryset.exclude(pk__in=archived_ids())
