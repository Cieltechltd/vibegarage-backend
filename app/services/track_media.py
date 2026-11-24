"""Storage helpers for public previews and protected paid audio."""

import asyncio
import io
import logging
import os
import uuid
from pathlib import PurePosixPath
from typing import Any

from supabase import Client, create_client


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PUBLIC_MEDIA_BUCKET = "vibegarage"
PAID_AUDIO_BUCKET = os.getenv("SUPABASE_PAID_AUDIO_BUCKET", "vibegarage-paid-audio")
PRIVATE_AUDIO_PREFIX = "private://"
PREVIEW_LENGTH_MS = 15_000
SIGNED_AUDIO_URL_TTL_SECONDS = 300
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/ogg",
}
AUDIO_TYPE_SUFFIXES = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/flac": ".flac",
    "audio/ogg": ".ogg",
}
logger = logging.getLogger(__name__)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials missing from environment variables.")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def private_audio_reference(object_path: str) -> str:
    """Return the opaque database value for an object in the private bucket."""
    return f"{PRIVATE_AUDIO_PREFIX}{PAID_AUDIO_BUCKET}/{object_path.lstrip('/')}"


def _parse_private_audio_reference(reference: str) -> tuple[str, str] | None:
    if not reference.startswith(PRIVATE_AUDIO_PREFIX):
        return None

    bucket_and_path = reference[len(PRIVATE_AUDIO_PREFIX):]
    bucket, separator, object_path = bucket_and_path.partition("/")
    if not separator or bucket != PAID_AUDIO_BUCKET or not object_path:
        return None

    normalized = str(PurePosixPath(object_path))
    if ".." in PurePosixPath(normalized).parts:
        return None
    return bucket, normalized


def preview_object_path(track_id: str) -> str:
    return f"previews/{track_id}.mp3"


def public_preview_url(track_id: str) -> str:
    return (
        f"{SUPABASE_URL}/storage/v1/object/public/"
        f"{PUBLIC_MEDIA_BUCKET}/{preview_object_path(track_id)}"
    )


def public_audio_url(audio_reference: str | None) -> str | None:
    """Resolve existing free-track references without exposing private paths."""
    if not audio_reference or audio_reference.startswith(PRIVATE_AUDIO_PREFIX):
        return None
    if audio_reference.startswith(("http://", "https://")):
        return audio_reference

    object_path = audio_reference.lstrip("/")
    if object_path.startswith(f"{PUBLIC_MEDIA_BUCKET}/"):
        object_path = object_path[len(PUBLIC_MEDIA_BUCKET) + 1:]
    if object_path.startswith("object/public/"):
        object_path = object_path[len("object/public/"):]
        _, separator, object_path = object_path.partition("/")
        if not separator:
            return None
    return f"{SUPABASE_URL}/storage/v1/object/public/{PUBLIC_MEDIA_BUCKET}/{object_path}"


def catalog_audio_url(track: Any) -> str:
    """Safe URL for catalogue responses; premium tracks expose only previews."""
    if getattr(track, "is_for_sale", False):
        return public_preview_url(str(track.id))
    return public_audio_url(getattr(track, "audio_path", None)) or ""


def _make_preview(audio_bytes: bytes) -> bytes:
    from pydub import AudioSegment

    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    preview = audio[:PREVIEW_LENGTH_MS]
    output = io.BytesIO()
    preview.export(output, format="mp3")
    return output.getvalue()


def validate_audio_upload(audio_bytes: bytes, content_type: str | None) -> str:
    """Validate audio uploads consistently and return the normalized MIME type."""
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_type not in ALLOWED_AUDIO_TYPES:
        raise ValueError("Unsupported audio format. Upload an MP3, WAV, FLAC, or OGG file.")
    if not audio_bytes:
        raise ValueError("The audio file is empty. Choose a non-empty audio file and try again.")
    return normalized_type


def _audio_suffix(filename: str | None, content_type: str) -> str:
    suffix = os.path.splitext(filename or "")[1].lower()
    allowed_suffix = AUDIO_TYPE_SUFFIXES[content_type]
    if suffix != allowed_suffix:
        return allowed_suffix
    return suffix


def _upload_object(bucket: str, path: str, data: bytes, content_type: str) -> None:
    supabase_client.storage.from_(bucket).upload(
        path=path,
        file=data,
        file_options={"content-type": content_type},
    )


