# Frontend Integration Guide

This guide explains how the frontend should interact with the VibeGarage backend.

---

# Authentication Flow

1 Register user
2 Login user
3 Store JWT token
4 Attach token to all API requests

Header example

```
Authorization: Bearer TOKEN
```

---

# Artist Workflow

1 Register
2 Login
3 Create artist profile
4 Upload tracks
5 Create album
6 Add tracks to album
7 Monitor analytics
8 Request payouts

---

# Listener Workflow

1 Register
2 Search for music
3 Play tracks
4 Like songs
5 Follow artists
6 Discover trending songs

---

# Track Upload Flow

Artist dashboard calls

```
POST /tracks/upload
```

Upload audio file and metadata.

---

# Analytics Flow

Artist dashboard fetches statistics

```
GET /artist/stats
```

Display

streams
followers
earnings

---

# Search Implementation

Search field calls

```
GET /search?q=query
```

Display

tracks
artists
albums
