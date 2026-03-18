# mentorship/urls.py
from django.urls import path
from .views import topics_by_thematic
from .api_views import MentorshipVisitFullAPI

app_name = "mentorship"

urlpatterns = [
    path("ajax/topics-by-thematic/", topics_by_thematic, name="topics_by_thematic"),
     path("mentorship-data/", MentorshipVisitFullAPI.as_view(), name="mentorship-data"),
]
