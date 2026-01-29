# mentorship/views.py

from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import MentorshipTopics

@staff_member_required
def topics_by_thematic(request):
    thematic_id = request.GET.get("thematic_id")
    if not thematic_id:
        return JsonResponse({"results": []})

    qs = MentorshipTopics.objects.filter(
        thematicfk_id=thematic_id
    ).order_by("shortname", "name")

    results = []
    for t in qs:
        label = f"{t.shortname} - {t.name}" if t.shortname else t.name
        results.append({"id": t.id, "label": label})

    return JsonResponse({"results": results})
