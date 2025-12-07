from django.shortcuts import render
from django.db.models import Sum
from fuzzywuzzy import process
from hiva.models import Province, Mpdsr
import json

def map_dashboard(request):
    # Load GeoJSON province names
    with open('dashboard/static/geojson/afghanistan_provinces.geojson', encoding='utf-8') as f:
        geojson = json.load(f)

    geojson_names = [f["properties"]["PROV_NA_EN"].strip() for f in geojson["features"]]  # Adjust key if needed

    # Get province names from your DB
    db_provinces = Province.objects.values_list('name', flat=True).distinct()

    # Fuzzy match DB names to GeoJSON
    name_map = {}
    for db_name in db_provinces:
        match, score = process.extractOne(db_name, geojson_names)
        name_map[db_name] = match if score >= 80 else None
        print(f"Matched: {db_name} → {match} (Score: {score})")

    # Aggregate maternal deaths from Mpdsr
    data = Mpdsr.objects.values('facilityname__districtfk__provincefk__name').annotate(
        total=Sum('n_maternaldeathreported')
    )

    # Use matched names to build deaths dictionary
    deaths_by_geojson_name = {}
    for d in data:
        db_name = d['facilityname__districtfk__provincefk__name']
        geojson_name = name_map.get(db_name)
        if geojson_name:
            deaths_by_geojson_name[geojson_name.lower()] = d['total']

    # Render map template
    return render(request, 'dashboard/map.html', {
        'deaths_json': deaths_by_geojson_name
    })