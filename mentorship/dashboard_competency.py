"""Two distinct-health-worker competency indicators; no database writes."""
from django.db.models import Q


def build_competency_data(details_qs):
    # Every queryset already has both authorization and dashboard filters.
    records = details_qs.exclude(menteename_id__isnull=True).order_by()
    competent = set(records.filter(Q(pc=True) | Q(mc=True)).values_list('menteename_id', flat=True))
    learners = set(records.filter(ls=True).values_list('menteename_id', flat=True))
    achieved_learners = competent & learners
    return {'competency_kpis': {
        'competent_mentees': len(competent),
        'learning_mentees': len(learners),
        'competent_learning_mentees': len(achieved_learners),
        'competent_percent': round(100 * len(achieved_learners) / len(learners), 1) if learners else None,
    }}
