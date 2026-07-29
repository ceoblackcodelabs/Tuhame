"""
Shared upload validators.

Each model field below only had client-side `accept="image/*"` (or nothing
at all) — that's a hint for the file picker, not an actual limit, so a
5 MB PNG or a renamed .exe would sail straight through and land in
MEDIA_ROOT. These add real server-side limits: a size cap per scenario and
a content-type/extension allowlist, so bad uploads get a clean form error
instead of quietly bloating storage or the page.
"""
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
DOCUMENT_EXTENSIONS = ('.pdf', '.jpg', '.jpeg', '.png')


def _validate(f, max_size, extensions, kind):
    ext = ('.' + f.name.rsplit('.', 1)[-1].lower()) if '.' in f.name else ''
    if ext not in extensions:
        raise ValidationError(
            f"Unsupported {kind} type '{ext or '(none)'}'. Allowed: {', '.join(extensions)}"
        )
    if f.size > max_size:
        raise ValidationError(
            f"File too large ({filesizeformat(f.size)}). Max size is {filesizeformat(max_size)}."
        )


def validate_profile_picture(f):
    _validate(f, max_size=5 * 1024 * 1024, extensions=IMAGE_EXTENSIONS, kind='image')


def validate_property_image(f):
    _validate(f, max_size=8 * 1024 * 1024, extensions=IMAGE_EXTENSIONS, kind='image')


def validate_signature_image(f):
    _validate(f, max_size=2 * 1024 * 1024, extensions=IMAGE_EXTENSIONS, kind='image')


def validate_document(f):
    _validate(f, max_size=10 * 1024 * 1024, extensions=DOCUMENT_EXTENSIONS, kind='document')
