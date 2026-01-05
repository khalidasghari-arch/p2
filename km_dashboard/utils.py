# km_dashboard/utils.py
def user_province(request):
    if request.user.is_superuser:
        return None
    if hasattr(request.user, "profile") and getattr(request.user.profile, "province", None):
        return request.user.profile.province
    return None
