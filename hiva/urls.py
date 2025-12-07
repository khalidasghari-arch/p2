from django.urls import path
from . import views

urlpatterns = [
    path('display-tables/', views.display_tables, name='display_tables'),
]