

***

```markdown
# 🎸 Vibe Garage Backend API Documentation

Welcome to the **Vibe Garage** Core. This API powers the intersection of music discovery, artist branding, and social engagement.

---

## 🛠 Project Workflow & Architecture

1. **Authentication**: Users/Artists authenticate via JWT.
2. **Discovery**: The `Garage Feed` (Video Clips) and `Trending` (7-day play count) drive user engagement.
3. **Monetization (Preview Logic)**:
   - Tracks can be marked as "Premium/Paid".
   - The API provides a `preview_url` (30-second snippet) for unpaid users and a `full_url` for authorized/paid users.
4. **Verification**: 
   - Not a "Blue Check". Verification is a custom Vibe Garage status (`is_verified`).
   - Verified artists get priority sorting in the Discovery Feed.
5. **Marketing**: Every artist has a dedicated Public Storefront with Open Graph meta-tags for social sharing and a downloadable QR code.

---

## 🔐 Authentication & Roles

| Role | Permissions |
| :--- | :--- |
| **USER** | Stream music, like/comment, follow artists, view public profiles. |
| **ARTIST** | Upload tracks/clips, manage storefront, view personal analytics. |
| **ADMIN** | Moderation, system configuration, payout approvals, global stats. |

**Headers required for protected routes:** `Authorization: Bearer <JWT_TOKEN>`

---

## 📡 API Endpoints Reference

### 1. Discovery & Social Feed
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/discovery/feed` | The "TikTok-style" vertical video feed. Prioritizes verified artists. |
| `GET` | `/discovery/trending` | Top 10 tracks by play count in the last 7 days. |
| `GET` | `/discovery/new-releases` | 10 most recently uploaded tracks. |

### 2. Public Artist Profiles (No Auth Required)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/public/artists/{username}` | Returns OG metadata for social sharing + auto-redirects to UI. |
| `GET` | `/public/artists/{username}/data` | Returns raw JSON (Bio, Avatar, Stats, Tracklist). |
| `GET` | `/public/artists/{username}/qrcode` | Returns a PNG QR Code leading to the profile. |

### 3. Track & Content Management
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/tracks/{track_id}` | Fetches track details including preview/full stream logic. |
| `POST` | `/tracks/play` | Logs a play event (Required for trending algorithm). |

---

## 🎵 Handling Paid Song Previews (Frontend Logic)

When fetching a track, the API returns two specific URL fields. The frontend **MUST** check the user's access status before deciding which to play.

**Example Track Response:**
```json
{
  "id": "uuid-123",
  "title": "Summer Vibe",
  "is_premium": true,
  "preview_url": "[https://cdn.vibegarage.app/previews/uuid-123.mp3](https://cdn.vibegarage.app/previews/uuid-123.mp3)",
  "full_url": "[https://cdn.vibegarage.app/full/uuid-123.mp3](https://cdn.vibegarage.app/full/uuid-123.mp3)",
  "has_access": false
}
```

- **If `is_premium` is `false`**: Play `full_url`.
- **If `is_premium` is `true` AND `has_access` is `false`**: Play `preview_url` (30s) and show "Buy to unlock full song" UI.
- **If `is_premium` is `true` AND `has_access` is `true`**: Play `full_url`.

---

## ✅ The "Vibe Garage" Verification Badge

Our verification is **NOT** a blue checkmark. 
- Backend Field: `is_verified` (boolean).
- **Frontend Instruction**: When `is_verified` is `true`, render the **Vibe Garage Custom Stamp** (e.g., Gold Vinyl icon or VG Stamp) over the artist's avatar. Do not use standard social media icons.

---

## 📊 Core Data Models

### Artist Profile (`/public/artists/{username}/data`)
```json
{
  "stage_name": "Utee Jacob",
  "avatar": "https://...",
  "is_verified": true,
  "bio": "Software Engineer & Music Visionary",
  "stats": {
    "total_streams": 45800,
    "track_count": 12
  },
  "joined_date": "January 2026"
}
```

### Garage Clip (Feed Item)
```json
{
  "clip_id": 50,
  "video_url": "https://...",
  "caption": "New single dropping soon!",
  "artist": {
    "username": "uteejacob",
    "is_verified": true,
    "avatar": "https://..."
  },
  "meta": {
    "has_lyrics": true,
    "track_id": "uuid-789"
  }
}
```

---

## ⚠️ Error Handling
- `401 Unauthorized`: Token missing or expired.
- `402 Payment Required`: Attempted to access `full_url` on a premium track without ownership.
- `404 Not Found`: Artist or Track does not exist.
- `422 Unprocessable Entity`: Check `detail` for field validation errors.

---

## 🛠 Installation for Local Testing
1. Ensure `Python 3.10+` and `PostgreSQL` are installed.
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `alembic upgrade head`
4. Start Server: `uvicorn app.main:app --reload`
```





# License

MIT License
