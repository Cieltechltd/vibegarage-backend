# Database Overview

The application uses SQLAlchemy with PostgreSQL. The connection is supplied by
`DATABASE_URL`; `postgres://` URLs are normalised to `postgresql://` at runtime.

## Main entities

| Area | Entities |
| --- | --- |
| Identity | `users`, artist profile data held on the user record, follows, likes, audit logs, system settings |
| Catalogue | tracks, albums, playlists, playlist-track links, lyrics, clips |
| Listener activity | plays, downloads, purchases, favorites, recommendations and library queries |
| Revenue | payments, transactions, earning entries, artist payment settings, payout requests |
| Growth and content | fan links and blog posts |

## User identity

`users.id` is the platform identifier. Email is unique. Password hashes remain
non-null so Google-created accounts receive an unguessable generated hash;
password login is only possible after a password is explicitly set. The nullable,
unique `google_subject` stores Google’s stable `sub` claim and must never be
derived from an email address.

Users can be listeners, artists, or administrators. Profile, social, account
preferences, verification, two-factor, wallet, and subscription fields are kept
on this central model. Artist-specific payment settings are a one-to-one
relationship with a user.

## Important relationships

```text
User (artist) 1 --- * Track
User (artist) 1 --- * Album
User             1 --- * Like / Play / Follow
Album            1 --- * Track (optional album membership)
Track            1 --- * Lyric / Clip / Download / Purchase activity
User (artist)    1 --- 1 ArtistPaymentSettings
User (artist)    1 --- * EarningEntry / PayoutRequest
```

The exact model declarations are the source of truth; use the live database and
the SQLAlchemy models when planning a data migration.

## Migrations

All schema changes belong in a new Alembic revision under `alembic/versions/`.
Apply migrations with `alembic upgrade head`. Check the active revision with
`alembic current` before deploying. A migration should include a downgrade path
where safe and should avoid dropping production data without an explicit backup
and rollout plan.

The Google sign-in schema addition is
`eb1b4b3e9a11_add_google_identity_to_users.py`; it adds the unique nullable
`users.google_subject` column.
