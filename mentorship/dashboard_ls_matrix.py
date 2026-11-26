"""Province/thematic LS totals from the already authorized, filtered details."""
from django.db.models import Count, Q


def build_ls_matrix(details):
    province_path = 'mentorshipvistfk__facilityfk__districtfk__provincefk'
    # Group source records by IDs, then combine the requested reporting areas.
    groups = list(details.order_by().values(
        province_path, province_path + '__name',
        'thematicname_id', 'thematicname__name',
    ).annotate(ls_total=Count('pk', filter=Q(ls=True))))
    provinces = {}
    thematics = {}
    counts = {}
    for group in groups:
        province_id = group[province_path]
        thematic_id = group['thematicname_id']
        provinces[province_id] = group[province_path + '__name'] or 'Province not entered'
        name = group['thematicname__name'] or 'Thematic area not entered'
        normalized = ' '.join(name.split()).casefold()
        if normalized in {
            'antenatal care (anc)',
            'perinatal mental health (pmh)',
            'maternal and child health (mch) handbook',
        }:
            thematic_id = -1  # Reporting-only ANC group; no database records change.
            name = 'Antenatal Care (ANC)'
        thematics[thematic_id] = name
        key = (province_id, thematic_id)
        counts[key] = counts.get(key, 0) + group['ls_total']
    columns = sorted(thematics, key=lambda pk: (thematics[pk].casefold(), pk or 0))
    rows = []
    totals = [0] * len(columns)
    for province_id in sorted(provinces, key=lambda pk: (provinces[pk].casefold(), pk or 0)):
        values = [int(counts.get((province_id, pk), 0)) for pk in columns]
        rows.append({'province': provinces[province_id], 'values': values, 'total': sum(values)})
        totals = [a + b for a, b in zip(totals, values)]
    return {'columns': [thematics[pk] for pk in columns], 'rows': rows,
            'totals': totals, 'grand_total': sum(totals)}


def append_ls_matrix_sheet(workbook, matrix):
    sheet = workbook.create_sheet('LS_Province_Thematic')
    sheet.append(['Province', *matrix['columns'], 'Grand Total'])
    for row in matrix['rows']:
        sheet.append([row['province'], *row['values'], row['total']])
    sheet.append(['Grand Total', *matrix['totals'], matrix['grand_total']])
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    for row_number in (1, sheet.max_row):
        for cell in sheet[row_number]:
            cell.fill = PatternFill('solid', fgColor='073F35')
            cell.font = Font(color='FFFFFF', bold=True)
    sheet.row_dimensions[1].height = 65
    for cell in sheet[1]:
        cell.alignment = Alignment(wrap_text=True, vertical='center')
    for column in range(1, sheet.max_column + 1):
        sheet.column_dimensions[get_column_letter(column)].width = 25 if column == 1 else 22
    sheet.freeze_panes = 'B2'
    return sheet
