def user_province(request):
    """
    Returns Province for normal users.
    Returns None for superuser (means unrestricted).
    """
    if request.user.is_superuser:
        return None

    profile = getattr(request.user, "profile", None)
    return getattr(profile, "province", None)
