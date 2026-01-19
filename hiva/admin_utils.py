# hiva/admin_utils.py

def user_province(request):
    if request.user.is_superuser:
        return None
    profile = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
    return getattr(profile, "province", None)

class ProvinceRestrictedAdminMixin:
    """
    Universal restriction for province-based access.
    Subclasses must define:
      - province_filter_kwargs(request)
    Optional:
      - approved_status_value (default "approved")
      - status_field_name (default "status") -> only enforced if exists
    """

    approved_status_value = "approved"
    status_field_name = "status"

    def province_filter_kwargs(self, request):
        raise NotImplementedError

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        prov = user_province(request)

        # superuser -> all
        if request.user.is_superuser:
            return qs

        # no province -> see nothing (safer)
        if prov is None:
            return qs.none()

        return qs.filter(**self.province_filter_kwargs(request))

    def _obj_in_scope(self, request, obj):
        return self.get_queryset(request).filter(pk=obj.pk).exists()

    def has_view_permission(self, request, obj=None):
        base = super().has_view_permission(request, obj=obj)
        if not base:
            return False
        if obj is None or request.user.is_superuser:
            return True
        return self._obj_in_scope(request, obj)

    def has_change_permission(self, request, obj=None):
        base = super().has_change_permission(request, obj=obj)
        if not base:
            return False
        if obj is None or request.user.is_superuser:
            return True

        # province restriction
        if not self._obj_in_scope(request, obj):
            return False

        # approved lock only if the model actually has a status field
        if hasattr(obj, self.status_field_name):
            if getattr(obj, self.status_field_name) == self.approved_status_value:
                return False

        return True

    def has_delete_permission(self, request, obj=None):
        base = super().has_delete_permission(request, obj=obj)
        if not base:
            return False
        if obj is None or request.user.is_superuser:
            return True
        return self._obj_in_scope(request, obj)
