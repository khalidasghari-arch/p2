from django.urls import path
from .views import map_dashboard

urlpatterns = [
    path('maternal-map/', map_dashboard, name='maternal-map'),
]
