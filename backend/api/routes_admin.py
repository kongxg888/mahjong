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
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from . import database, models

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "mahjong_admin_2024")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 12

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _make_token(username: str) -> tuple[str, int]:
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + JWT_EXPIRE_HOURS * 3600,
    }
    token = jwt.encode(payload, ADMIN_SECRET, algorithm=JWT_ALGORITHM)
    return token, JWT_EXPIRE_HOURS * 3600


def _verify_token(authorization: str) -> TokenPayload:
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
    return _verify_token(authorization)


# ---------------------------------------------------------------------------
# Auth endpoint
# ---------------------------------------------------------------------------

@router.post("/login", response_model=LoginResponse)
def admin_login(body: LoginRequest):
    if body.username != ADMIN_USERNAME or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, expires_in = _make_token(body.username)
    return LoginResponse(token=token, expires_in=expires_in)


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def dashboard_stats(___: TokenPayload = Depends(_require_auth)):
    stats = database.admin_get_stats()
    # 在线人数从 websocket.py 的 room_manager 获取
    try:
        from api.routes import room_manager
        rooms = room_manager.get_rooms()
        total_online = sum(1 for r in rooms if isinstance(r, dict) and r.get("status") == "playing")
        stats["total_online"] = total_online
    except Exception:
        stats["total_online"] = stats.get("active_rooms", 0)
    return stats


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

@router.get("/rooms")
def list_admin_rooms(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    ___: TokenPayload = Depends(_require_auth),
):
    rooms, total = database.list_rooms(status=status, search=search,
                                        limit=limit, offset=offset)
    return {"rooms": rooms, "total": total, "limit": limit, "offset": offset}


class RoomUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    initial_chips: Optional[int] = None


@router.patch("/rooms/{room_id}")
def update_room(room_id: str, body: RoomUpdateRequest, ___: TokenPayload = Depends(_require_auth)):
    room = database.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    updated = database.update_room(
        room_id,
        name=body.name,
        status=body.status,
    )
    return updated


@router.post("/rooms/{room_id}/close")
def close_room(room_id: str, ___: TokenPayload = Depends(_require_auth)):
    room = database.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    database.update_room(room_id, status="ended")
    return {"ok": True, "room_id": room_id}


@router.post("/rooms/{room_id}/reopen")
def reopen_room(room_id: str, ___: TokenPayload = Depends(_require_auth)):
    room = database.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    database.update_room(room_id, status="waiting")
    return {"ok": True, "room_id": room_id}


@router.post("/rooms/{room_id}/start")
def admin_start_room(room_id: str, ___: TokenPayload = Depends(_require_auth)):
    """手动开局：等待中的房间，手动开始游戏"""
    room = database.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["status"] != "waiting":
        raise HTTPException(status_code=400, detail="只能对等待中的房间开局")
    updated = database.update_room(room_id, status="playing")
    return {"ok": True, "room": updated}


@router.post("/rooms/{room_id}/force_end")
def force_end_room(room_id: str, ___: TokenPayload = Depends(_require_auth)):
    """强制结束：进行中的房间，强制终止游戏，重置房间状态"""
    room = database.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["status"] == "ended":
        raise HTTPException(status_code=400, detail="房间已结束，无需强制结束")
    # 重置游戏状态：改为 waiting，人数归零，局数归零
    updated = database.update_room(room_id, reset_game=True)
    return {"ok": True, "room": updated}


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------

@router.get("/players")
def list_players(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    ___: TokenPayload = Depends(_require_auth),
):
    players, total = database.list_players(status=status, search=search,
                                           limit=limit, offset=offset)
    # 补充战绩数据
    result = []
    for p in players:
        stats = database.get_player_game_stats(p["id"])
        result.append({**p, **stats})
    return {"players": result, "total": total, "limit": limit, "offset": offset}


class PlayerUpdateRequest(BaseModel):
    chips: Optional[int] = None
    status: Optional[str] = None
    note: Optional[str] = None
    name: Optional[str] = None


@router.patch("/players/{player_id}")
def update_player(player_id: str, body: PlayerUpdateRequest, ___: TokenPayload = Depends(_require_auth)):
    player = database.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    # normal -> active (统一命名)
    effective_status = body.status
    if effective_status == "normal":
        effective_status = "active"
    if effective_status is not None and effective_status not in ("active", "frozen", "banned"):
        raise HTTPException(status_code=400, detail="Invalid status")
    updated = database.update_player(
        player_id,
        chips=body.chips,
        status=effective_status,
        note=body.note if body.note and body.note.strip() else None,
        name=body.name if body.name and body.name.strip() else None,
    )
    return updated


@router.post("/players/{player_id}/reset-chips")
def reset_chips(player_id: str, amount: int = 10000, ___: TokenPayload = Depends(_require_auth)):
    """重置玩家筹码到指定数额（默认10000）。"""
    player = database.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    updated = database.reset_player_chips(player_id, amount)
    return {"ok": True, "player": updated}


@router.get("/players/{player_id}")
def get_player(player_id: str, ___: TokenPayload = Depends(_require_auth)):
    player = database.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    stats = database.get_player_game_stats(player_id)
    return {**player, **stats}


class CreatePlayerRequest(BaseModel):
    phone: str
    name: str = ""
    chips: int = 10000


@router.post("/players")
def create_player_endpoint(body: CreatePlayerRequest, ___: TokenPayload = Depends(_require_auth)):
    if not body.phone.strip():
        raise HTTPException(status_code=400, detail="手机号不能为空")
    if len(body.phone) < 11:
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    try:
        player = database.create_player(
            phone=body.phone.strip(),
            name=body.name.strip() if body.name else "",
            chips=body.chips,
        )
        return {"ok": True, "player": player}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/players/{player_id}")
def delete_player_endpoint(player_id: str, ___: TokenPayload = Depends(_require_auth)):
    player = database.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    ok = database.delete_player(player_id)
    if not ok:
        raise HTTPException(status_code=500, detail="删除失败")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Game history
# ---------------------------------------------------------------------------

@router.get("/games")
def list_games(
    room_id: Optional[str] = None,
    winner_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    ___: TokenPayload = Depends(_require_auth),
):
    games, total = database.list_games(room_id=room_id, winner_id=winner_id,
                                        limit=limit, offset=offset)
    return {"games": games, "total": total, "limit": limit, "offset": offset}


@router.get("/games/{game_id}")
def get_game(game_id: int, ___: TokenPayload = Depends(_require_auth)):
    game = database.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")
    return dict(game)


@router.get("/games/{game_id}/participants")
def get_game_participants(game_id: int, ___: TokenPayload = Depends(_require_auth)):
    rows = database.get_game_participants(game_id)
    return rows


@router.get("/games/{game_id}/han")
def get_game_han(game_id: int, ___: TokenPayload = Depends(_require_auth)):
    rows = database.get_game_han(game_id)
    return {"han": rows}
