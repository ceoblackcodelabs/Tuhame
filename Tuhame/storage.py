import logging

from whitenoise.storage import CompressedManifestStaticFilesStorage

logger = logging.getLogger(__name__)


class LenientCompressedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Same as WhiteNoise's CompressedManifestStaticFilesStorage (gzip/brotli
    pre-compression + cache-busted hashed filenames), except a single
    unresolvable reference inside a vendor CSS/JS file (e.g. a sourcemap
    comment pointing at a .map file the bundle doesn't actually ship) just
    gets logged and left as-is, instead of aborting the entire
    `collectstatic` run. Every other file is still hashed/compressed
    normally - manifest_strict below covers the same kind of gap for a
    slightly different code path (a file that exists but isn't in the
    manifest yet), the converter override here covers the file being
    missing entirely.
    """

    manifest_strict = False

    def url_converter(self, name, hashed_files, template=None):
        base_converter = super().url_converter(name, hashed_files, template)

        def converter(matchobj):
            try:
                return base_converter(matchobj)
            except ValueError as exc:
                logger.warning(
                    "Static post-processing: skipping unresolvable reference "
                    "in %s (%s)", name, exc
                )
                return matchobj.group("matched")

        return converter
