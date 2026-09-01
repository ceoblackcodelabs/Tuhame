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

Every attempt - request built, response received, result applied - is
logged to the 'mpesa' logger at INFO level (see LOGGING in settings.py,
which writes it to mpesa.log). This is a money-handling flow: nothing
here should ever happen silently. Only the access token itself and raw
credentials are kept out of the logs; everything else (amounts, phone
numbers, checkout IDs, response bodies, result codes) is logged in full
so a disputed transaction can always be traced end to end.
"""
import base64
import logging
from datetime import datetime

import requests
from decouple import config
from requests.auth import HTTPBasicAuth
from django.urls import reverse

logger = logging.getLogger('mpesa')


def _safe_int(value):
    """result_code is an IntegerField, but Safaricom sends two different
    kinds of codes into this same code path: numeric STK ResultCodes (0,
    1032, 2001...) and dotted Apigee gateway error codes ("400.002.02").
    Only the former fits the column - anything else (including None)
    saves as NULL instead of crashing the failure-handling path itself."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _environment():
    return config('MPESA_ENVIRONMENT', default='sandbox').strip().lower()


def _base_url():
    return (
        "https://sandbox.safaricom.co.ke"
        if _environment() == "sandbox"
        else "https://api.safaricom.co.ke"
    )


def get_access_token():
    """OAuth token from Safaricom. Returns the token string, or None on
    any failure -- never raises."""
    try:
        consumer_key = config('CONSUMER_KEY', default='')
        consumer_secret = config('CONSUMER_SECRET', default='')

        if not consumer_key or not consumer_secret:
            logger.error("M-Pesa consumer credentials not configured")
            return None

        url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(url, auth=HTTPBasicAuth(consumer_key, consumer_secret), timeout=30)

        if response.status_code == 200:
            logger.info("M-Pesa access token obtained (env=%s)", _environment())
            return response.json().get('access_token')

        logger.error("Failed to get M-Pesa token: HTTP %s: %s", response.status_code, response.text[:500])
        return None
    except Exception as e:
        logger.error("Error getting M-Pesa access token: %s", str(e))
        return None


def build_callback_url():
    """Returns (callback_url, error_message). error_message is None on
    success. Centralised so both the push and any future re-validation
    (e.g. an admin 'test my callback URL' button) use the exact same
    logic and can never drift apart."""
    site_url = config('SITE_URL', default='')
    if not site_url:
        return None, "SITE_URL not configured - needed to build the M-Pesa callback URL"

    callback_url = f"{site_url.rstrip('/')}{reverse('subscriptions:subscription_callback')}"
    if not callback_url.startswith('https://'):
        # Safaricom rejects this outright with "Invalid CallBackURL" - fail
        # fast locally with a message that actually says why, instead of
        # burning an API round-trip to find out. The usual cause: SITE_URL
        # is missing/wrong in .env on this specific server (or an OS-level
        # environment variable is silently overriding the .env file -
        # decouple checks os.environ FIRST, before the .env file).
        return None, (
            f"SITE_URL must be a public HTTPS URL for M-Pesa callbacks "
            f"(currently resolves to: {callback_url})"
        )
    return callback_url, None


def initiate_subscription_stk_push(payment):
    """STK push for a SubscriptionPayment. Never raises -- the calling
    view always gets a clean True/False, with the reason recorded on
    `payment` itself via mark_failed()."""
    logger.info(
        "STK push initiate: payment=%s user=%s plan=%s amount=%s phone=%s env=%s",
        payment.id, payment.user_id, payment.plan_id, payment.amount, payment.phone_number, _environment(),
    )
    try:
        business_short_code = config('BUSINESS_SHORT_CODE', default='')
        till_number = config('TILL_NUMBER', default='')
        passkey = config('PASSKEY', default='')

        if not passkey or not business_short_code:
            logger.error("payment=%s: M-Pesa credentials not configured", payment.id)
            payment.mark_failed(None, "M-Pesa credentials not configured")
            return False

        callback_url, err = build_callback_url()
        if err:
            logger.error("payment=%s: %s", payment.id, err)
            payment.mark_failed(None, err)
            return False
        logger.info("payment=%s: callback URL resolved to %s", payment.id, callback_url)

        access_token = get_access_token()
        if not access_token:
            payment.mark_failed(None, "Failed to get access token")
            return False

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{business_short_code}{passkey}{timestamp}".encode()
        ).decode()

        url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"
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
            "CallBackURL": callback_url,
            "AccountReference": f"SUB{payment.id}",
            "TransactionDesc": f"{payment.plan.name} subscription"[:100],
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        logger.info("payment=%s: STK push HTTP %s: %s", payment.id, response.status_code, response.text[:1000])

        if response.status_code == 200:
            data = response.json()
            if data.get('ResponseCode') == '0':
                payment.merchant_request_id = data.get('MerchantRequestID')
                payment.checkout_request_id = data.get('CheckoutRequestID')
                payment.save(update_fields=['merchant_request_id', 'checkout_request_id'])
                logger.info(
                    "payment=%s: STK push accepted, checkout_request_id=%s",
                    payment.id, payment.checkout_request_id,
                )
                return True
            error_desc = data.get('ResponseDescription', 'Unknown error')
            logger.error("payment=%s: STK push rejected (200 but ResponseCode != 0): %s", payment.id, data)
            payment.mark_failed(_safe_int(data.get('ResponseCode')), error_desc)
            return False

        # Non-200 from Safaricom's gateway. This is almost always their
        # Apigee error envelope: {"requestId": "...", "errorCode": "...",
        # "errorMessage": "..."} - NOT a ResponseDescription. Parse it
        # properly instead of chopping the raw text at an arbitrary length,
        # which previously hid the one field (errorMessage) that actually
        # explains what's wrong.
        try:
            err = response.json()
            error_code = err.get('errorCode', str(response.status_code))
            error_message = err.get('errorMessage', response.text[:300])
        except ValueError:
            error_code = response.status_code
            error_message = response.text[:300]
        # error_code from this envelope is often a dotted string like
        # "400.002.02", not a number - result_code is an IntegerField, so
        # keep the code in the text (result_desc) and only pass a number
        # (or nothing) to result_code itself. A crash here would leave the
        # payment stuck instead of cleanly marked failed.
        payment.mark_failed(
            _safe_int(error_code), f"[{error_code}] HTTP {response.status_code}: {error_message}",
        )
        return False

    except Exception as e:
        logger.error("payment=%s: STK push error: %s", payment.id, str(e))
        payment.mark_failed(None, str(e))
        return False


