"""Read-only mentee identity, current-status attrition and facility-history review."""
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
import re
import unicodedata

from django.db.models import F
from .models import Staff

MISSING_FATHER = 'FATHERNAME NOT ENTERED'


def display_name(value):
    """Uppercase the initial letter of each name part; preserve other letters."""
    return re.sub(r'(?<!\w)([^\W\d_])', lambda match: match.group().upper(), ' '.join(str(value or '').split()))


def normalized_name(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w]+', ' ', value, flags=re.UNICODE).split())


def name_issues(value, label, required=False):
    original = str(value or '')
    value = original.strip()
    if not value:
        return [f'{label} missing'] if required else []
    issues = []
    if any(match.group().islower() for match in re.finditer(r'(?<!\w)([^\W\d_])', value)):
        issues.append(f'{label}: initial capital letter required')
    if original != value or re.search(r'\s{2,}', value):
        issues.append(f'{label}: extra whitespace — verify formatting')
    if any(c.isdigit() for c in value):
        issues.append(f'{label}: contains digits')
    if any(not (c.isalpha() or unicodedata.combining(c) or c.isspace() or c in ".'-’ـ") for c in value):
        issues.append(f'{label}: unusual characters — verify spelling')
    if normalized_name(value) in {'unknown', 'test', 'dummy', 'na', 'n a', 'none', 'null', 'not entered'}:
        issues.append(f'{label}: placeholder text — confirm real name')
    if not any(c.isalpha() for c in value):
        issues.append(f'{label}: no letters — confirm real name')
    return issues


def identity_rows(records):
    identities, review = {}, []
    for row in records:
        raw_name = ' '.join(str(row.get(key) or '').strip() for key in ('firstname', 'lastname')).strip()
        father = str(row.get('fathername') or '').strip()
        identity = {
            **row, 'mentee_id': row['id'], 'mentee': display_name(raw_name),
            'fathername': display_name(father) or MISSING_FATHER,
            'fathername_missing': not bool(father),
        }
        identities[row['id']] = identity
        issues = (name_issues(row.get('firstname'), 'First name', True)
                  + name_issues(row.get('lastname'), 'Last name')
                  + name_issues(father, 'Father name', True))
        if issues:
            review.append({**identity, 'issues': '; '.join(issues),
                           'recorded_values': f"First: {row.get('firstname') or ''}; Last: {row.get('lastname') or ''}; Father: {father or MISSING_FATHER}",
                           'suggested_values': f"First: {display_name(row.get('firstname'))}; Last: {display_name(row.get('lastname'))}; Father: {display_name(father) or 'Clinical mentor must confirm'}"})
    return identities, review


def duplicate_candidates(identities):
    """Flag candidates only; names cannot establish duplicate identity."""
    exact, fathers = defaultdict(list), defaultdict(list)
    for identity in identities.values():
        key = normalized_name(' '.join(str(identity.get(k) or '') for k in ('firstname', 'lastname')))
        father = normalized_name(identity.get('fathername')) if not identity['fathername_missing'] else ''
        if key:
            exact[key].append((identity, father, key))
        if key and father:
            fathers[(father, key[0])].append((identity, father, key))
    found = {}
    def add(left, right, reason, score):
        a, b = sorted((left, right), key=lambda row: row['id'])
        found[(a['id'], b['id'])] = {
            'mentee_id': a['id'], 'mentee': a['mentee'], 'fathername': a['fathername'],
            'fathername_missing': a['fathername_missing'], 'facility': a.get('facility') or '',
            'other_id': b['id'], 'other_mentee': b['mentee'], 'other_fathername': b['fathername'],
            'other_fathername_missing': b['fathername_missing'], 'other_facility': b.get('facility') or '',
            'reason': reason, 'similarity': round(score * 100, 1),
        }
    for group in exact.values():
        for (a, af, _), (b, bf, _) in combinations(group, 2):
            if af and bf and af != bf:
                continue
            if af and bf:
                add(a, b, 'Same normalized mentee name and father name — confirm identity', 1)
            else:
                add(a, b, 'Same normalized mentee name; father name missing — may be namesakes', 1)
    for group in fathers.values():
        for (a, _, an), (b, _, bn) in combinations(group, 2):
            if an == bn:
                continue
            similarity = SequenceMatcher(None, an, bn).ratio()
            if similarity >= .90:
                add(a, b, 'Similar mentee name (≥90%) and same father name — possible spelling variation', similarity)
    return list(found.values())


