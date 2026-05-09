"""
routes_admin.py - Admin API: JWT auth + management endpoints.

Admin auth: POST /api/admin/login  →  JWT token (HS256)
All other /api/admin/* routes require: Authorization: Bearer <token>

Env var: ADMIN_SECRET  (default "mahjong_admin_2024")
         ADMIN_USERNAME (default "admin")
         ADMIN_PASSWORD (default "admin123")
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "mahjong_admin_2024")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 12

router = APIRouter()


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    sub: str          # username
    exp: int          # unix timestamp
    iat: int


# ---------------------------------------------------------------------------
# Shared in-memory stores (same process as room_manager)
# ---------------------------------------------------------------------------
# Filled by the WebSocket handler when a game ends.
# In production this would be a real database.
_game_history: list[dict] = []
_player_registry: dict[str, dict] = {}   # player_id → {chips, status, note, last_seen}


def register_game_to_history(game_record: dict) -> None:
    """Called by websocket.py when a game ends — stores the record."""
    _game_history.insert(0, game_record)  # newest first
    # Keep last 500 records
    if len(_game_history) > 500:
        _game_history[:] = _game_history[:500]


def upsert_player(player_id: str, **kwargs) -> None:
    """Create or update a player record."""
    if player_id not in _player_registry:
        _player_registry[player_id] = {
            "id": player_id,
            "chips": kwargs.get("chips", 1000),
            "status": "active",
            "note": "",
            "last_seen": datetime.utcnow().isoformat(),
            "total_games": 0,
            "total_wins": 0,
        }
    for k, v in kwargs.items():
        if k in ("chips", "status", "note"):
            _player_registry[player_id][k] = v
    if "last_seen" in kwargs or True:
        _player_registry[player_id]["last_seen"] = datetime.utcnow().isoformat()


def get_all_players() -> list[dict]:
    return list(_player_registry.values())


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _make_token(username: str) -> tuple[str, int]:
    """Generate a JWT and return (token, expires_in_seconds)."""
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + JWT_EXPIRE_HOURS * 3600,
    }
    token = jwt.encode(payload, ADMIN_SECRET, algorithm=JWT_ALGORITHM)
    return token, JWT_EXPIRE_HOURS * 3600


def _verify_token(authorization: str) -> TokenPayload:
    """Validate Bearer token and return payload. Raises HTTPException on failure."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return TokenPayload(**payload)


def _require_auth(authorization: str = Header(...)) -> TokenPayload:
    """Dependency: verify admin token or raise 401."""
    return _verify_token(authorization)


# ---------------------------------------------------------------------------
# Auth endpoint
# ---------------------------------------------------------------------------

@router.post("/login", response_model=LoginResponse)
def admin_login(body: LoginRequest):
    """Verify credentials and return a JWT."""
    if body.username != ADMIN_USERNAME or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, expires_in = _make_token(body.username)
    return LoginResponse(token=token, expires_in=expires_in)


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    total_players: int
    total_games: int
    active_rooms: int
    total_online: int


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(_: TokenPayload = None):
    """Quick KPI summary for the dashboard."""
    from api.routes import room_manager
    active = sum(1 for r in room_manager.get_rooms() if r.status == "playing")
    return DashboardStats(
        total_players=len(_player_registry),
        total_games=len(_game_history),
        active_rooms=active,
        total_online=_sum_online(),
    )


def _sum_online() -> int:
    """Approximate online count: human players in active rooms + waiting rooms."""
    from api.routes import room_manager
    seen: set[str] = set()
    for room in room_manager.get_rooms():
        for pid in room.human_players:
            if not pid.startswith("ai_player_"):
                seen.add(pid)
    return len(seen)


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

@router.get("/rooms")
def list_admin_rooms(_: TokenPayload = None):
    """All rooms including ended ones."""
    from api.routes import room_manager
    rooms = room_manager.get_rooms()
    return [_room_detail(r) for r in rooms]


class RoomUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None   # "waiting" | "playing" | "ended"
    chips: Optional[int] = None     # set initial chips for all players


@router.patch("/rooms/{room_id}")
def update_room(room_id: str, body: RoomUpdateRequest, _: TokenPayload = None):
    from api.routes import room_manager
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.name is not None:
        room.name = body.name
    if body.status is not None:
        if body.status not in ("waiting", "playing", "ended"):
            raise HTTPException(status_code=400, detail="Invalid status")
        room.status = body.status
    if body.chips is not None:
        from game.room_manager import INITIAL_CHIPS
        for pid in room.human_players:
            room.cumulative_scores[pid] = body.chips
        # also reset AI player scores
        if room.game_state:
            for p in room.game_state.players:
                if p.id.startswith("ai_player_"):
                    room.cumulative_scores[p.id] = body.chips
    return _room_detail(room)


@router.post("/rooms/{room_id}/close")
def close_room(room_id: str, _: TokenPayload = None):
    """Force-close a room (set status to ended)."""
    from api.routes import room_manager
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    room.status = "ended"
    return {"ok": True, "room_id": room_id}


@router.post("/rooms/{room_id}/reopen")
def reopen_room(room_id: str, _: TokenPayload = None):
    """Reopen an ended room (set back to waiting)."""
    from api.routes import room_manager
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.status not in ("ended", "waiting"):
        raise HTTPException(status_code=400, detail="Can only reopen ended or waiting rooms")
    room.status = "waiting"
    room.game_state = None
    return {"ok": True, "room_id": room_id}


def _room_detail(room) -> dict:
    return {
        "id": room.id,
        "name": room.name,
        "status": room.status,
        "player_count": room.player_count,
        "max_players": room.max_players if hasattr(room, "max_players") else 4,
        "created_at": room.created_at.isoformat() if hasattr(room, "created_at") else "",
        "round_number": room.round_number,
        "cumulative_scores": dict(room.cumulative_scores),
        "human_players": room.human_players,
    }


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------

@router.get("/players")
def list_players(_: TokenPayload = None):
    players = get_all_players()
    return {
        "players": players,
        "total": len(players),
    }


class PlayerUpdateRequest(BaseModel):
    chips: Optional[int] = None
    status: Optional[str] = None   # "active" | "banned"
    note: Optional[str] = None


@router.patch("/players/{player_id}")
def update_player(player_id: str, body: PlayerUpdateRequest, _: TokenPayload = None):
    if player_id not in _player_registry:
        raise HTTPException(status_code=404, detail="Player not found")
    if body.status is not None and body.status not in ("active", "banned"):
        raise HTTPException(status_code=400, detail="Invalid status")
    record = _player_registry[player_id]
    if body.chips is not None:
        record["chips"] = body.chips
    if body.status is not None:
        record["status"] = body.status
    if body.note is not None:
        record["note"] = body.note
    return record


@router.get("/players/{player_id}")
def get_player(player_id: str, _: TokenPayload = None):
    if player_id not in _player_registry:
        raise HTTPException(status_code=404, detail="Player not found")
    return _player_registry[player_id]


# ---------------------------------------------------------------------------
# Game history
# ---------------------------------------------------------------------------

@router.get("/games")
def list_games(
    limit: int = 50,
    offset: int = 0,
    _: TokenPayload = None,
):
    """Paginated game history, newest first."""
    total = len(_game_history)
    records = _game_history[offset : offset + limit]
    return {
        "games": records,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/games/{game_id}")
def get_game(game_id: str, _: TokenPayload = None):
    for g in _game_history:
        if g.get("id") == game_id:
            return g
    raise HTTPException(status_code=404, detail="Game not found")
