from django.http import HttpResponse
from django.conf import settings

def test_qr_url(request):
    """Test view to see the QR URL"""
    if request.user.is_authenticated:
        from .models import Profile
        profile, _ = Profile.objects.get_or_create(user=request.user)
        token = profile.qr_code_token
        base_url = settings.SITE_URL.rstrip('/')
        return HttpResponse(f"""
            <h1>Your QR URL:</h1>
            <p><a href="/users/qr/{token}/">/users/qr/{token}/</a></p>
            <p>Full URL: {base_url}/users/qr/{token}/</p>
        """)
    return HttpResponse("Please login first")