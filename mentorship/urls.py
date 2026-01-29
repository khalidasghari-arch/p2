# mentorship/urls.py

from django.urls import path
from .views import topics_by_thematic

app_name = "mentorship"

urlpatterns = [
    path("ajax/topics-by-thematic/", topics_by_thematic, name="topics_by_thematic"),
]
