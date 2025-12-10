# kms/views.py
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.shortcuts import render
from .models import KnowledgeItem

def search(request):
    q = request.GET.get("q", "")
    results = []
    if q:
        query = SearchQuery(q)
        qs = KnowledgeItem.objects.annotate(
            rank=SearchRank(models.F("search_vector"), query)
        ).filter(search_vector=query).order_by("-rank")
        results = qs
    return render(request, "kms/search.html", {"query": q, "results": results})

# Create your views here.
