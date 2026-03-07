# VibeGarage Backend

VibeGarage is a modern music streaming platform that allows artists to upload music, grow their audience, and earn revenue from streams while listeners discover new music.

This repository contains the backend API that powers the VibeGarage platform.

The backend is built using FastAPI and provides APIs for artist dashboards, listener experiences, analytics, streaming, and monetization.

---

# Tech Stack

Backend Framework
FastAPI

Language
Python

Database
PostgreSQL

ORM
SQLAlchemy

Authentication
JWT (JSON Web Tokens)

File Storage
Local uploads (audio files, images)

Migrations
Alembic

Server
Uvicorn / ASGI

---

# Project Structure

```
app/
│
├── main.py
│
├── core/
│   ├── config.py
│   ├── security.py
│
├── db/
│   ├── database.py
│
├── models/
│   ├── user.py
│   ├── track.py
│   ├── album.py
│
├── schemas/
│   ├── user.py
│   ├── track.py
│   ├── album.py
│
├── routers/
│   ├── auth.py
│   ├── user.py
│   ├── artist.py
│   ├── track.py
│   ├── album.py
│   ├── search.py
│   ├── trending.py
│   ├── clips.py
│   ├── lyrics.py
│   ├── payments.py
│   ├── payouts.py
│   └── admin.py
│
├── services/
│
└── uploads/
```

---

# Installation

Clone the repository

```
git clone https://github.com/Cieltechltd/vibegarage-backend
cd vibegarage-backend
```

Create virtual environment

```
python3 -m venv venv
source venv/bin/activate
```

Install dependencies

```
pip install -r requirements.txt
```

Run database migrations

```
alembic upgrade head
```

Run the server

```
uvicorn app.main:app --reload
```

Server will start at

```
http://127.0.0.1:8000
```

---

# API Documentation

Swagger UI

```
/docs
```

---

# Core Features

Artist System
Artists can upload tracks, create albums, add lyrics and monitor performance.

Music Upload
Supports audio uploads with metadata such as genre, title and cover art.

Search
Users can search artists, tracks and albums.

Trending System
Tracks trending music across the platform.

Music Clips
Short-form music content similar to TikTok clips.

Analytics
Artists can view engagement metrics such as streams and followers.

Monetization
Artists earn revenue through streams and can request payouts.

Admin Panel
Admins can manage users, artists, tracks and platform statistics.

---

# Environment Variables

Create a `.env` file

```

```

---

# Documentation

Detailed developer documentation is available in the `/docs` directory.

API Reference
docs/API_REFERENCE.md

Frontend Integration Guide
docs/FRONTEND_GUIDE.md

System Architecture
docs/SYSTEM_ARCHITECTURE.md

Database Overview
docs/DATABASE_OVERVIEW.md

---

# License

MIT License
