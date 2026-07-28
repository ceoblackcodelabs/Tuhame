"""
Shared upload-time image optimization.

Phone camera photos routinely come in at 3-8 MB and several thousand
pixels wide - way more than any listing card, gallery, or avatar on the
site ever displays. Serving that full-size file to every visitor is one of
the biggest, easiest-to-fix sources of slow page loads. This resizes and
re-compresses images once, at upload time, so every page load afterwards
serves the already-small file - no per-request image processing needed.
"""
import logging
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


def optimize_image_field(image_field, max_dimension=1600, quality=82):
    """
    Downscale + re-compress an ImageField's file in place (call this on a
    model instance before save(), e.g. in the model's own save() override).
    Safe to call on every save - if the file is already small/optimized,
    or isn't a format we know how to touch, it's left untouched.

    - Auto-rotates based on EXIF orientation (common phone-photo issue
      where the image looks rotated once EXIF is stripped downstream).
    - Resizes so neither dimension exceeds `max_dimension`, preserving
      aspect ratio. Never upscales a smaller image.
    - Re-saves as JPEG (RGB) with `quality`, stripping EXIF/metadata bloat.
      PNGs with transparency are kept as PNG so logos/graphics with
      transparent backgrounds aren't broken.
    """
    if not image_field or not hasattr(image_field, "file"):
        return

    # Only process a file that was just assigned/uploaded this save - not
    # one that's already sitting in storage from a previous save (Django
    # marks a freshly-assigned FieldFile as "uncommitted" until it's
    # actually written to storage). Otherwise every unrelated model save
    # would re-open, re-compress and slightly degrade the same JPEG again.
    if getattr(image_field, "_committed", True):
        return

    try:
        image_field.seek(0)
        img = Image.open(image_field)
        img = ImageOps.exif_transpose(img)  # respect camera rotation, then drop the tag

        has_alpha = img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        )

        original_format = (img.format or "JPEG").upper()
        target_format = "PNG" if (has_alpha or original_format == "PNG") else "JPEG"

        # Resize (only ever down, never up)
        img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        buffer = BytesIO()
        save_kwargs = {"optimize": True}
        if target_format == "JPEG":
            if img.mode != "RGB":
                img = img.convert("RGB")
            save_kwargs["quality"] = quality
            save_kwargs["progressive"] = True
        img.save(buffer, format=target_format, **save_kwargs)
        buffer.seek(0)

        name = image_field.name
        if target_format == "JPEG" and not name.lower().endswith((".jpg", ".jpeg")):
            name = name.rsplit(".", 1)[0] + ".jpg"

        image_field.file = InMemoryUploadedFile(
            buffer, None, name, f"image/{target_format.lower()}",
            buffer.getbuffer().nbytes, None
        )
        image_field.name = name
    except Exception as exc:
        # Never let an image-optimization hiccup block the actual upload -
        # worst case the original file is saved un-optimized.
        logger.warning("Image optimization skipped for %s: %s", getattr(image_field, "name", "?"), exc)
