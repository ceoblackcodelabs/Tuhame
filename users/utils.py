# apps/users/utils.py
import qrcode
from io import BytesIO
import base64
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_qr_code_for_url(url, fill_color="#1E3A8A"):
    """
    Generate a QR code data-URI for an arbitrary absolute URL. Used for the
    owner/mover portfolio "business card" QR codes as well as the tenant
    digital ID QR.
    """
    try:
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        logger.warning("QR generation error for url %s: %s", url, e)
        return None


def generate_qr_code_for_user(user_profile):
    """
    Generate a QR code for a user profile with a public URL
    """
    try:
        token = user_profile.qr_code_token

        # Build the full URL from SITE_URL (always set - see settings.py)
        base_url = settings.SITE_URL.rstrip('/')

        # Use the shorter QR URL pattern
        qr_url = f"{base_url}/users/qr/{token}/"

        return generate_qr_code_for_url(qr_url)
    except Exception as e:
        logger.warning("QR generation error for profile %s: %s", getattr(user_profile, 'pk', '?'), e)
        return None