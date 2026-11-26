"""Filtered province/thematic activity and distinct mentees by database ID."""
from collections import defaultdict
from django.db.models import Count, Q

ANC_GROUP = {
    'antenatal care (anc)',
    'perinatal mental health (pmh)',
    'maternal and child health (mch) handbook',
}


def build_ls_matrix(details):
    province_path = 'mentorshipvistfk__facilityfk__districtfk__provincefk'
    # Aggregate in SQL by mentee and source thematic ID, then union IDs after
    # reporting groups are mapped. Summing distinct source counts would overcount ANC.
    groups = details.order_by().values(
        province_path, province_path + '__name',
        'thematicname_id', 'thematicname__name', 'menteename_id',
    ).annotate(
        ls_total=Count('pk', filter=Q(ls=True)),
        competent_records=Count('pk', filter=Q(pc=True) | Q(mc=True)),
    )
    provinces, thematics = {}, {}
    counts = defaultdict(int)
    learners, competent = defaultdict(set), defaultdict(set)
    province_learners, province_competent = defaultdict(set), defaultdict(set)
    area_learners, area_competent = defaultdict(set), defaultdict(set)
    all_learners, all_competent = set(), set()
    for group in groups:
        province_id = group[province_path]
        thematic_id = group['thematicname_id']
        provinces[province_id] = group[province_path + '__name'] or 'Province not entered'
        name = group['thematicname__name'] or 'Thematic area not entered'
        if ' '.join(name.split()).casefold() in ANC_GROUP:
            thematic_id, name = -1, 'Antenatal Care (ANC)'
        thematics[thematic_id] = name
        key = (province_id, thematic_id)
        counts[key] += group['ls_total']
        mentee_id = group['menteename_id']
        if mentee_id is None:
            continue
        if group['ls_total']:
            learners[key].add(mentee_id)
            province_learners[province_id].add(mentee_id)
            area_learners[thematic_id].add(mentee_id)
            all_learners.add(mentee_id)
        if group['competent_records']:
            competent[key].add(mentee_id)
            province_competent[province_id].add(mentee_id)
            area_competent[thematic_id].add(mentee_id)
            all_competent.add(mentee_id)
    columns = sorted(thematics, key=lambda pk: (thematics[pk].casefold(), pk or 0))
    rows, totals = [], [0] * len(columns)
    for province_id in sorted(provinces, key=lambda pk: (provinces[pk].casefold(), pk or 0)):
        values = [counts[(province_id, pk)] for pk in columns]
        rows.append({
            'province': provinces[province_id], 'values': values, 'total': sum(values),
            'ls_mentees_values': [len(learners[(province_id, pk)]) for pk in columns],
            'ls_mentees_total': len(province_learners[province_id]),
            'competent_mentees_values': [len(competent[(province_id, pk)]) for pk in columns],
            'competent_mentees_total': len(province_competent[province_id]),
        })
        totals = [a + b for a, b in zip(totals, values)]
    return {
        'columns': [thematics[pk] for pk in columns], 'rows': rows,
        'totals': totals, 'grand_total': sum(totals),
        'ls_mentees_totals': [len(area_learners[pk]) for pk in columns],
        'ls_mentees_grand_total': len(all_learners),
        'competent_mentees_totals': [len(area_competent[pk]) for pk in columns],
        'competent_mentees_grand_total': len(all_competent),
    }


def append_ls_matrix_sheet(workbook, matrix):
    sheet = workbook.create_sheet('LS_Province_Thematic')
    sheet.append(['Province', 'Indicator', *matrix['columns'], 'Grand Total'])
    for row in matrix['rows']:
        sheet.append([row['province'], 'LS entries', *row['values'], row['total']])
        sheet.append([row['province'], 'Distinct mentees receiving LS', *row['ls_mentees_values'], row['ls_mentees_total']])
        sheet.append([row['province'], 'Distinct mentees with PC or MC', *row['competent_mentees_values'], row['competent_mentees_total']])
    sheet.append(['Grand Total', 'LS entries', *matrix['totals'], matrix['grand_total']])
    sheet.append(['Grand Total', 'Distinct mentees receiving LS', *matrix['ls_mentees_totals'], matrix['ls_mentees_grand_total']])
    sheet.append(['Grand Total', 'Distinct mentees with PC or MC', *matrix['competent_mentees_totals'], matrix['competent_mentees_grand_total']])
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    for row_number in (1, sheet.max_row - 2, sheet.max_row - 1, sheet.max_row):
        for cell in sheet[row_number]:
            cell.fill = PatternFill('solid', fgColor='073F35')
            cell.font = Font(color='FFFFFF', bold=True)
    sheet.row_dimensions[1].height = 65
    for cell in sheet[1]:
        cell.alignment = Alignment(wrap_text=True, vertical='center')
    for column in range(1, sheet.max_column + 1):
        sheet.column_dimensions[get_column_letter(column)].width = 34 if column == 2 else 24
    sheet.freeze_panes = 'C2'
    notes = workbook.create_sheet('LS_Matrix_Notes')
    notes.append(['Indicator', 'Definition'])
    notes.append(['LS entries', 'Number of saved mentorship detail records with LS=True, including repeated sessions.'])
    notes.append(['Distinct mentees receiving LS', 'Unique non-null menteename IDs with LS=True under the selected filters.'])
    notes.append(['Distinct mentees with PC or MC', 'Unique non-null menteename IDs with PC=True OR MC=True under the selected filters. Prior LS is not required for this recorded-competency measure; saved topic status is not used.'])
    notes.append(['Distinct totals', 'Union of mentee IDs, not sum of cell counts. A mentee appearing in several areas or provinces is counted once in the applicable total.'])
    notes.append(['ANC grouping', 'ANC combines Antenatal Care, Perinatal Mental Health and MCH Handbook. Mentee IDs are deduplicated across these areas.'])
    notes.append(['Scope', 'These indicators use the same authorized, filtered records as the dashboard. Province is based on visit facility.'])
    notes.column_dimensions['A'].width = 35
    notes.column_dimensions['B'].width = 105
    for row in notes:
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical='top')
    return sheet
