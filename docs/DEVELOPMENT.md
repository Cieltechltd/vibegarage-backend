# Development and Operations Guide

## Prerequisites

- Python 3.10 or later
- PostgreSQL reachable from the API process
- A virtual environment with dependencies from `requirements.txt`
- An `.env` file in the repository root

## Environment configuration

The settings class reads `.env`. These values are required by the application
configuration unless a default is shown:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string. |
| `SECRET_KEY` | Secret used to sign JWTs; use a long random production value. |
| `ALGORITHM` | JWT algorithm; defaults to `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime; defaults to `60`. |
| `SUPABASE_URL`, `SUPABASE_KEY` | Supabase integration configuration. |
| `MASTER_ADMIN_EMAIL`, `MASTER_ADMIN_PASSWORD` | Bootstrap administrator credentials. |
| `SMTP_USER`, `SMTP_PASSWORD`, `ADMIN_EMAIL` | Mail configuration. SMTP host defaults to Gmail on port 587. |
| `PAYSTACK_SECRET_KEY` | Paystack payment and webhook signing secret. |
| `BASE_URL` | Public backend/site base URL; defaults to `https://vibegarage.app`. |
| `GOOGLE_CLIENT_ID` | Google OAuth web client ID used to verify frontend ID tokens. |
| `RESEND_API_KEY` | Verification email API key, read by the email helper. |

Do not commit `.env` or production secrets. Rotate a secret immediately if it
has been exposed.

Example development skeleton:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/vibegarage
SECRET_KEY=replace-with-a-long-random-value
SUPABASE_URL=https://example.supabase.co
SUPABASE_KEY=replace-me
MASTER_ADMIN_EMAIL=admin@example.test
MASTER_ADMIN_PASSWORD=replace-me
SMTP_USER=mailbox@example.test
SMTP_PASSWORD=replace-me
ADMIN_EMAIL=admin@example.test
PAYSTACK_SECRET_KEY=replace-me
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The service listens on `http://127.0.0.1:8000` by default. Visit `/docs` for
Swagger UI and `/openapi.json` for the machine-readable schema.

## Database workflow

1. Make a model change.
2. Generate or create a reviewed Alembic migration in `alembic/versions/`.
3. Inspect the generated SQL/migration operations.
4. Apply it locally with `alembic upgrade head`.
5. Run syntax checks and test the affected endpoint.
6. Apply migrations in the deployment process before serving code that requires
   the changed schema.

Never use `Base.metadata.create_all()` as the production migration strategy.

## Google Sign-In setup

1. In Google Cloud, create an OAuth 2.0 client for a web application.
2. Add each frontend origin to the client’s authorized JavaScript origins.
3. Put the client ID in `GOOGLE_CLIENT_ID` for the API deployment.
4. Render Google’s sign-in control in the frontend.
5. Send the resulting ID token to `POST /auth/google`.

The backend must be able to reach Google’s public certificate endpoint when it
validates an ID token. Do not send a Google access token in place of the ID
token expected by this endpoint.

## Deployment checklist

- Install the pinned requirements, including `google-auth`.
- Set every required environment variable in the deployment environment.
- Run `alembic upgrade head` and confirm `alembic current` reports the head.
- Confirm a persistent PostgreSQL database is in use.
- Configure a durable media/object-storage strategy before scaling beyond one
  instance; local `app/uploads` storage is instance-local.
- Configure Paystack webhook delivery to the public billing webhook endpoint.
- Configure allowed frontend origins in the CORS list where necessary.
- Confirm scheduler lifecycle and logs in the process manager.

## Verification commands

```bash
python -m compileall app alembic
alembic current
alembic heads
```

Exercise core smoke paths via `/docs`: signup/verify/login, `/auth/google`,
protected `/auth/me`, one public discovery endpoint, and a Paystack test-mode
payment flow.
