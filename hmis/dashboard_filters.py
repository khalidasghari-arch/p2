"""HMIS dashboard extension. No model/schema changes; inherits existing helpers."""
import os
import tempfile
from calendar import month_name
from django.contrib import messages
from django.db.models import Q, Sum, Count, Max
from django.http import FileResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from hmis.models import HMISFact, HMISMonthlySummary

# Must match slugify(indicator_name) in the supplied import pipeline.
SUMMARY_CODES = {
    'anc1': 'anc1', 'anc2': 'anc2', 'anc3': 'anc3', 'anc4': 'anc4',
    'pnc1': 'pnc1', 'pnc2': 'pnc2', 'n_delivery': 'n-delivery',
    'a_delivery': 'a-delivery', 'c_section': 'c-section',
    'lbw': 'lbw', 'stillbirth': 'stillbirth',
}
BASELINE_NOTE = (
    'Baseline: distinct facilities observed anywhere in HMIS history, limited by '
    'the selected facility group and location. This assumes those facilities are '
    'expected in every displayed month; facilities never recorded and changes '
    'in operational status cannot be determined from these models. A monthly '
    'summary with at least one nonblank indicator, or a nonblank HMIS fact, counts '
    'as reported. Zero counts as reported. Missing means no recorded report, '
    'not a confirmed overdue submission.'
)


def month_periods(start, end, years=(), months=()):
    """Include gaps inside the database's observed calendar range."""
    if not start or not end:
        return []
    year, month = int(start[:4]), int(start[4:])
    result = []
    while f'{year:04d}{month:02d}' <= end:
        if (not years or year in years) and (not months or month in months):
            result.append(f'{year:04d}{month:02d}')
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result


def reporting_rows(roster, submissions, periods):
    """One reporting count per facility/month, independent of indicator selection."""
    submitted = {}
    for hf, period in submissions:
        submitted.setdefault(period, set()).add(hf)
    expected = set(roster)
    rows = []
    for period in periods:
        reporting = expected & submitted.get(period, set())
        missing = sorted(expected - reporting, key=str.casefold)
        rows.append({
            'periodcode': period,
            'period': f'{month_name[int(period[4:])]} {period[:4]}',
            'expected': len(expected), 'reported': len(reporting),
            'missing_count': len(missing),
            'rate': round(100 * len(reporting) / len(expected), 2) if expected else None,
            'rate_display': f'{100 * len(reporting) / len(expected):.1f}%' if expected else '—',
            'missing': [dict(roster[hf], hf=hf) for hf in missing],
        })
    return rows


