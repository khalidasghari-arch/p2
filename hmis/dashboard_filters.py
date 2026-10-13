"""HMIS dashboard extension. No model/schema changes; inherits existing helpers."""
import os
import tempfile
from calendar import month_name
from decimal import Decimal, ROUND_HALF_UP
from django.contrib import messages
from django.db.models import Q, Sum, Count, Max
from django.http import FileResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from hmis.models import HMISFact, HMISMonthlySummary, IndicatorMetadata

# Must match slugify(indicator_name) in the supplied import pipeline.
SUMMARY_CODES = {
    'anc1': 'anc1', 'anc2': 'anc2', 'anc3': 'anc3', 'anc4': 'anc4',
    'pnc1': 'pnc1', 'pnc2': 'pnc2', 'n_delivery': 'n-delivery',
    'a_delivery': 'a-delivery', 'c_section': 'c-section',
    'lbw': 'lbw', 'stillbirth': 'stillbirth',
}
COMPOSITE_INDICATORS = (
    ('lbw', 'LBW (% of live births)'),
    ('babies-breastfed-1st-hour', 'Breastfed 1st Hour (% of live births)'),
    ('newborn-resuscitated', 'NB Resuscitated (% of live births)'),
    ('premature', 'Premature (% of live births)'),
)
LIVE_BIRTH_CODE = 'newbornalive'
COMPOSITE_NOTE = (
    'Each percentage = the recorded numerator ÷ Newborn Alive × 100 for matching '
    'facility-months. Only pairs with a nonblank, nonnegative numerator and a '
    'positive denominator contribute to both totals. Recorded zero numerators '
    'are included; missing values are not treated as zero. Combined rates use '
    'summed counts, not an average of percentages. These measures use the selected '
    'location and dates and remain available regardless of the indicator dropdown. '
    'NB Resuscitated is a share of live births, not a resuscitation success rate '
    'or coverage among babies needing resuscitation. Numerators must refer to '
    'the same live-born population as Newborn Alive; out-of-facility or referred '
    'cases can make that comparison inappropriate.'
)


