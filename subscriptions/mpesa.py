"""
M-Pesa Daraja (STK Push) for subscription payments only.

Credentials are read from .env via decouple at call time - never cached,
never hardcoded, so a missing value fails loudly into the payment's own
failure path (SubscriptionPayment.mark_failed) instead of silently
proceeding with an empty string. Required vars (see DEPLOY.md):

  CONSUMER_KEY, CONSUMER_SECRET, PASSKEY, BUSINESS_SHORT_CODE,
  TILL_NUMBER, MPESA_ENVIRONMENT (sandbox|production), SITE_URL
  (already used elsewhere in the app - re-used here to build the callback
  URL rather than adding a second, easy-to-forget MPESA_CALLBACK_URL var).
"""
import base64
import logging
from datetime import datetime

import requests
from decouple import config
from requests.auth import HTTPBasicAuth
from django.urls import reverse

logger = logging.getLogger('mpesa')


def get_access_token():
    """OAuth token from Safaricom. Returns the token string, or None on
    any failure -- never raises."""
    try:
        consumer_key = config('CONSUMER_KEY', default='')
        consumer_secret = config('CONSUMER_SECRET', default='')
        environment = config('MPESA_ENVIRONMENT', default='sandbox').strip().lower()

        if not consumer_key or not consumer_secret:
            logger.error("M-Pesa consumer credentials not configured")
            return None

        url = (
            "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
            if environment == "sandbox"
            else "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        )
        response = requests.get(url, auth=HTTPBasicAuth(consumer_key, consumer_secret), timeout=30)

        if response.status_code == 200:
            return response.json().get('access_token')

        logger.error("Failed to get M-Pesa token: HTTP %s", response.status_code)
        return None
    except Exception as e:
        logger.error("Error getting M-Pesa access token: %s", str(e))
        return None


def initiate_subscription_stk_push(payment):
    """STK push for a SubscriptionPayment. Never raises -- the calling
    view always gets a clean True/False, with the reason recorded on
    `payment` itself via mark_failed()."""
    try:
        business_short_code = config('BUSINESS_SHORT_CODE', default='')
        till_number = config('TILL_NUMBER', default='')
        passkey = config('PASSKEY', default='')
        site_url = config('SITE_URL', default='')
        environment = config('MPESA_ENVIRONMENT', default='sandbox').strip().lower()

        if not passkey or not business_short_code:
            logger.error("M-Pesa credentials not configured")
            payment.mark_failed(999, "M-Pesa credentials not configured")
            return False

        if not site_url:
            logger.error("SITE_URL not configured - needed to build the M-Pesa callback URL")
            payment.mark_failed(999, "Callback URL not configured")
            return False

        access_token = get_access_token()
        if not access_token:
            payment.mark_failed(999, "Failed to get access token")
            return False

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{business_short_code}{passkey}{timestamp}".encode()
        ).decode()

        url = (
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
            if environment == "sandbox"
            else "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        )
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "BusinessShortCode": business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            # Till number -> CustomerBuyGoodsOnline. If this project ever
            # moves to a paybill instead, switch to CustomerPayBillOnline
            # and drop PartyB back to business_short_code.
            "TransactionType": "CustomerBuyGoodsOnline",
            "Amount": int(payment.amount),
            "PartyA": payment.phone_number,
            "PartyB": till_number or business_short_code,
            "PhoneNumber": payment.phone_number,
            "CallBackURL": f"{site_url.rstrip('/')}{reverse('subscriptions:subscription_callback')}",
            "AccountReference": f"SUB{payment.id}",
            "TransactionDesc": f"{payment.plan.name} subscription"[:100],
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if data.get('ResponseCode') == '0':
                payment.merchant_request_id = data.get('MerchantRequestID')
                payment.checkout_request_id = data.get('CheckoutRequestID')
                payment.save(update_fields=['merchant_request_id', 'checkout_request_id'])
                return True
            error_desc = data.get('ResponseDescription', 'Unknown error')
            logger.error("STK push rejected (200 but ResponseCode != 0): %s", data)
            payment.mark_failed(data.get('ResponseCode'), error_desc)
            return False

        # Non-200 from Safaricom's gateway. This is almost always their
        # Apigee error envelope: {"requestId": "...", "errorCode": "...",
        # "errorMessage": "..."} - NOT a ResponseDescription. Parse it
        # properly instead of chopping the raw text at an arbitrary length,
        # which previously hid the one field (errorMessage) that actually
        # explains what's wrong.
        logger.error("STK push HTTP %s: %s", response.status_code, response.text[:2000])
        try:
            err = response.json()
            error_code = err.get('errorCode', str(response.status_code))
            error_message = err.get('errorMessage', response.text[:300])
        except ValueError:
            error_code = response.status_code
            error_message = response.text[:300]
        payment.mark_failed(error_code, f"HTTP {response.status_code}: {error_message}")
        return False

    except Exception as e:
        logger.error("STK push error: %s", str(e))
        payment.mark_failed(999, str(e))
        return False