async def upload_track_audio(
    audio_bytes: bytes,
    filename: str | None,
    content_type: str | None,
    track_id: str,
    is_paid: bool,
) -> str:
    """Upload a full track and, for paid tracks, a public 15-second preview.

    Paid originals go only to the private bucket. Their public preview is
    written first; if either operation fails, the upload fails closed.
    """
    normalized_type = validate_audio_upload(audio_bytes, content_type)
    suffix = _audio_suffix(filename, normalized_type)

    object_path = f"audio/{track_id}{suffix}"
    bucket = PAID_AUDIO_BUCKET if is_paid else PUBLIC_MEDIA_BUCKET
    preview_path = preview_object_path(track_id)

    if is_paid:
        try:
            preview_bytes = await asyncio.to_thread(_make_preview, audio_bytes)
        except Exception as exc:
            raise ValueError(
                "The audio file could not be read. Upload a valid MP3, WAV, FLAC, or OGG file."
            ) from exc
        try:
            await asyncio.to_thread(
                _upload_object, PUBLIC_MEDIA_BUCKET, preview_path, preview_bytes, "audio/mpeg"
            )
        except Exception as exc:
            raise RuntimeError("Audio storage is temporarily unavailable.") from exc

    try:
        await asyncio.to_thread(
            _upload_object, bucket, object_path, audio_bytes, normalized_type
        )
    except Exception as exc:
        if is_paid:
            try:
                await asyncio.to_thread(
                    supabase_client.storage.from_(PUBLIC_MEDIA_BUCKET).remove,
                    [preview_path],
                )
            except Exception:
                pass
        raise RuntimeError("Audio storage is temporarily unavailable.") from exc

    if is_paid:
        return private_audio_reference(object_path)
    return public_audio_url(object_path) or ""


async def delete_track_audio(
    track_id: str,
    filename: str | None,
    content_type: str | None,
    is_paid: bool,
) -> None:
    """Best-effort removal of audio objects when a track record cannot be saved."""
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_type not in AUDIO_TYPE_SUFFIXES:
        logger.warning("Could not determine audio type while cleaning track %s", track_id)
        return

    object_path = f"audio/{track_id}{_audio_suffix(filename, normalized_type)}"
    bucket = PAID_AUDIO_BUCKET if is_paid else PUBLIC_MEDIA_BUCKET
    try:
        await asyncio.to_thread(
            supabase_client.storage.from_(bucket).remove, [object_path]
        )
    except Exception:
        logger.exception("Could not remove uploaded audio for track %s", track_id)

    if is_paid:
        try:
            await asyncio.to_thread(
                supabase_client.storage.from_(PUBLIC_MEDIA_BUCKET).remove,
                [preview_object_path(track_id)],
            )
        except Exception:
            logger.exception("Could not remove uploaded preview for track %s", track_id)


def _signed_private_audio_url(reference: str) -> str:
    parsed = _parse_private_audio_reference(reference)
    if not parsed:
        raise ValueError("Paid audio is not stored in the configured private bucket.")

    bucket, object_path = parsed
    try:
        response = supabase_client.storage.from_(bucket).create_signed_url(
            object_path, SIGNED_AUDIO_URL_TTL_SECONDS
        )
    except Exception as exc:
        raise RuntimeError("Could not sign paid track audio.") from exc
    signed_url = response.get("signedURL") or response.get("signedUrl")
    if not signed_url:
        raise RuntimeError("Storage did not return a signed audio URL.")
    if signed_url.startswith(("http://", "https://")):
        return signed_url
    return f"{SUPABASE_URL}/{signed_url.lstrip('/')}"


def track_playback_url(track: Any, can_play_full: bool) -> str:
    """Resolve a safe media URL for a listener's access level."""
    is_paid = bool(getattr(track, "is_for_sale", False))
    reference = getattr(track, "audio_path", None) or ""

    if is_paid and not can_play_full:
        return public_preview_url(str(track.id))

    if is_paid:
        try:
            return _signed_private_audio_url(reference)
        except (ValueError, RuntimeError, KeyError) as exc:
            raise RuntimeError(
                "Paid track audio is not ready in private storage."
            ) from exc

    if reference.startswith(PRIVATE_AUDIO_PREFIX):
        try:
            return _signed_private_audio_url(reference)
        except (ValueError, RuntimeError, KeyError) as exc:
            raise RuntimeError("Track audio is not available in storage.") from exc

    audio_url = public_audio_url(reference)
    if not audio_url:
        raise RuntimeError("Track audio is not available in storage.")
    return audio_url
