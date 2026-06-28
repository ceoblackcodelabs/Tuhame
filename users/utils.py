# apps/users/utils.py
import qrcode
from io import BytesIO
import base64
from django.conf import settings
from django.urls import reverse


def generate_qr_code_for_user(user_profile):
    """
    Generate a QR code for a user profile with a URL
    """
    try:
        # Build the URL for the public profile
        # Using the QR token from the profile
        token = user_profile.qr_code_token

        # Build the full URL
        # If you have a domain set in settings, use it, otherwise use relative path
        if hasattr(settings, 'SITE_URL'):
            base_url = settings.SITE_URL
        else:
            # Fallback to relative URL
            base_url = ""

        # Create the full URL
        qr_url = f"{base_url}/users/profile/{token}/"

        # If you want to use a shorter URL or different format
        # qr_url = f"{base_url}/qr/{token}/"

        print(f"QR URL: {qr_url}")  # Debug print

        # Generate QR code with the URL
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)  # Add URL instead of text
        qr.make(fit=True)

        img = qr.make_image(fill_color="#1E3A8A", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        print(f"QR generation error: {e}")
        return None