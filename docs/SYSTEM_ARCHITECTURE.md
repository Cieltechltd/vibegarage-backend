# VibeGarage System Architecture

## Component view

```text
Web or mobile client
        |
        v
FastAPI application (app/main.py)
        |
        +-- Routers: HTTP validation, authentication, and responses
        +-- Services: payments, storage, recommendations, email, notifications
        +-- Core: settings, JWT/password helpers, role dependencies
        +-- SQLAlchemy models and sessions
        |
        +-- PostgreSQL / Supabase-compatible database
        +-- Local uploads exposed at /static
        +-- Paystack, Resend, Google Identity Services
```

## Request lifecycle

1. `app/main.py` creates the FastAPI application, CORS middleware, local static
   mount, routers, and startup/shutdown lifecycle.
2. A router validates its request with Pydantic schemas and obtains a database
   session through `get_db` where required.
3. Protected routes use JWT and role dependencies to resolve the current user.
4. Services perform feature-specific work such as payments, storage, rewards,
   audit logging, or recommendations.
5. SQLAlchemy persists data in PostgreSQL and the router returns a JSON or
   streaming response.

## Startup and background work

At startup the application ensures local upload folders exist, creates mapped
tables, runs database bootstrap logic, and starts clip-expiry and subscription-
expiry schedulers. Schedulers are stopped during application shutdown.

Schema changes should still be applied through Alembic before deployment;
startup table creation is not a substitute for migrations.

## Authentication and authorization

- Passwords use Argon2 via Passlib.
- JWTs are signed with `SECRET_KEY`, `ALGORITHM`, and an expiry configured by
  `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Email/password accounts require email verification before normal login.
- Google ID tokens are verified server-side against `GOOGLE_CLIENT_ID`; their
  `sub` value is stored as the stable external identity.
- Admin accounts may enable TOTP two-factor authentication. The client sends
  `X-2FA-Code` on login when prompted by `X-2FA-Required: true`.
- Artist and admin endpoints enforce their relevant role dependencies.

## Integrations

| Integration | Responsibility |
| --- | --- |
| PostgreSQL / Supabase | Primary relational database connection through `DATABASE_URL`. |
| Google Identity Services | User identity token issuance; the API validates tokens with `google-auth`. |
| Resend | Verification email delivery using `RESEND_API_KEY`. |
| Paystack | Artist verification, track purchases, bank lookups, payouts, and webhooks. |
| Local file storage | Development audio, covers, avatars, and clips under `app/uploads/`. |

## CORS and static content

CORS allows the configured local frontend ports and VibeGarage domains. Add a
new production frontend origin deliberately in `app/main.py`; avoid allowing
arbitrary origins when cookies or credentials are enabled. Local upload files
are available at `/static/<type>/<filename>`.
