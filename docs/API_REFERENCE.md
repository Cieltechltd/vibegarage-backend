# API Reference

The server exposes endpoints at its root URL. FastAPI publishes the authoritative
OpenAPI schema at `/openapi.json` and interactive Swagger UI at `/docs`; use
those for field-level request schemas and response examples.

## Conventions

- Requests and responses use JSON unless an endpoint accepts file uploads.
- Protected routes require `Authorization: Bearer <access_token>`.
- Upload routes use `multipart/form-data`.
- Errors normally use `{ "detail": "..." }` with `401` for absent/invalid
  credentials, `403` for permissions or disabled features, `404` for missing
  resources, and `422` for invalid request data.
- The API is currently not prefixed with `/api/v1`.

## Authentication

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/auth/signup` | No | Register an email/password user; email verification is required. |
| POST | `/auth/login` | No | Return an access token for an active account. |
| POST | `/auth/google` | No | Verify a Google ID token, then sign in, create, or link the account. |
| GET | `/auth/me` | Yes | Return the authenticated user. |
| POST | `/auth/verify-email` | No | Activate account with email and verification code query parameters. |
| GET | `/auth/2fa/setup` | Yes | Return an administrator’s TOTP QR image. |
| POST | `/auth/2fa/enable` | Yes | Enable TOTP with a verified code. |
| POST | `/auth/forgot-password` | No | Start password reset flow. |
| POST | `/auth/reset-password` | No | Complete password reset. |

### Email signup

```http
POST /auth/signup
Content-Type: application/json

{
  "email": "listener@example.com",
  "password": "a-strong-password",
  "username": "listener",
  "full_name": "Listener Name",
  "dob": "2000-01-01",
  "role": "LISTENER"
}
```

### Password login

```http
POST /auth/login
Content-Type: application/json

{ "email": "listener@example.com", "password": "a-strong-password" }
```

Successful login responses use:

```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

### Google sign-in or account creation

```http
POST /auth/google
Content-Type: application/json

{ "credential": "<Google Identity Services ID token>" }
```

`credential` must be a Google ID token issued to the web client configured as
`GOOGLE_CLIENT_ID`. The API validates it on the server. A verified Google email
creates an active listener account on first use; if a local account already has
that email, its Google identity is linked. The response is the standard JWT
object above.

## Account and listener features

| Group | Endpoints |
| --- | --- |
| Account | `GET /account/me`, `PATCH /account/update-profile`, `POST /account/upload-avatar`, `PUT /account/change-password`, `PATCH /account/deactivate`, `/account/socials`, `/account/preferences`, `/account/upgrade-to-artist` |
| Listener dashboard | `/listener/dashboard`, `/listener/likes`, `/listener/liked-tracks`, `/listener/following`, `/listener/recently-played`, `/listener/history`, `/listener/recommendations`, `/listener/profile` |
| Library | `/library/purchased`, `/library/liked`, `/library/recently-played`, `/library/downloads`, `/library/my-uploads` |
| Playlists | `/playlists/public`, `/playlists/my-favorites`, `/playlists/create`, `/playlists/{playlist_id}`, add/remove track routes, and `/playlists/{playlist_id}/upload-cover` |
| Discovery | `/discovery/trending`, `/discovery/new-releases`, `/discovery/feed`, `/discovery/editor-picks`, `/explore/feed`, `/explore/search`, `/explore/rising-stars`, `/daily-mix/`, `/trending/landing-page` |

Most account and library endpoints require authentication. Discovery routes are
designed for browsing; check `/docs` for the current per-route requirement.

## Artist catalogue and public profiles

| Method | Path | Description |
| --- | --- | --- |
| GET | `/artist/dashboard` | Artist dashboard data. |
| GET | `/artist/stats` | Artist statistics. |
| GET | `/artist/earnings` | Artist earnings ledger and summary. |
| POST | `/tracks/upload` | Upload a track and metadata. |
| POST | `/tracks/stream/{track_id}` | Record/start a stream. |
| GET | `/tracks/download/{track_id}` | Download a permitted track. |
| GET | `/tracks/my` | Current artist’s tracks. |
| POST | `/tracks/{track_id}/like` | Toggle or register a like. |
| GET | `/tracks/public/latest` | Latest public tracks. |
| GET | `/tracks/public/trending` | Trending public tracks. |
| GET | `/tracks/public/{track_id}` | Public track details. |
| POST/GET/PUT/DELETE | `/albums/*` | Album creation, publishing, drafts, track membership, and retrieval. |
| POST/GET | `/lyrics/upload/{track_id}`, `/lyrics/{track_id}` | Add and retrieve lyrics. |
| POST | `/clips/upload` | Upload a verified artist’s video clip. |
| GET | `/public/artists/all` | Discover public artists. |
| GET | `/public/artists/profile/{username}` | Public artist page. |
| GET | `/public/artists/profile/{username}/data` | Public profile JSON. |
| GET | `/public/artists/profile/{username}/qrcode` | Profile QR code image. |

Track and album uploads require artist authorization. The exact multipart fields
vary by route; inspect the live OpenAPI form in `/docs` before implementation.

## Payments, verification, and payouts

| Method | Path | Description |
| --- | --- | --- |
| GET | `/billing/verify-artist/plans` | Available artist verification plans. |
| POST | `/billing/verify-artist/initialize` | Start verification payment. |
| GET | `/billing/verify-artist/confirm/{reference}` | Confirm a verification transaction. |
| POST | `/billing/buy-track/{track_id}` | Start paid-track purchase. |
| POST | `/billing/webhook` | Paystack webhook receiver; do not call from the client. |
| GET | `/payouts/banks` | Supported bank list. |
| POST | `/payouts/settings` | Save artist payment settings. |
| POST | `/payouts/request` | Request a payout. |

## Fan links and blog

| Method | Path | Description |
| --- | --- | --- |
| POST | `/fanlinks` | Create an artist fan link. |
| GET | `/fanlinks/mine` | Current artist’s fan links. |
| GET | `/fanlinks/public/{slug}` | Public fan-link landing data. |
| GET | `/fanlinks/public/{slug}/download` | Download fan-link asset/content. |
| GET | `/blog/` | Published blog listing. |
| GET | `/blog/{slug}` | Published blog post. |

## Administration

The `/admin/*` routes require administrator authorization. They include dashboard
health and summaries, user role/suspension management, track/lyrics/clips
moderation, payout approval/rejection, settings, audit logs, email broadcasts,
and blog management. Use Swagger UI for the complete administrator route list
and payload shapes.

## Agent distribution

`/distro/initialize` initializes the agent-distribution integration and
`/distro/webhook` receives its events. These endpoints are operational
integrations and should not be exposed to untrusted browser callers.
