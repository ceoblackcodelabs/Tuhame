"""
Shared upload-time video optimization (hero background videos).

Mirrors Tuhame/image_utils.py's shape and guarantees: called on a model
instance before save(), swaps the field's file in place with a
compressed version, and NEVER raises or blocks the save - worst case the
original, uncompressed file goes to storage as-is and a warning is
logged.

Unlike image compression (Pillow, a pure-Python dependency already in
requirements.txt), video transcoding needs the `ffmpeg` binary on the
server PATH. Shared/cPanel hosting doesn't always have it installed, so
this checks for it first and quietly skips compression - rather than
failing the upload - when it's missing. See DEPLOY.md for how to get
ffmpeg onto the server if you want compression to actually run.
"""
import logging
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger(__name__)

# Hero videos autoplay muted/looped as a full-bleed background - visitors
# never scrub or watch them like content, so there's no reason to ship
# more resolution/bitrate than that. 1080p, modest CRF, and a capped
# duration keep the file small without visibly hurting a background loop.
MAX_HEIGHT = 1080
CRF = 28
MAX_DURATION_SECONDS = 30
AUDIO_STRIPPED = True  # hero videos always play muted - no reason to ship an audio track at all


def _ffmpeg_available():
    return shutil.which('ffmpeg') is not None


def compress_video_field(video_field, max_height=MAX_HEIGHT, crf=CRF):
    """
    Downscale + re-encode a FileField's video in place (call this on a
    model instance before save(), same pattern as optimize_image_field).
    Safe to call on every save - only touches a freshly-uploaded,
    not-yet-committed file, and is a silent no-op if ffmpeg isn't
    installed on the server or the re-encode fails for any reason.
    """
    if not video_field:
        return

    # Same "only a freshly-assigned file" guard as optimize_image_field -
    # otherwise every unrelated save would re-encode the same video again.
    if getattr(video_field, "_committed", True):
        return

    if not _ffmpeg_available():
        logger.warning(
            "Video compression skipped for %s: ffmpeg not found on PATH "
            "(uploading the original, uncompressed file instead)",
            getattr(video_field, "name", "?"),
        )
        return

    try:
        if not hasattr(video_field, "file"):
            return
    except Exception as exc:
        logger.warning("Video compression skipped (file unreadable) for %s: %s", getattr(video_field, "name", "?"), exc)
        return

    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp(prefix='hero_video_')
        src_path = Path(tmp_dir) / 'input'
        dst_path = Path(tmp_dir) / 'output.mp4'

        video_field.seek(0)
        with open(src_path, 'wb') as f:
            for chunk in video_field.chunks():
                f.write(chunk)

        cmd = [
            'ffmpeg', '-y', '-i', str(src_path),
            '-t', str(MAX_DURATION_SECONDS),
            '-vf', f"scale=-2:'min({max_height},ih)'",
            '-c:v', 'libx264', '-crf', str(crf), '-preset', 'medium',
            '-movflags', '+faststart',  # lets the browser start playing before the whole file downloads
        ]
        cmd += ['-an'] if AUDIO_STRIPPED else ['-c:a', 'aac', '-b:a', '96k']
        cmd += [str(dst_path)]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0 or not dst_path.exists():
            logger.warning(
                "ffmpeg compression failed for %s (exit %s): %s",
                getattr(video_field, "name", "?"), result.returncode, result.stderr[-500:],
            )
            return

        compressed_bytes = dst_path.read_bytes()
        original_name = video_field.name
        new_name = original_name.rsplit('.', 1)[0] + '.mp4'

        buffer = BytesIO(compressed_bytes)
        video_field.file = InMemoryUploadedFile(
            buffer, None, new_name, 'video/mp4', len(compressed_bytes), None,
        )
        video_field.name = new_name

    except Exception as exc:
        logger.warning("Video compression skipped for %s: %s", getattr(video_field, "name", "?"), exc)
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def extract_video_poster(video_field):
    """
    Grabs a single still frame (1s in, to skip a black opening frame) from
    a video file as JPEG bytes, for use as a <video poster> while the file
    loads. Returns None if ffmpeg is unavailable or extraction fails -
    callers should treat that as "no poster", not an error.
    """
    if not video_field or not _ffmpeg_available():
        return None

    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp(prefix='hero_poster_')
        src_path = Path(tmp_dir) / 'input'
        dst_path = Path(tmp_dir) / 'poster.jpg'

        video_field.seek(0)
        with open(src_path, 'wb') as f:
            for chunk in video_field.chunks():
                f.write(chunk)

        cmd = ['ffmpeg', '-y', '-ss', '1', '-i', str(src_path), '-frames:v', '1', str(dst_path)]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0 or not dst_path.exists():
            return None

        return dst_path.read_bytes()
    except Exception as exc:
        logger.warning("Poster extraction skipped: %s", exc)
        return None
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
