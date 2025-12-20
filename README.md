VibeGarage Backend API

Description:
Backend API for VibeGarage, a music streaming platform. Built with FastAPI and Python, handling authentication, artist management, track uploads, listener dashboards, search, and monetization logic.

🗂 Project Structure

🔑 Authentication

JWT-based

Endpoints:

POST /auth/signup → create account

POST /auth/login → login, returns access token

Notes:

Only artists can upload tracks and edit profiles.

Listeners have access to dashboard and liked/followed data.

🎤 Artist Endpoints

GET /artist/profile → view artist profile

PUT /artist/profile → update artist info (stage_name)

Upload tracks, manage plays, likes (already implemented).

🔎 Search Endpoints

GET /search/tracks?q=<query> → search tracks by title or artist stage name

GET /search/artists?q=<query> → search artists by stage name

Responses:

Clean JSON via Pydantic schemas

Includes track info, artist info, play/like counts

🎧 Listener Endpoints

GET /listener/dashboard → summary for listener (liked tracks, followed artists, listening stats)

GET /listener/detail → detailed listener info

(Future) trending tracks, recommended tracks

💰 Monetization Logic

Artists earn revenue only after 10,000 streams or 150 followers

Streams count only if ads played

Endpoints expose artist eligibility and earnings status


test merge