def facility_history(events, selected_events):
    """Earlier/later means distinct dates. Same-day facility order is unknown."""
    grouped = defaultdict(lambda: defaultdict(dict))
    for event in events:
        if event['date'] and event['facility_id'] is not None:
            grouped[event['mentee_id']][event['date']][event['facility_id']] = event
    multiple, changes, ambiguous = [], [], []
    for mentee_id, dated in grouped.items():
        all_facilities = {fid for day in dated.values() for fid in day}
        if len(all_facilities) > 1:
            names = {fid: event['facility'] for day in dated.values() for fid, event in day.items()}
            multiple.append({'mentee_id': mentee_id, 'facility_count': len(all_facilities),
                             'facilities': '; '.join(f'{names[fid]} (#{fid})' for fid in sorted(names)),
                             'first_seen': min(dated), 'last_seen': max(dated)})
        previous = None
        for day, facilities in sorted(dated.items()):
            if len(facilities) > 1:
                # Any selected detail for this date/facility makes this a review item.
                if any((mentee_id, day, fid) in selected_events for fid in facilities):
                    ambiguous.append({'mentee_id': mentee_id, 'date': day,
                                      'facilities': '; '.join(e['facility'] for e in facilities.values()),
                                      'reason': 'Multiple facilities on the same date — sequence unknown'})
                previous = None
                continue
            current = next(iter(facilities.values()))
            if previous and current['facility_id'] != previous['facility_id']:
                if (mentee_id, day, current['facility_id']) in selected_events:
                    changes.append({'mentee_id': mentee_id, 'from_facility': previous['facility'],
                                    'to_facility': current['facility'], 'previous_date': previous['date'],
                                    'later_date': day, 'reason': 'Later mentorship recorded in a different facility — confirm reason'})
            previous = current
    return multiple, changes, ambiguous


def build_quality_data(request, details_qs, scoped_history_qs, filters, province_id, roster_rows, status_counts):
    selected_ids = set(details_qs.order_by().exclude(menteename_id__isnull=True).values_list('menteename_id', flat=True))
    # Review roster plus participants in matching visits. These identities are
    # already visible in the existing authorized dashboard details.
    review_ids = selected_ids | {row['id'] for row in roster_rows}
    records = Staff.objects.filter(pk__in=review_ids).values(
        'id', 'firstname', 'lastname', 'fathername', 'gender', 'status',
        facility=F('hfname__name'), facility_id=F('hfname_id'),
    )
    identities, quality_rows = identity_rows(records)
    candidates = duplicate_candidates(identities)
    selected_events = set(details_qs.order_by().exclude(menteename_id__isnull=True).values_list(
        'menteename_id', 'mentorshipvistfk__visitdate', 'mentorshipvistfk__facilityfk_id'))
    history = scoped_history_qs.filter(menteename_id__in=selected_ids)
    # Do not use observations after the selected end date to infer movement.
    if filters.get('date_to'):
        history = history.filter(mentorshipvistfk__visitdate__lte=filters['date_to'])
    events = history.order_by().values(
        mentee_id=F('menteename_id'), date=F('mentorshipvistfk__visitdate'),
        facility_id=F('mentorshipvistfk__facilityfk_id'), facility=F('mentorshipvistfk__facilityfk__name'))
    multiple, changes, ambiguous = facility_history(events.iterator(chunk_size=2000), selected_events)
    for rows in (multiple, changes, ambiguous):
        for row in rows:
            identity = identities[row['mentee_id']]
            row.update({key: identity[key] for key in ('mentee', 'fathername', 'fathername_missing')})
    denominator = status_counts['active'] + status_counts['inactive']
    attrition_rate = round(100 * status_counts['inactive'] / denominator, 1) if denominator else None
    return {
        'mentee_identity_map': identities, 'quality_rows': quality_rows, 'duplicate_rows': candidates,
        'multiple_facility_rows': multiple, 'facility_change_rows': changes, 'facility_sequence_review_rows': ambiguous,
        'attrition_rate': attrition_rate, 'attrition_denominator': denominator,
        'quality_kpis': {
            'reviewed_mentees': len(identities),
            'missing_fathername': sum(r['fathername_missing'] for r in identities.values()),
            'name_review_mentees': len(quality_rows), 'duplicate_pairs': len(candidates),
            'multiple_facility_mentees': len(multiple),
            'later_facility_mentees': len({r['mentee_id'] for r in changes}),
            'facility_sequence_review_mentees': len({r['mentee_id'] for r in ambiguous}),
        },
    }
