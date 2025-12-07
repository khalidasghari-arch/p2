from django.shortcuts import render
from hiva.models import Mpdsr
from django.db.models import Sum

def map_dashboard(request):
    data = Mpdsr.objects.values('facilityname__districtfk__provincefk__name').annotate(
        total=Sum('n_maternaldeathreported')
    )
    deaths_by_province = {d['facilityname__districtfk__provincefk__name']: d['total'] for d in data}
    return render(request, 'dashboard/map.html', {'deaths_json': deaths_by_province})
