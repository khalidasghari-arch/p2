"""Read-only checks of LS chronology against recorded competency, by actual IDs."""
from collections import defaultdict
from django.db.models import F, Q


def classify_sequence(history, facility_id):
    competencies = [e for e in history if e['pc'] or e['mc']]
    first = min((e['date'] for e in competencies if e['date']), default=None)
    learning = [e for e in history if e['ls']]
    earlier = [e for e in learning if e['date'] and first and e['date'] < first]
    # An undated event can change which event was first. Never infer chronology.
    uncertain = any(not e['date'] for e in competencies + learning)
    if uncertain or first is None:
        code, label = 'undated', 'Missing dates — verify sequence'
    elif earlier:
        code, label = 'confirmed', 'Earlier LS recorded'
    elif any(e['date'] == first for e in learning):
        code, label = 'same_day', 'Same-day LS/PC/MC — verify sequence'
    elif learning:
        code, label = 'later_ls', 'LS only after first PC/MC — verify sequence'
    else:
        code, label = 'no_ls', 'No LS in available authorized history — verify'
    outside = bool(earlier and not any(e['facility_id'] == facility_id for e in earlier))
    return {'code': code, 'interpretation': label, 'first_competency_date': first,
            'prior_ls_visits': len({e['visit_id'] for e in earlier}),
            'prior_ls_other_facility': outside, 'confirmed': code == 'confirmed'}


def build_sequence_data(details_qs, authorized_history, filters):
    # Only competencies in the displayed activity scope produce profile checks.
    selected = list(details_qs.filter(Q(pc=True) | Q(mc=True)).exclude(
        menteename_id__isnull=True).exclude(topicname_id__isnull=True).order_by().values(
        'menteename_id', 'topicname_id', 'mentorshipvistfk__facilityfk_id',
        'topicname__name').distinct())
    pairs = {(r['menteename_id'], r['topicname_id']) for r in selected}
    histories = defaultdict(list)
    if pairs:
        history = authorized_history.filter(menteename_id__in={p[0] for p in pairs},
                                             topicname_id__in={p[1] for p in pairs})
        if filters.get('date_to'):
            history = history.filter(Q(mentorshipvistfk__visitdate__lte=filters['date_to']) |
                                     Q(mentorshipvistfk__visitdate__isnull=True))
        for row in history.order_by().values('ls', 'pc', 'mc',
                mentee_id=F('menteename_id'), topic_id=F('topicname_id'),
                date=F('mentorshipvistfk__visitdate'), visit_id=F('mentorshipvistfk_id'),
                facility_id=F('mentorshipvistfk__facilityfk_id')).iterator(chunk_size=2000):
            pair = (row['mentee_id'], row['topic_id'])
            if pair in pairs:
                histories[pair].append(row)
    checks = {}
    for row in selected:
        mid, tid, fid = row['menteename_id'], row['topicname_id'], row['mentorshipvistfk__facilityfk_id']
        checks[(fid, mid, tid)] = {'topic_id': tid, 'topic': row['topicname__name'],
                                  **classify_sequence(histories[(mid, tid)], fid)}
    return {'sequence_checks': checks}
