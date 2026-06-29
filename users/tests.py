from django.http import HttpResponse

def test_qr_url(request):
    """Test view to see the QR URL"""
    if request.user.is_authenticated:
        profile = request.user.profile
        token = profile.qr_code_token
        return HttpResponse(f"""
            <h1>Your QR URL:</h1>
            <p><a href="/users/qr/{token}/">/users/qr/{token}/</a></p>
            <p>Full URL: https://6b4d-217-199-148-239.ngrok-free.app/users/qr/{token}/</p>
        """)
    return HttpResponse("Please login first")