def calculate_composites(pairs):
    """Rates plus facility/month follow-up, without changing eligibility rules."""
    result = []
    for code, label in COMPOSITE_INDICATORS:
        short_name = label.split(' (')[0]
        numerator = denominator = Decimal('0')
        matched = excluded = above = 0
        missing_numerator = missing_denominator = zero_denominator = negative = 0
        issues = []
        for (facility, periodcode), values in sorted(pairs.items()):
            n, d = values.get(code), values.get(LIVE_BIRTH_CODE)
            reason = action = ''
            included = False
            if n is None or d is None:
                excluded += 1
                missing_numerator += n is None
                missing_denominator += d is None
                if n is None and d is None:
                    reason = f'{short_name} and Newborn Alive values are missing from imported data'
                elif n is None:
                    reason = f'{short_name} value is missing from imported data'
                else:
                    reason = 'Newborn Alive value is missing from imported data'
                action = 'Check the facility report for this month. Confirm the missing value; record zero only if verified, then import the corrected report.'
            elif n < 0 or d < 0:
                excluded += 1
                negative += 1
                reason = 'A recorded count is negative'
                action = 'Compare the counts with the source register. Correct any entry or import error and re-import the report.'
            elif d == 0:
                excluded += 1
                zero_denominator += 1
                if n == 0:
                    reason = 'Newborn Alive is zero; a percentage cannot be calculated'
                    action = 'Confirm that no live births occurred. If both counts are correct, leave the percentage unavailable; no correction is needed.'
                else:
                    reason = f'{short_name} is recorded, but Newborn Alive is zero'
                    action = 'Check the live-birth count and whether the indicator includes referred or outborn babies. Correct confirmed errors and re-import.'
            else:
                numerator += n
                denominator += d
                matched += 1
                included = True
                if n > d:
                    above += 1
                    reason = f'{short_name} count exceeds Newborn Alive'
                    action = 'Compare both counts with the source register. Check duplicate entries and whether both counts cover the same babies. Correct confirmed errors and re-import.'
            if reason:
                period = str(periodcode)
                period_label = (f'{month_name[int(period[4:])]} {period[:4]}'
                                if len(period) == 6 and period.isdigit() and 1 <= int(period[4:]) <= 12 else period)
                issues.append(dict(facility=facility, periodcode=period, period=period_label,
                    numerator=n, denominator=d,
                    numerator_display=f'{n:,.0f}' if n is not None else 'Not recorded',
                    denominator_display=f'{d:,.0f}' if d is not None else 'Not recorded',
                    reason=reason, action=action, included=included,
                    calculation_status='Included — count review required' if included else 'Not used in this percentage'))
        rate = (numerator / denominator * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if matched else None
        messages = []
        if not matched:
            messages.append('No percentage available')
        if excluded:
            unit = 'facility-month' if excluded == 1 else 'facility-months'
            messages.append(f'{excluded} {unit} not used — check missing, zero or invalid counts')
        if above:
            unit = 'facility-month' if above == 1 else 'facility-months'
            messages.append(f'{above} {unit} needs count review')
        if not pairs:
            messages.append('Check whether the newborn indicators were imported for this selection')
        result.append(dict(code=code, label=label,
            numerator=numerator if matched else None, denominator=denominator if matched else None,
            rate=rate, rate_display=f'{rate:.2f}%' if rate is not None else '—',
            numerator_display=f'{numerator:,.0f}' if matched else '—',
            denominator_display=f'{denominator:,.0f}' if matched else '—',
            matched=matched, excluded=excluded, above=above,
            missing_numerator=missing_numerator, missing_denominator=missing_denominator,
            zero_denominator=zero_denominator, negative=negative,
            issues=issues, issue_count=len(issues),
            status='; '.join(messages) or 'No issues detected in matched records',
            warning=bool(issues)))
    return result


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
        # Use actual fact codes for every indicator; preserve old summary URLs.
        indicators = list(dict.fromkeys(
            SUMMARY_CODES.get(value.strip(), value.strip())
            for value in request.GET.getlist('indicator')
            if value.strip() and len(value.strip()) <= 128))
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
            queryset = queryset.filter(indicator_code__in=filters['indicator'])
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

    def _indicator_catalogue(self, queryset):
        """All recorded fact indicators, including zero values and future additions."""
        records = list(queryset.order_by().exclude(indicator_code='')
                       .filter(value__isnull=False).values('indicator_code')
                       .annotate(recorded_name=Max('indicator_name')))
        codes = [record['indicator_code'] for record in records]
        metadata = {}
        for item in IndicatorMetadata.objects.filter(indicator_code__in=codes).order_by(
                '-is_active', 'sort_order', 'indicator_name'):
            metadata.setdefault(item.indicator_code, item)
        options = []
        for record in records:
            code = record['indicator_code']
            item = metadata.get(code)
            label = (item.indicator_name if item and item.indicator_name else
                     record['recorded_name'] or code)
            order = item.sort_order if item and item.sort_order is not None else 1_000_000
            options.append((order, label.casefold(), code, label))
        options.sort(key=lambda item: (item[0], item[1], item[2]))
        return [(code, label) for _order, _sort_label, code, label in options]

    def _indicator_options(self, filters):
        # Apply location/date scope, but never restrict by the selected indicators.
        return self._indicator_catalogue(
            self._filter_queryset(HMISFact.objects.all(), filters))

    def _selection_labels(self, filters):
        labels = dict(self._indicator_catalogue(HMISFact.objects.filter(
            indicator_code__in=filters['indicator'])))
        return [labels.get(code, code) for code in filters['indicator']]

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

    def _composite_data(self, filters):
        codes = [code for code, _label in COMPOSITE_INDICATORS] + [LIVE_BIRTH_CODE]
        facts = self._filter_queryset(HMISFact.objects.all(), filters).filter(indicator_code__in=codes)
        grouped = facts.order_by().values('hf', 'periodcode', 'indicator_code').annotate(
            total=Sum('value'), nonblank=Count('value'))
        pairs = {}
        monthly_pairs = {}
        for record in grouped.iterator(chunk_size=2000):
            key = (record['hf'], record['periodcode'])
            value = record['total'] if record['nonblank'] else None
            pairs.setdefault(key, {})[record['indicator_code']] = value
            monthly_pairs.setdefault(record['periodcode'], {}).setdefault(key, {})[record['indicator_code']] = value
        monthly = []
        for period in sorted(monthly_pairs):
            for row in calculate_composites(monthly_pairs[period]):
                monthly.append(dict(row, periodcode=period, period=self._period_label(period)))
        return dict(rows=calculate_composites(pairs), monthly=monthly, note=COMPOSITE_NOTE)

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

    def _multi_excel(self, facts, filters, reporting, composite):
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
                values = self._selection_labels(filters)
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
        composite_sheet = workbook.create_sheet('Composite Indicators')
        headers = ('Scope', 'Indicator', 'Numerator', 'Newborn Alive (matched)', 'Rate (%)',
                   'Matched Facility-Months', 'Excluded Facility-Months', 'Status')
        self._msh_header(composite_sheet, headers, (24,44,18,26,18,26,26,65))
        for row in composite['rows']:
            composite_sheet.append([self._excel_text(x) for x in (
                'Selected period', row['label'], row['numerator'], row['denominator'], row['rate'],
                row['matched'], row['excluded'], row['status'])])
        for row in composite['monthly']:
            composite_sheet.append([self._excel_text(x) for x in (
                row['period'], row['label'], row['numerator'], row['denominator'], row['rate'],
                row['matched'], row['excluded'], row['status'])])
        composite_sheet.append([])
        composite_sheet.append(['Calculation', COMPOSITE_NOTE])
        checks = workbook.create_sheet('Composite Data Checks')
        self._msh_header(checks,
            ('Indicator', 'Facility', 'Month', 'Indicator Count', 'Newborn Alive',
             'Issue', 'Suggested Action', 'Calculation Treatment'),
            (38,42,24,20,20,65,90,38))
        for row in composite['rows']:
            for issue in row['issues']:
                checks.append([self._excel_text(value) for value in (
                    row['label'], issue['facility'], issue['period'], issue['numerator'],
                    issue['denominator'], issue['reason'], issue['action'], issue['calculation_status'])])
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
        composite = self._composite_data(filters)
        if request.GET.get('export') == 'xlsx':
            if facts.count() > self._filtered_excel_row_limit():
                self.message_user(request, 'Please narrow the filters: the Excel detail row limit was exceeded.', level=messages.WARNING)
                params = request.GET.copy()
                params.pop('export', None)
                return HttpResponseRedirect(request.path + '?' + params.urlencode())
            return self._multi_excel(facts, filters, reporting, composite)
        first = filters['indicator'][0] if filters['indicator'] else 'anc1'
        summary_field = next((field for field, code in SUMMARY_CODES.items() if code == first), 'anc1')
        data = self._build_dashboard_data(summaries, summary_field)
        data['selected_indicator_label'] = ', '.join(self._selection_labels(filters)) or 'All HMIS indicators'
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
                   'composite': composite,
                   'export_url': '?' + export_params.urlencode(), 'print_url': '?' + print_params.urlencode(),
                   'excel_export_limit_display': f'{self._filtered_excel_row_limit():,}',
                   'print_all_mode': for_print}
        if extra_context:
            context.update(extra_context)
        request.current_app = self.admin_site.name
        return TemplateResponse(request, self.change_list_template, context)
