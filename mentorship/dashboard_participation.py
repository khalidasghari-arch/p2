"""Profession breakdown and actual monthly mentor visits."""
from collections import defaultdict
from datetime import date
from django.db.models import Count, F, Q


def build_participation_data(request, details_qs, filters, province_id):
    professions = list(details_qs.exclude(menteename_id__isnull=True).order_by().values(
        profession_id=F('menteename__position_id'), profession=F('menteename__position__name'),
    ).annotate(
        mentees=Count('menteename_id', distinct=True),
        female=Count('menteename_id', distinct=True, filter=Q(menteename__gender=True)),
        male=Count('menteename_id', distinct=True, filter=Q(menteename__gender=False)),
        unspecified=Count('menteename_id', distinct=True, filter=Q(menteename__gender__isnull=True)),
    ).order_by('-mentees', 'profession', 'profession_id'))
    actual = defaultdict(set)
    actual_names = defaultdict(set)
    for day, mentor in details_qs.order_by().values_list('mentorshipvistfk__visitdate', 'mentor__name').iterator(chunk_size=2000):
        name = (mentor or '').strip().lower()
        if day and name:
            month = day.replace(day=1)
            actual[month].add((day, name))
            actual_names[month].add(name)
    from_date = date.fromisoformat(filters['date_from']) if filters.get('date_from') else None
    to_date = date.fromisoformat(filters['date_to']) if filters.get('date_to') else None
    months = set(actual)
    start = from_date.replace(day=1) if from_date else min(months, default=None)
    end = to_date.replace(day=1) if to_date else max(months, default=None)
    if start and end:
        current = start
        while current <= end:
            months.add(current)
            current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    rows = []
    for month in sorted(months):
        count = len(actual.get(month, set()))
        mentors = len(actual_names.get(month, set()))
        rows.append({'month': month, 'month_label': month.strftime('%b %Y'), 'mentor_visits': count,
                     'mentors_with_visits': mentors,
                     'average_actual': round(count / mentors, 2) if mentors else None})
    total = sum(r['mentor_visits'] for r in rows)
    return {'profession_rows': professions, 'monthly_visit_rows': rows,
            'monthly_average_visits': round(total / len(rows), 2) if rows else None,
            'monthly_visit_max': max([r['mentor_visits'] for r in rows] + [1])}
