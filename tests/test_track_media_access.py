"""Regression tests for private paid audio and safe preview delivery."""

import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.update(
    {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "unit-test-supabase-key",
    }
)

try:
    import supabase  # noqa: F401
except ModuleNotFoundError:
    supabase_stub = types.ModuleType("supabase")
    supabase_stub.Client = object
    supabase_stub.create_client = lambda *_args, **_kwargs: None
    sys.modules["supabase"] = supabase_stub

with patch.object(supabase, "create_client", return_value=None):
    from app.services import track_media
from app.schemas.track import TrackOut


VALID_WAV_HEADER = b"RIFF\x00\x00\x00\x00WAVE"


class FakeBucket:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    def upload(self, **kwargs):
        self.calls.append(("upload", self.name, kwargs))

    def create_signed_url(self, path, expires_in):
        self.calls.append(("sign", self.name, path, expires_in))
        return {"signedURL": f"/storage/v1/object/sign/{self.name}/{path}?token=temporary"}

    def remove(self, paths):
        self.calls.append(("remove", self.name, paths))


class FakeStorage:
    def __init__(self):
        self.calls = []

    def from_(self, name):
        return FakeBucket(name, self.calls)


class TrackMediaAccessTests(unittest.IsolatedAsyncioTestCase):
    def test_audio_validation_requires_matching_container_signature(self):
        examples = {
            "audio/mpeg": b"ID3\x04\x00\x00\x00\x00\x00\x00",
            "audio/mp3": b"\xff\xfb\x90\x64",
            "audio/wav": b"RIFF\x00\x00\x00\x00WAVE",
            "audio/x-wav": b"RIFF\x00\x00\x00\x00WAVE",
            "audio/flac": b"fLaC\x00\x00",
            "audio/ogg": b"OggS\x00\x02",
        }
        for content_type, audio_bytes in examples.items():
            with self.subTest(content_type=content_type):
                self.assertEqual(
                    track_media.validate_audio_upload(audio_bytes, content_type),
                    content_type,
                )

        with self.assertRaisesRegex(ValueError, "contents do not match"):
            track_media.validate_audio_upload(b"RIFF\x00\x00\x00\x00WAVE", "audio/mpeg")

    async def test_audio_upload_accepts_mime_parameters_and_canonicalizes_extension(self):
        storage = FakeStorage()
        with patch.object(track_media, "supabase_client", SimpleNamespace(storage=storage)):
            reference = await track_media.upload_track_audio(
                VALID_WAV_HEADER, "song.exe", " Audio/WAV; charset=binary ", "track-mime", is_paid=False
            )

        self.assertTrue(reference.endswith("/audio/track-mime.wav"))
        uploaded = [call for call in storage.calls if call[0] == "upload"]
        self.assertEqual(uploaded[0][2]["file_options"]["content-type"], "audio/wav")

    async def test_audio_upload_rejects_unsupported_type_before_storage(self):
        storage = FakeStorage()
        with patch.object(track_media, "supabase_client", SimpleNamespace(storage=storage)):
            with self.assertRaisesRegex(ValueError, "Unsupported audio format"):
                await track_media.upload_track_audio(
                    VALID_WAV_HEADER, "song.mp4", "video/mp4", "track-bad-type", is_paid=False
                )

        self.assertEqual(storage.calls, [])

    async def test_audio_upload_rejects_empty_file_before_storage(self):
        storage = FakeStorage()
        with patch.object(track_media, "supabase_client", SimpleNamespace(storage=storage)):
            with self.assertRaisesRegex(ValueError, "audio file is empty"):
                await track_media.upload_track_audio(
                    b"", "song.mp3", "audio/mpeg", "track-empty", is_paid=False
                )

        self.assertEqual(storage.calls, [])

    async def test_audio_storage_errors_are_reported_as_temporary_failures(self):
        def fail_upload(*_args, **_kwargs):
            raise OSError("storage offline")

        with patch.object(track_media, "_upload_object", side_effect=fail_upload):
            with self.assertRaisesRegex(RuntimeError, "Audio storage is temporarily unavailable"):
                await track_media.upload_track_audio(
                    b"ID3\x04\x00\x00\x00\x00\x00\x00", "song.mp3", "audio/mpeg", "track-storage", is_paid=False
                )

    async def test_audio_cleanup_removes_paid_original_and_public_preview(self):
        storage = FakeStorage()
        with patch.object(track_media, "supabase_client", SimpleNamespace(storage=storage)):
            await track_media.delete_track_audio(
                "track-cleanup", "song.wav", "audio/wav", is_paid=True
            )

        removals = [call for call in storage.calls if call[0] == "remove"]
        self.assertEqual(
            removals,
            [
                ("remove", track_media.PAID_AUDIO_BUCKET, ["audio/track-cleanup.wav"]),
                ("remove", track_media.PUBLIC_MEDIA_BUCKET, ["previews/track-cleanup.mp3"]),
            ],
        )

    async def test_paid_upload_keeps_original_private_and_creates_public_preview(self):
        storage = FakeStorage()
        with (
            patch.object(track_media, "supabase_client", SimpleNamespace(storage=storage)),
            patch.object(track_media, "_make_preview", return_value=b"preview-audio"),
        ):
            audio_reference = await track_media.upload_track_audio(
                VALID_WAV_HEADER, "song.wav", "audio/wav", "track-1", is_paid=True
            )

        self.assertEqual(
            audio_reference,
            "private://vibegarage-paid-audio/audio/track-1.wav",
        )
        uploaded = [call for call in storage.calls if call[0] == "upload"]
        self.assertEqual([call[1] for call in uploaded], ["vibegarage", "vibegarage-paid-audio"])
        self.assertEqual(uploaded[0][2]["path"], "previews/track-1.mp3")
        self.assertEqual(uploaded[1][2]["path"], "audio/track-1.wav")

    def test_unowned_paid_track_gets_preview_not_original(self):
        track = SimpleNamespace(
            id="track-2",
            is_for_sale=True,
            audio_path="private://vibegarage-paid-audio/audio/track-2.mp3",
        )

        url = track_media.track_playback_url(track, can_play_full=False)

        self.assertIn("/previews/track-2.mp3", url)
        self.assertNotIn("paid-audio", url)

    def test_purchased_paid_track_gets_a_short_lived_signed_url(self):
        storage = FakeStorage()
        track = SimpleNamespace(
            id="track-3",
            is_for_sale=True,
            audio_path="private://vibegarage-paid-audio/audio/track-3.mp3",
        )
        with patch.object(track_media, "supabase_client", SimpleNamespace(storage=storage)):
            url = track_media.track_playback_url(track, can_play_full=True)

        self.assertIn("/object/sign/vibegarage-paid-audio/audio/track-3.mp3", url)
        self.assertIn("token=temporary", url)
        self.assertEqual(storage.calls[0][3], track_media.SIGNED_AUDIO_URL_TTL_SECONDS)

    def test_paid_track_with_legacy_public_path_fails_closed(self):
        track = SimpleNamespace(
            id="track-4",
            is_for_sale=True,
            audio_path="https://example.supabase.co/storage/v1/object/public/vibegarage/audio/old.mp3",
        )

        with self.assertRaises(RuntimeError):
            track_media.track_playback_url(track, can_play_full=True)

    def test_free_tracks_keep_their_public_audio(self):
        track = SimpleNamespace(
            id="track-5",
            is_for_sale=False,
            audio_path="https://example.supabase.co/storage/v1/object/public/vibegarage/audio/free.mp3",
        )

        self.assertEqual(
            track_media.track_playback_url(track, can_play_full=False),
            track.audio_path,
        )

    def test_free_track_without_audio_is_unavailable(self):
        track = SimpleNamespace(id="track-7", is_for_sale=False, audio_path=None)

        with self.assertRaisesRegex(RuntimeError, "Track audio is not available"):
            track_media.track_playback_url(track, can_play_full=False)

    def test_paid_track_schema_uses_preview_instead_of_private_reference(self):
        track = TrackOut(
            id="track-6",
            title="Paid track",
            audio_path="private://vibegarage-paid-audio/audio/track-6.mp3",
            cover_path=None,
            is_for_sale=True,
        )

        self.assertEqual(
            track.audio_path,
            "https://tatswhuxpbxzlprjfvln.supabase.co/storage/v1/object/public/"
            "vibegarage/previews/track-6.mp3",
        )


if __name__ == "__main__":
    unittest.main()
