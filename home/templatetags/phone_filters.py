import re

from django import template

register = template.Library()


@register.filter
def whatsapp_number(value):
    """
    Normalize a phone number to the digits-only international format
    wa.me needs, e.g. '0712 345 678' or '+254 712345678' -> '254712345678'.
    Assumes Kenyan numbers when no country code is present.
    """
    if not value:
        return ''
    digits = re.sub(r'\D', '', str(value))
    if not digits:
        return ''
    if digits.startswith('0') and len(digits) == 10:
        digits = '254' + digits[1:]
    elif len(digits) == 9:
        digits = '254' + digits
    return digits


@register.filter
def tel_href(value):
    """Strip a phone number down to digits (keeping a leading +) for tel: links."""
    if not value:
        return ''
    value = str(value).strip()
    digits = re.sub(r'\D', '', value)
    if not digits:
        return ''
    if digits.startswith('0') and len(digits) == 10:
        digits = '254' + digits[1:]
    elif len(digits) == 9:
        digits = '254' + digits
    return '+' + digits
