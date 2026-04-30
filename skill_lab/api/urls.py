from django.urls import path

from . import views

app_name = "skilllab_api"

urlpatterns = [
    path("summary/", views.dashboard_summary, name="dashboard_summary"),
    path("sessions-by-province/", views.sessions_by_province, name="sessions_by_province"),
    path("sessions-by-month/", views.sessions_by_month, name="sessions_by_month"),
    path("sessions-by-skill-lab/", views.sessions_by_skill_lab, name="sessions_by_skill_lab"),
    path("ls-mc-by-thematic-area/", views.ls_mc_by_thematic_area, name="ls_mc_by_thematic_area"),
    path("competency-status/", views.competency_status, name="competency_status"),
    path("mentees-by-profession/", views.mentees_by_profession, name="mentees_by_profession"),
    path("topic-coverage/", views.topic_coverage, name="topic_coverage"),
]