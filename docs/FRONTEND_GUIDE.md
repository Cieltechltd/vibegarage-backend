# Frontend Integration Guide

The backend currently exposes routes at the root URL. For a development API at
`http://127.0.0.1:8000`, use paths such as
`http://127.0.0.1:8000/auth/login`.

## Authentication

Store the access token returned by `/auth/login` or `/auth/google` using the
security approach appropriate for your client. Send it on protected requests:

```http
Authorization: Bearer <access_token>
```

On a `401` response, remove the stored token and return the user to sign-in.
A `403` usually means an inactive account, a missing role, or an unavailable
feature. Validation errors use `422` and include a `detail` field.

### Email and password

1. Submit registration details to `POST /auth/signup`.
2. Ask the user for the verification code delivered by email.
3. Call `POST /auth/verify-email?email=...&code=...`.
4. Sign in with `POST /auth/login` and store its bearer token.
5. Use `GET /auth/me` or `GET /account/me` to hydrate the signed-in user.

The signup request requires `email`, `password`, `username`, and `dob`; `role`
is optional and accepts `LISTENER` or `ARTIST`.

## Google sign-in

Create a Google OAuth 2.0 **Web application** client. Add the frontend’s
development and production origins to its authorised JavaScript origins, then
configure its client ID as `GOOGLE_CLIENT_ID` in the backend environment.

After Google Identity Services returns a credential, send it unchanged to the
backend. Do not trust a decoded token in the browser as proof of identity.

```js
const response = await fetch(`${API_URL}/auth/google`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ credential: googleCredential }),
});

if (!response.ok) throw new Error((await response.json()).detail);
const { access_token, token_type } = await response.json();
```

The API validates the token’s signature, expiry, issuer, verified email, and
audience. The first sign-in creates an active listener account. If an email
password account already uses that verified email, it is linked to the Google
identity. Both cases return the same JWT response as password login.

## Uploads and media

Track, clip, cover, and avatar routes accept multipart uploads. Use
`FormData`; do not set the `Content-Type` header yourself because the browser
must include the multipart boundary.

```js
const form = new FormData();
form.append("audio_file", file);
form.append("title", title);
form.append("genre", genre);

await fetch(`${API_URL}/tracks/upload`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: form,
});
```

Local media URLs are served under `/static`. Treat returned media URLs as the
source of truth instead of constructing paths in the client.

## Playback and purchases

Start playback by calling `POST /tracks/stream/{track_id}`. Use the track data
returned by the API to decide whether to play preview or full media:

- Non-premium tracks can use the full stream.
- Premium tracks without access should use the preview and show purchase UI.
- Premium tracks with access can use the full stream.

Use `POST /billing/buy-track/{track_id}` to initialize payment. Redirect the
user using the authorization URL supplied by the payment response, then refresh
the track/library after Paystack confirmation.

## Main client flows

| User goal | Relevant endpoints |
| --- | --- |
| Discover music | `/explore/feed`, `/explore/search`, `/discovery/*`, `/trending/landing-page` |
| Listener library | `/library/*`, `/listener/*`, `/playlists/*` |
| Profile management | `/account/me`, `/account/update-profile`, `/account/upload-avatar` |
| Artist publishing | `/account/upgrade-to-artist`, `/tracks/upload`, `/albums/*`, `/lyrics/*`, `/clips/upload` |
| Artist reporting | `/artist/dashboard`, `/artist/stats`, `/artist/earnings`, `/payouts/*` |
| Public sharing | `/public/artists/profile/{username}`, `/fanlinks/public/{slug}` |

Refer to [API_REFERENCE.md](API_REFERENCE.md) and the live `/docs` page for
exact schemas and required multipart fields.