# ---------------------------------------------------------------------------
# Result interpretation - shared by the Safaricom callback (views.py) and
# the query-based reconciliation below, so the two can never disagree
# about what a given ResultCode means.
# ---------------------------------------------------------------------------

def apply_result_code(payment, result_code, result_desc, callback_data=None, source='callback'):
    """Applies a Safaricom ResultCode to `payment`. Idempotent: does
    nothing if payment is no longer pending, since Safaricom retries
    callbacks and the query API can be polled repeatedly - this must be
    safe to call more than once for the same payment without double
    -applying (e.g. double-extending a subscription)."""
    payment.refresh_from_db()
    if payment.status != payment.STATUS_PENDING:
        logger.info(
            "payment=%s: %s result_code=%s ignored, already %s",
            payment.id, source, result_code, payment.status,
        )
        return payment.status

    logger.info(
        "payment=%s: applying %s result_code=%s result_desc=%r",
        payment.id, source, result_code, result_desc,
    )

    if result_code == 0:
        items = (callback_data or {}).get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [])
        receipt = next((i.get('Value') for i in items if i.get('Name') == 'MpesaReceiptNumber'), None)
        if receipt:
            payment.mark_completed(receipt_number=receipt, callback_data=callback_data)
            logger.info("payment=%s: COMPLETED, receipt=%s", payment.id, receipt)
            return payment.STATUS_COMPLETED
        payment.mark_failed(999, "Missing receipt", callback_data)
        logger.error("payment=%s: ResultCode 0 but no receipt in payload", payment.id)
        return payment.STATUS_FAILED

    if result_code == 1032:
        # User actively pressed "Cancel" on the STK prompt.
        payment.mark_cancelled(result_desc, callback_data)
        return payment.STATUS_CANCELLED

    if result_code == 1037:
        # Safaricom's "DS timeout user cannot be reached" - the prompt was
        # never actioned (phone off/unreachable, or just ignored). This is
        # NOT the same as the user cancelling, so it gets its own status.
        payment.mark_timeout(result_desc, callback_data)
        return payment.STATUS_TIMEOUT

    if result_code == 2001:
        payment.mark_failed(2001, result_desc or "Wrong M-Pesa PIN entered", callback_data)
        return payment.STATUS_FAILED

    payment.mark_failed(_safe_int(result_code), result_desc or "Payment failed", callback_data)
    return payment.STATUS_FAILED


def query_stk_status(payment):
    """Asks Safaricom directly what happened to a pending STK push, via
    the Lipa Na M-Pesa Online Query API. This is what makes "timeout"
    an actual fact rather than a guess: instead of the frontend
    unilaterally deciding "it's been N seconds, I'll call it a timeout",
    we ask Safaricom, and only apply a terminal status once THEY confirm
    one. If Safaricom says the transaction is still being processed, the
    payment is left exactly as pending and nothing is guessed.

    Returns the resulting status string (including STATUS_PENDING if
    still unresolved), never raises.
    """
    payment.refresh_from_db()
    if payment.status != payment.STATUS_PENDING:
        return payment.status
    if not payment.checkout_request_id:
        return payment.status

    try:
        business_short_code = config('BUSINESS_SHORT_CODE', default='')
        passkey = config('PASSKEY', default='')
        if not passkey or not business_short_code:
            return payment.status

        access_token = get_access_token()
        if not access_token:
            return payment.status

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{business_short_code}{passkey}{timestamp}".encode()
        ).decode()

        url = f"{_base_url()}/mpesa/stkpushquery/v1/query"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "BusinessShortCode": business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": payment.checkout_request_id,
        }
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        logger.info(
            "payment=%s: STK query HTTP %s: %s", payment.id, response.status_code, response.text[:1000],
        )

        if response.status_code != 200:
            # Common here: errorCode 500.001.1001 "The transaction is
            # being processed" - Safaricom hasn't got a definitive answer
            # yet either. Leave the payment pending; try again on the
            # next poll rather than guessing.
            return payment.status

        data = response.json()
        result_code = data.get('ResultCode')
        if result_code is None:
            return payment.status
        result_code = _safe_int(result_code)
        if result_code is None:
            return payment.status

        result_desc = data.get('ResultDesc', '')
        return apply_result_code(payment, result_code, result_desc, callback_data=data, source='query')

    except Exception as e:
        logger.error("payment=%s: STK query error: %s", payment.id, str(e))
        return payment.status
