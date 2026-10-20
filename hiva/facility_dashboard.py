"""Read-only facility dashboard; queryset and permissions belong to FacilityAdmin."""
from collections import Counter
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse

CATEGORIES = (
    ('afiat', 'AFIAT'), ('skilllab', 'Skill Lab'), ('aim', 'AIM'),
    ('safesurgery', 'Safe Surgery'), ('ganc', 'G-ANC / G-PNC'),
    ('nbcc', 'NBCC'), ('sncu', 'SNCU'), ('kmc', 'KMC'),
)


def coordinate_status(facility):
    if facility.latitude is None or facility.longitude is None:
        return 'Missing coordinates', None
    try:
        lat, lon = Decimal(str(facility.latitude)), Decimal(str(facility.longitude))
        if not lat.is_finite() or not lon.is_finite() or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return 'Invalid coordinates', None
        # Screening bounds only: not an administrative boundary test.
        if not (29 <= lat <= 39 and 60 <= lon <= 75):
            return 'Outside Afghanistan screening bounds', None
        return 'Mapped', [float(lat), float(lon)]
    except (InvalidOperation, ValueError, TypeError):
        return 'Invalid coordinates', None


def state(value):
    return 'Yes' if value is True else 'No' if value is False else 'Not recorded'


class FacilityDashboardMixin:
    change_list_template = 'admin/hiva/facility/change_list.html'

    def get_urls(self):
        info = self.model._meta
        return [path('dashboard/', self.admin_site.admin_view(self.facility_dashboard),
                     name=f'{info.app_label}_{info.model_name}_dashboard')] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        info = self.model._meta
        context = dict(extra_context or {})
        context['facility_dashboard_url'] = reverse(
            f'{self.admin_site.name}:{info.app_label}_{info.model_name}_dashboard')
        return super().changelist_view(request, extra_context=context)

    def facility_dashboard(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        # Includes the existing ProvinceRestrictedAdminMixin; no direct global query.
        base = self.get_queryset(request).select_related('districtfk__provincefk', 'facilitytypefk')
        # Exactly one intervention at a time; obsolete multi-select parameters are ignored.
        intervention = request.GET.get('intervention', 'all')
        labels = dict(CATEGORIES)
        if intervention != 'all' and intervention not in labels:
            raise SuspiciousOperation('Invalid intervention')
        from django.db.models import Count, Q
        aggregate = base.aggregate(total=Count('pk'), **{
            key: Count('pk', filter=Q(**{key: True})) for key, _ in CATEGORIES
        })
        tabs = [{'key': 'all', 'label': 'All facilities', 'count': aggregate['total'],
                 'active': intervention == 'all', 'url': '?intervention=all'}]
        tabs += [{'key': key, 'label': label, 'count': aggregate[key],
                  'active': intervention == key, 'url': '?intervention=' + key}
                 for key, label in CATEGORIES]
        selected_label = labels.get(intervention, 'All facilities')
        selected = base if intervention == 'all' else base.filter(**{intervention: True})
        rows, markers = [], []
        counts = Counter()
        totals = {key: Counter() for key, _ in CATEGORIES}
        provinces, types = Counter(), Counter()
        for f in selected.order_by('districtfk__provincefk__name', 'name'):
            status, coords = coordinate_status(f)
            counts[status] += 1
            province = f.districtfk.provincefk.name
            provinces[province] += 1
            types[str(f.facilitytypefk)] += 1
            flags = {key: state(getattr(f, key)) for key, _ in CATEGORIES}
            for key, val in flags.items():
                totals[key][val] += 1
            row = {'id': f.pk, 'name': f.name, 'code': f.hfcode, 'province': province,
                   'district': f.districtfk.name, 'type': str(f.facilitytypefk),
                   'selectionphase': f.selectionphase, 'aimphase': f.aimphase,
                   'latitude': str(f.latitude) if f.latitude is not None else '',
                   'longitude': str(f.longitude) if f.longitude is not None else '',
                   'status': status, 'flags': flags, 'states': list(flags.values())}
            rows.append(row)
            if coords:
                markers.append({**row, 'coordinates': coords})
        total = len(rows)
        summary = [{'label': label, 'yes': totals[key]['Yes'], 'no': totals[key]['No'],
                    'unknown': totals[key]['Not recorded'],
                    'percent': round(totals[key]['Yes'] * 100 / total, 1) if total else None}
                   for key, label in CATEGORIES]
        if request.GET.get('export') == 'csv':
            import csv
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="hiva_facilities_filtered.csv"'
            response.write('\ufeff')
            writer = csv.writer(response)
            writer.writerow(['ID', 'Facility', 'HF code', 'Province', 'District', 'Facility type',
                             'Selection phase', 'AIM phase', 'Latitude', 'Longitude', 'Map status'] + [label for _, label in CATEGORIES])
            for row in rows:
                values = [row[k] for k in ('id', 'name', 'code', 'province', 'district', 'type',
                                           'selectionphase', 'aimphase', 'latitude', 'longitude', 'status')] + row['states']
                # Prevent spreadsheet formula evaluation of user-entered text.
                writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
            return response
        info = self.model._meta
        from urllib.parse import urlencode
        export_query = urlencode({'intervention': intervention, 'export': 'csv'})
        context = {**self.admin_site.each_context(request), 'title': 'Health Facility Dashboard',
                   'opts': info, 'tabs': tabs, 'intervention': intervention,
                   'map_only': request.GET.get('view') == 'map',
                   'dashboard_base': ('admin/hiva/facility_map_base.html' if request.GET.get('view') == 'map' else 'admin/base_site.html'),
                   'full_map_url': '?' + urlencode({'intervention': intervention, 'view': 'map'}),
                   'dashboard_url': '?' + urlencode({'intervention': intervention}),
                   'selected_label': selected_label, 'rows': rows, 'markers': markers,
                   'summary': summary, 'total': total, 'mapped': counts['Mapped'],
                   'unmapped': total - counts['Mapped'], 'province_count': len(provinces),
                   'provinces': sorted(provinces.items()), 'types': sorted(types.items()),
                   'categories': [label for _, label in CATEGORIES], 'category_pairs': CATEGORIES,
                   'export_url': '?' + export_query,
                   'facility_list_url': reverse(f'{self.admin_site.name}:{info.app_label}_{info.model_name}_changelist')}
        return TemplateResponse(request, 'admin/hiva/facility_dashboard.html', context)
