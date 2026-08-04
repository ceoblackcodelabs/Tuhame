"""
Inline SVG icon system (Lucide icons, https://lucide.dev - ISC licensed).
Replaces the emoji previously used as ad hoc UI icons across the site with
real, consistent, theme-colored icons that don't depend on the OS/browser's
emoji font (which varies by platform and looks inconsistent).

Usage in templates:
    {% load icons %}
    {% icon "map-pin" %}                       default 1em, currentColor
    {% icon "star" size=16 filled=True %}       solid-filled variant
    {% icon "check" class_name="text-success" %}

NOTE ON THE "lucide-icon" CLASS NAME: don't rename this to plain "icon".
Both home/static/assets/css/style.css (.form-input-icon .icon,
.profile-nav-item .icon) and the dashboard theme's vendor CSS
(dashboard/static/2Hame/assets/css/style.css, 8 separate ".icon" rules)
already style a bare ".icon" class - usually with position:absolute for
positioning inside inputs/nav items. If this tag's own <svg> also carried
class="icon", it would inherit that positioning too, and when it's nested
inside another ".icon" wrapper span (a common pattern in this codebase,
e.g. templates/auth/login.html's .form-input-icon), you get the SVG
absolutely-positioned *inside* an already absolutely-positioned span -
double-offset and visibly broken. "lucide-icon" is deliberately
namespaced to never collide with either stylesheet.
"""
from django import template
from django.utils.safestring import mark_safe

from .icons_data import ICONS
from .brand_icons_data import BRAND_ICONS

register = template.Library()


@register.simple_tag
def icon(name, size=None, filled=False, class_name=""):
    """Render an inline SVG icon by name. Falls back to a small blank
    square (rather than raising) if an unknown name is passed, so a typo
    degrades gracefully instead of 500ing a page."""
    body = ICONS.get(name)
    if body is None:
        body = ICONS.get("warning", "")
        name = "missing-icon"

    style_size = f"width:{size}px;height:{size}px;" if size else "width:1em;height:1em;"
    fill = "currentColor" if filled else "none"
    classes = f"lucide-icon lucide-icon-{name} {class_name}".strip()

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="{fill}" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'class="{classes}" style="{style_size}vertical-align:-0.125em;flex-shrink:0;display:inline-block;" '
        f'aria-hidden="true" focusable="false">{body}</svg>'
    )
    return mark_safe(svg)


@register.simple_tag
def brand_icon(name, size=None, class_name=""):
    """Render a real brand/social logo (facebook, x-twitter, instagram,
    linkedin) - see brand_icons_data.py for sourcing/licensing. Unlike
    icon(), these are solid single-path marks with their own native
    viewBox, not currentColor-stroked UI icons."""
    entry = BRAND_ICONS.get(name)
    if entry is None:
        return mark_safe("")
    viewbox, path_d = entry

    style_size = f"width:{size}px;height:{size}px;" if size else "width:1em;height:1em;"
    classes = f"lucide-icon brand-icon brand-icon-{name} {class_name}".strip()

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" '
        f'class="{classes}" style="{style_size}vertical-align:-0.125em;flex-shrink:0;display:inline-block;" '
        f'aria-hidden="true" focusable="false">'
        f'<path fill="currentColor" d="{path_d}" /></svg>'
    )
    return mark_safe(svg)
