# apps/users/utils.py
import qrcode
from io import BytesIO
import base64
from django.conf import settings


def generate_qr_code_for_user(user_profile):
    """
    Generate a QR code for a user profile with a public URL
    """
    try:
        token = user_profile.qr_code_token

        # Build the full URL
        if hasattr(settings, 'SITE_URL') and settings.SITE_URL:
            base_url = settings.SITE_URL
        else:
            base_url = "https://6b4d-217-199-148-239.ngrok-free.app"

        # Use the shorter QR URL pattern
        qr_url = f"{base_url}/users/qr/{token}/"

        print(f"QR URL: {qr_url}")  # Debug print

        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#1E3A8A", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        print(f"QR generation error: {e}")
        return None