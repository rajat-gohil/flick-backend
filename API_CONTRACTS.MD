# Backend API Contract (Frozen)

Status: FROZEN ✅  
Date: 2026-01-09

## Auth
POST /api/auth/register/
POST /api/auth/login/

## Genres
GET /api/genres/

## Sessions
POST /api/sessions/create/
POST /api/sessions/join/
POST /api/sessions/end/
GET  /api/sessions/<id>/
GET  /api/sessions/status/?code=

## Movies
GET /api/movies/
GET /api/movies/<id>/
POST /api/movies/sync-tmdb/ (admin only)

## Swipes
POST   /api/swipes/
DELETE /api/swipes/undo/
GET    /api/swipes/history/

## Matches
GET /api/matches/

## Recommendations
GET /api/recommendations/?session_id=

### Rules
- Sessions support multiple matches
- A movie can match only once per session
- Sessions are ended via ended_at (not deleted)
- All auth via DRF tokens

No breaking changes allowed without a new version.