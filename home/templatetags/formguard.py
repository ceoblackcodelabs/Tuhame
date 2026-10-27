from django import template
from django.utils.html import format_html

from Tuhame import formguard

register = template.Library()


@register.simple_tag
def form_guard():
    """Honeypot + signed timing token. Place inside every public <form>."""
    return format_html(
        '<div aria-hidden="true" style="position:absolute;left:-5000px;width:1px;height:1px;overflow:hidden;">'
        '<label>Leave this empty<input type="text" name="{}" value="" tabindex="-1" autocomplete="off"></label></div>'
        '<input type="hidden" name="{}" value="{}">',
        formguard.HONEYPOT_FIELD, formguard.TOKEN_FIELD, formguard.issue_token(),
    )
