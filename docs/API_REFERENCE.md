# VibeGarage API Reference

Base URL

```
/api/v1
```

All endpoints return JSON responses.

Authentication uses JWT tokens.

---

# Authentication

## Register

POST /auth/register

Request

```
{
  "username": "artist1",
  "email": "artist@email.com",
  "password": "password"
}
```

Response

```
{
  "id": 1,
  "username": "artist1",
  "email": "artist@email.com"
}
```

---

## Login

POST /auth/login

Response

```
{
  "access_token": "JWT_TOKEN",
  "token_type": "bearer"
}
```

---

# User

## Get Current User

GET /users/me

---

# Artist

## Create Artist Profile

POST /artist/profile

Request

```
{
  "stage_name": "DJ Sky",
  "bio": "Afrobeats artist"
}
```

---

# Tracks

## Upload Track

POST /tracks/upload

Multipart Form Data

Fields

title
genre
audio_file
cover_image
album_id (optional)

---

## Get My Tracks

GET /tracks/my-tracks

---

## Update Track

PUT /tracks/{track_id}

---

## Delete Track

DELETE /tracks/{track_id}

---

# Albums

## Create Album

POST /albums

---

## Get My Albums

GET /albums/my-albums

---

# Search

GET /search?q=keyword

Search across tracks, artists and albums.

---

# Trending

GET /trending

Returns trending tracks.

---

# Lyrics

POST /lyrics

GET /lyrics/{track_id}

---

# Clips

POST /clips/upload

GET /clips/trending

---

# Artist Analytics

GET /artist/stats

Returns

total_streams
followers
earnings

---

# Payments

POST /payments

Handles listener payments and subscriptions.

---

# Payouts

POST /payouts/request

Artists request withdrawals.

GET /payouts/history

---

# Admin

GET /admin/users

GET /admin/tracks

DELETE /admin/track/{id}

---

# Error Format

```
{
 "detail": "Error message"
}
```
