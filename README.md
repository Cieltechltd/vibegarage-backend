# VibeGarage Backend

VibeGarage is a FastAPI backend for a music platform: listener discovery,
artist publishing, streaming, paid-track purchases, verification, payouts,
short clips, fan links, and administration.

The API is mounted at the application root (for example, `/auth/login`), not
under a `/api/v1` prefix. Interactive API documentation is available at
`/docs` when the server is running.

## What the API provides

- Email/password authentication, email verification, password reset, admin 2FA,
  and Google sign-in.
- Listener features: discovery, search, likes, follows, playlists, downloads,
  recommendations, and listening history.
- Artist features: profiles, audio and cover uploads, albums, lyrics, clips,
  earnings, verification, and payouts.
- Monetization through Paystack for artist verification and paid-track access.
- Public artist pages, QR codes, fan links, a blog, and admin moderation.

## Documentation

| Document | Purpose |
| --- | --- |
| [Getting started and operations](docs/DEVELOPMENT.md) | Required environment variables, migrations, local run commands, deployment checks, and scheduled work. |
| [API reference](docs/API_REFERENCE.md) | Endpoint catalogue, authentication rules, and request examples. |
| [Frontend integration guide](docs/FRONTEND_GUIDE.md) | Token handling, Google Sign-In exchange, upload flows, and playback rules. |
| [System architecture](docs/SYSTEM_ARCHITECTURE.md) | Components, request paths, external services, and storage. |
| [Database overview](docs/DATABASE_OVERVIEW.md) | Main entities, relationships, and migration policy. |

## Quick start

Prerequisites: Python 3.10+, PostgreSQL, and a populated `.env` file. See the
[full setup guide](docs/DEVELOPMENT.md) for all required values.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to inspect and exercise the API.

## Authentication at a glance

Protected requests use a bearer token:

```http
Authorization: Bearer <access_token>
```

Use `POST /auth/signup` to register with email/password, then confirm the
email through `POST /auth/verify-email`. `POST /auth/login` returns a JWT.

Google Identity Services clients should send their ID token to
`POST /auth/google` as `{"credential": "<id-token>"}`. The API verifies the
token against `GOOGLE_CLIENT_ID`, creates a verified listener on first sign-in,
or links a matching existing email account. See the
[frontend guide](docs/FRONTEND_GUIDE.md#google-sign-in) for the exchange.

## Common development commands

```bash
# Check migration state and apply outstanding migrations
alembic current
alembic upgrade head

# Start the development API
uvicorn app.main:app --reload

# Compile Python files as a quick syntax check
python -m compileall app alembic
```

## Repository layout

```text
app/
  routers/       HTTP endpoints grouped by feature
  models/        SQLAlchemy database models
  schemas/       Pydantic request and response models
  services/      Payments, storage, recommendations, notifications, and jobs
  core/          Settings, authentication helpers, and authorization helpers
  db/            Engine, sessions, dependency, and bootstrap logic
  uploads/       Local development media storage, served as /static
alembic/         Database migration environment and revisions
docs/            Product, API, integration, data, and operations documentation
```

## Operational notes

- Keep `.env`, tokens, payment keys, and SMTP credentials out of source control.
- Run migrations before deploying code that depends on schema changes.
- The application creates upload directories at startup and serves local uploads
  from `/static`; use durable object storage/CDN before horizontally scaling.
- Paystack webhooks must be reachable publicly and must be configured with the
  same secret used by the API.

## License

MIT License