class HMISDashboardFilterMixin:
    """Place before admin.ModelAdmin in HMISDashboardAdmin's inheritance list."""

    def _catalogue(self):
        fields = ('prov', 'dist', 'hf', 'hiva_hfs', 'year', 'month', 'periodcode')
        # Union includes facilities/periods present in either reporting table.
        rows = list(HMISMonthlySummary.objects.order_by().values_list(*fields).union(
            HMISFact.objects.order_by().values_list(*fields)))
        result = []
        for prov, dist, hf, hiva, year, month, period in rows:
            period = str(period or '')
            if len(period) != 6 or not period.isdigit() or not 1 <= int(period[4:]) <= 12:
                continue
            if year != int(period[:4]) or month != int(period[4:]):
                continue
            result.append(dict(province=prov, district=dist, facility=hf,
                               group='hiva' if hiva else 'non_hiva',
                               year=year, month=month, periodcode=period))
        return result

    @staticmethod
    def _geo_rows(rows, filters):
        return [r for r in rows if
                (filters['facility_group'] == 'all' or r['group'] == filters['facility_group'])
                and (not filters['prov'] or r['province'] == filters['prov'])
                and (not filters['dist'] or r['district'] == filters['dist'])
                and (not filters['hf'] or r['facility'] == filters['hf'])]

    def _read_filters(self, request):
        def integers(key, lower, upper):
            values = []
            for raw in request.GET.getlist(key):
                try:
                    value = int(raw)
                except (TypeError, ValueError):
                    continue
                if lower <= value <= upper and value not in values:
                    values.append(value)
            return sorted(values)
        indicators = list(dict.fromkeys(
            value for value in request.GET.getlist('indicator') if value in SUMMARY_CODES))
        group = request.GET.get('facility_group', 'all')
        return dict(prov=request.GET.get('prov', '').strip(),
                    dist=request.GET.get('dist', '').strip(), hf=request.GET.get('hf', '').strip(),
                    facility_group=group if group in ('all', 'hiva', 'non_hiva') else 'all',
                    year=integers('year', 1, 9999), month=integers('month', 1, 12),
                    indicator=indicators)

    def _filter_queryset(self, queryset, filters):
        for name in ('prov', 'dist', 'hf'):
            if filters[name]:
                queryset = queryset.filter(**{name: filters[name]})
        for name in ('year', 'month'):
            if filters[name]:
                queryset = queryset.filter(**{name + '__in': filters[name]})
        return self._apply_facility_group(queryset, filters['facility_group'])

    def _filter_fact_queryset(self, queryset, filters):
        queryset = self._filter_queryset(queryset, filters)
        if filters['indicator']:
            queryset = queryset.filter(indicator_code__in=[SUMMARY_CODES[x] for x in filters['indicator']])
        return queryset

    def _filter_options(self, rows, filters):
        groups = sorted({r['group'] for r in rows})
        scope = [r for r in rows if filters['facility_group'] == 'all' or r['group'] == filters['facility_group']]
        provinces = sorted({r['province'] for r in scope if r['province']})
        if filters['prov']:
            scope = [r for r in scope if r['province'] == filters['prov']]
        districts = sorted({r['district'] for r in scope if r['district']})
        if filters['dist']:
            scope = [r for r in scope if r['district'] == filters['dist']]
        facilities = sorted({r['facility'] for r in scope if r['facility']})
        if filters['hf']:
            scope = [r for r in scope if r['facility'] == filters['hf']]
        years = sorted({r['year'] for r in scope}, reverse=True)
        if filters['year']:
            scope = [r for r in scope if r['year'] in filters['year']]
        months = sorted({r['month'] for r in scope})
        return dict(groups=[{'value': x, 'label': 'HIVA Health Facilities' if x == 'hiva'
                            else 'Non-HIVA Health Facilities'} for x in groups],
                    provinces=provinces, districts=districts, facilities=facilities,
                    years=years, months=[{'value': x, 'label': month_name[x]} for x in months],
                    location_cascade=rows)

    def _indicator_options(self, filters):
        summaries = self._filter_queryset(HMISMonthlySummary.objects.all(), filters)
        facts = self._filter_queryset(HMISFact.objects.all(), filters)
        codes = set(facts.exclude(value__isnull=True).values_list('indicator_code', flat=True).distinct())
        counts = summaries.aggregate(**{field: Count(field) for field in SUMMARY_CODES})
        return [(field, label) for field, label in self.INDICATORS
                if counts[field] or SUMMARY_CODES[field] in codes]

    def _reporting(self, catalogue, filters):
        # Latest observed location/group per facility; dates never shrink the roster.
        latest = {}
        for r in sorted(catalogue, key=lambda r: (r['periodcode'], r['province'], r['district'], r['group'])):
            if r['facility']:
                latest[r['facility']] = r
        roster = {r['facility']: {'prov': r['province'], 'dist': r['district'],
                                 'group': r['group']} for r in self._geo_rows(list(latest.values()), filters)}
        observed = sorted({r['periodcode'] for r in catalogue})
        periods = month_periods(observed[0], observed[-1], filters['year'], filters['month']) if observed else []
        nonblank = Q()
        for field in SUMMARY_CODES:
            nonblank |= Q(**{field + '__isnull': False})
        # Query by roster identity, regardless of historical group/location changes.
        summaries = HMISMonthlySummary.objects.filter(nonblank, hf__in=roster, periodcode__in=periods)
        facts = HMISFact.objects.filter(hf__in=roster, periodcode__in=periods, value__isnull=False)
        submissions = summaries.order_by().values_list('hf', 'periodcode').union(
            facts.order_by().values_list('hf', 'periodcode'))
        return reporting_rows(roster, submissions, periods)

    @staticmethod
    def _msh_header(worksheet, headers, widths=None):
        worksheet.freeze_panes = 'A2'
        color = 'EF6C00' if worksheet.title == 'Missing Reports' else '073F36'
        cells = []
        for index, header in enumerate(headers, 1):
            cell = WriteOnlyCell(worksheet, value=header)
            cell.fill = PatternFill('solid', fgColor=color)
            cell.font = Font(color='FFFFFF', bold=True, size=11)
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            cells.append(cell)
            worksheet.column_dimensions[get_column_letter(index)].width = widths[index - 1] if widths else 20
        worksheet.append(cells)

    def _multi_excel(self, facts, filters, reporting):
        workbook = Workbook(write_only=True)
        scope = workbook.create_sheet('Summary')
        title = WriteOnlyCell(scope, value='MSH | IQoC-MNH | HMIS filtered export')
        title.font = Font(color='FFFFFF', bold=True, size=14)
        title.fill = PatternFill('solid', fgColor='073F36')
        scope.append([title, timezone.localtime().isoformat()])
        for key in ('facility_group', 'prov', 'dist', 'hf', 'year', 'month', 'indicator'):
            values = filters[key]
            if key == 'month':
                values = [month_name[x] for x in values]
            if key == 'indicator':
                values = [self.INDICATOR_LABELS[x] for x in values]
            scope.append([key, self._excel_text(', '.join(map(str, values)) if isinstance(values, list)
                                               else values or 'All') or 'All'])
        scope.append(['Reporting baseline', BASELINE_NOTE])
        self._msh_header(scope, ('Indicator Code', 'Indicator Name', 'Total', 'Nonblank Values'), (20, 48, 18, 18))
        for r in facts.values('indicator_code').annotate(name=Max('indicator_name'), total=Sum('value'), n=Count('value')).order_by('indicator_code').iterator():
            scope.append([self._excel_text(r['indicator_code']), self._excel_text(r['name']), r['total'], r['n']])
        details = workbook.create_sheet('Details')
        fields = ('id', 'source_upload_id', 'prov', 'dist', 'hf', 'periodcode', 'year', 'month',
                  'month_name', 'hf_name_cleaned', 'hfid', 'hiva_hfs', 'indicator_code', 'indicator_name', 'value', 'created_at')
        self._msh_header(details, fields, (12,16,18,18,34,14,10,10,14,34,12,12,20,48,18,24))
        for row in facts.order_by().values_list(*fields).iterator(chunk_size=5000):
            values = [self._excel_text(v) for v in row]
            values[-1] = self._datetime_display(values[-1])
            details.append(values)
        monthly = workbook.create_sheet('Reporting Completeness')
        self._msh_header(monthly, ('Month', 'Expected Known Facilities', 'Reporting', 'Missing', 'Completeness (%)'), (24,28,16,16,24))
        missing = workbook.create_sheet('Missing Reports')
        self._msh_header(missing, ('Month', 'Province', 'District', 'Facility', 'Facility Group'), (24,22,22,40,20))
        for row in reporting:
            monthly.append([row['period'], row['expected'], row['reported'], row['missing_count'], row['rate']])
            for facility in row['missing']:
                missing.append([self._excel_text(x) for x in (row['period'], facility['prov'], facility['dist'], facility['hf'], facility['group'])])
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as handle:
                path = handle.name
            workbook.save(path)
            response = FileResponse(open(path, 'rb'), as_attachment=True,
                                    filename='HMIS_Filtered_Dashboard.xlsx',
                                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Cache-Control'] = 'no-store'
            response._resource_closers.append(lambda: os.path.exists(path) and os.remove(path))
            return response
        except Exception:
            if path and os.path.exists(path):
                os.remove(path)
            raise

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        filters = self._read_filters(request)
        catalogue = self._catalogue()
        options = self._filter_options(catalogue, filters)
        indicator_options = self._indicator_options(filters)
        summaries = self._filter_queryset(HMISMonthlySummary.objects.all(), filters)
        facts = self._filter_fact_queryset(HMISFact.objects.all(), filters)
        reporting = self._reporting(catalogue, filters)
        if request.GET.get('export') == 'xlsx':
            if facts.count() > self._filtered_excel_row_limit():
                self.message_user(request, 'Please narrow the filters: the Excel detail row limit was exceeded.', level=messages.WARNING)
                params = request.GET.copy()
                params.pop('export', None)
                return HttpResponseRedirect(request.path + '?' + params.urlencode())
            return self._multi_excel(facts, filters, reporting)
        first = filters['indicator'][0] if filters['indicator'] else 'anc1'
        data = self._build_dashboard_data(summaries, first)
        data['selected_indicator_label'] = ', '.join(self.INDICATOR_LABELS[x] for x in filters['indicator']) or 'All HMIS indicators'
        cards, charts = self._all_hmis_indicator_trends(facts)
        data['all_hmis_indicator_cards'] = cards
        data['chart_data']['all_hmis_indicator_trends'] = charts
        data.update(self._fact_detail_tables(facts, cards, first))
        expected = sum(r['expected'] for r in reporting)
        reported = sum(r['reported'] for r in reporting)
        data['kpis'].insert(0, dict(label='Monthly Reporting Completeness',
            value=self._percent_display(self._percent(reported, expected)),
            help=f'{reported:,}/{expected:,} expected known facility-month reports', **{'class': 'green'}))
        for kpi in data['kpis']:
            if kpi['label'] == 'Data Completeness':
                kpi['label'] = 'Summary Field Completeness'
        for_print = bool(request.GET.get('print'))
        export_params = request.GET.copy()
        export_params.pop('print', None)
        export_params['export'] = 'xlsx'
        print_params = request.GET.copy()
        print_params.pop('export', None)
        print_params['print'] = 'filtered'
        primary_names = ('Monthly Reporting Completeness', 'Health Facilities', 'Reporting Periods',
                         'ANC 1st Visit', 'PNC 1st Visit', 'Total Deliveries')
        data['primary_kpis'] = [kpi for name in primary_names for kpi in data['kpis'] if kpi['label'] == name]
        data['additional_kpis'] = [kpi for kpi in data['kpis'] if kpi['label'] not in primary_names]
        context = {**self.admin_site.each_context(request), **data,
                   'title': 'HMIS Performance Dashboard', 'opts': self.model._meta,
                   'filters': filters, 'filter_options': options, 'indicator_options': indicator_options,
                   'reporting_rows': reporting, 'reporting_note': BASELINE_NOTE,
                   'export_url': '?' + export_params.urlencode(), 'print_url': '?' + print_params.urlencode(),
                   'excel_export_limit_display': f'{self._filtered_excel_row_limit():,}',
                   'print_all_mode': for_print}
        if extra_context:
            context.update(extra_context)
        request.current_app = self.admin_site.name
        return TemplateResponse(request, self.change_list_template, context)
