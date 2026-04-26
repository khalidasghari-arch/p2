from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path("", lambda request: redirect("admin/")),
    path("admin/", admin.site.urls),
    path("km/", include("km_dashboard.urls", namespace="km_dashboard")),
    path("mentorship/", include("mentorship.urls")),
    # path("product/", include("product.urls")),
    path("api/mentorship/", include(("mentorship.urls", "mentorship"), namespace="mentorship_api")),
    #path("dashboard/", include("dashboard.urls")),
    #path("", include("hiva.urls")),   # if you have app urls
    # path("", include("survey.urls")), # if you have
    path('api/product/', include('product.api.urls')),  # Add this line
    # path('hiva/', include('hiva.urls')),  # Add this line
    # path('', include('authentication.urls')),  # Add this line
    # path('dashboard/', include('dashboard.urls')),  # 🔗 dashboard URLs
    path("api/qqm/", include("qqm.api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



