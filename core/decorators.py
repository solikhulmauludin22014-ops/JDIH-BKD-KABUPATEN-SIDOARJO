from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


def admin_login_required(view_func):
    """
    Decorator to protect admin panel views.
    Ensures that request.session contains a valid 'admin_user' verified from Firebase.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        admin_user = request.session.get('admin_user')
        if not admin_user or not admin_user.get('uid'):
            messages.warning(request, "Silakan login terlebih dahulu untuk mengakses Panel Admin.")
            login_url = reverse('admin_panel:login')
            next_url = request.get_full_path()
            return redirect(f"{login_url}?next={next_url}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
