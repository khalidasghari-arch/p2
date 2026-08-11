from django.conf import settings
from django.contrib import admin


_original_get_app_list = admin.AdminSite.get_app_list


def custom_get_app_list(self, request, app_label=None):
    app_list = _original_get_app_list(
        self,
        request,
        app_label,
    )

    hidden_apps = getattr(
        settings,
        "ADMIN_HIDDEN_APPS",
        [],
    )

    return [
        app
        for app in app_list
        if app.get("app_label") not in hidden_apps
    ]


admin.AdminSite.get_app_list = custom_get_app_list