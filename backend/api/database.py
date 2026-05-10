"""
SQLite database layer for Mahjong backend.
Zero external dependencies — uses stdlib sqlite3.
"""
from __future__ import annotations
import sqlite3
import os
import json
import threading
from datetime import datetime
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "mahjong.db")
_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """Thread-local connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


@contextmanager
def get_db():
    conn = get_conn()
    try:
        yield conn
    finally:
        pass  # keep connection open for reuse


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    cursor = conn.cursor()

    # Players
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            phone TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            chips INTEGER NOT NULL DEFAULT 10000,
            role TEXT NOT NULL DEFAULT 'player',
            status TEXT NOT NULL DEFAULT 'active',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    """)
    # Add missing columns if they don't exist (for existing databases)
    for col, col_type in [("username", "TEXT"), ("password_hash", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE players ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # column already exists

    # Rooms
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting',
            max_players INTEGER NOT NULL DEFAULT 4,
            current_players INTEGER NOT NULL DEFAULT 0,
            initial_chips INTEGER NOT NULL DEFAULT 1000,
            dealer_idx INTEGER NOT NULL DEFAULT 0,
            round_num INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Games (history)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL,
            room_name TEXT NOT NULL,
            winner_id TEXT NOT NULL,
            winner_name TEXT NOT NULL,
            win_type TEXT NOT NULL DEFAULT 'rong',
            final_scores TEXT NOT NULL,
            chip_changes TEXT NOT NULL,
            han_details TEXT NOT NULL DEFAULT '[]',
            total_rounds INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # Game participants
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            final_score INTEGER NOT NULL,
            chip_change INTEGER NOT NULL,
            is_winner INTEGER NOT NULL DEFAULT 0,
            hand_tiles TEXT NOT NULL DEFAULT '[]',
            melds TEXT NOT NULL DEFAULT '[]',
            FOREIGN KEY (game_id) REFERENCES games(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    conn.commit()
    return conn


def row_to_player(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "phone": row["phone"],
        "name": row["name"],
        "chips": row["chips"],
        "role": row["role"],
        "status": row["status"],
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def row_to_room(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "status": row["status"],
        "max_players": row["max_players"],
        "current_players": row["current_players"],
        "initial_chips": row["initial_chips"],
        "dealer_idx": row["dealer_idx"],
        "round_num": row["round_num"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def row_to_game(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "room_id": row["room_id"],
        "room_name": row["room_name"],
        "winner_id": row["winner_id"],
        "winner_name": row["winner_name"],
        "win_type": row["win_type"],
        "final_scores": json.loads(row["final_scores"]),
        "chip_changes": json.loads(row["chip_changes"]),
        "han_details": json.loads(row["han_details"]),
        "total_rounds": row["total_rounds"],
        "created_at": row["created_at"],
    }


# ── Players ──────────────────────────────────────────────

def upsert_player(player_id: str, phone: str, name: str = "") -> dict:
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO players (id, phone, name, chips, status, note, created_at, updated_at)
        VALUES (?, ?, ?, 10000, 'active', '', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            phone=excluded.phone,
            name=excluded.name,
            updated_at=excluded.updated_at
    """, (player_id, phone, name, now, now))
    conn.commit()
    return get_player(player_id)


def get_player(player_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        row = cursor.fetchone()
        return row_to_player(row) if row else None


def create_guest(guest_id: str, name: str = "游客") -> dict:
    """创建游客账号（guest_id 即为 player_id）"""
    with get_db() as conn:
        from datetime import datetime
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO players (id, phone, name, chips, status, note, created_at, updated_at)
            VALUES (?, ?, ?, 10000, 'active', 'guest', ?, ?)
        """, (guest_id, f"guest_{guest_id}", name, now, now))
        conn.commit()
    return get_player(guest_id)


def get_player_by_phone(phone: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        return row_to_player(row) if row else None


def list_players(status: str = None, search: str = None,
                  limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    with get_db() as conn:
        cursor = conn.cursor()
        where, params = [], []
        if status:
            where.append("status = ?")
            params.append(status)
        if search:
            where.append("(name LIKE ? OR phone LIKE ? OR id LIKE ?)")
            s = f"%{search}%"
            params.extend([s, s, s])
        sql = "SELECT * FROM players"
        if where:
            sql += " WHERE " + " AND ".join(where)
        cursor.execute(f"SELECT COUNT(*) FROM players" +
                      (f" WHERE {' AND '.join(where)}" if where else ""),
                      params)
        total = cursor.fetchone()[0]
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(sql, params)
        return [row_to_player(r) for r in cursor.fetchall()], total


def update_player(player_id: str, chips: int = None, status: str = None,
                  note: str = None, name: str = None) -> dict | None:
    now = datetime.utcnow().isoformat()
    fields, params = ["updated_at = ?"], [now]
    if chips is not None:
        fields.append("chips = ?")
        params.append(chips)
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if note:
        fields.append("note = ?")
        params.append(note)
    if name:
        fields.append("name = ?")
        params.append(name)
    params.append(player_id)
    conn = get_conn()
    conn.execute("UPDATE players SET " + ", ".join(fields) + " WHERE id = ?", params)
    conn.commit()
    return get_player(player_id)


def reset_player_chips(player_id: str, amount: int = 10000) -> dict | None:
    return update_player(player_id, chips=amount)


def create_player(phone: str, name: str = "", chips: int = 10000) -> dict:
    """Create a new player manually. Returns the created player or raises ValueError."""
    import uuid
    now = datetime.utcnow().isoformat()
    player_id = f"p_{uuid.uuid4().hex[:10]}"
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO players (id, phone, name, chips, status, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', '', ?, ?)
        """, (player_id, phone, name, chips, now, now))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("该手机号已注册")
    return get_player(player_id)


def delete_player(player_id: str) -> bool:
    """Delete a player. Returns True if deleted, False if not found."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE id = ?", (player_id,))
    conn.commit()
    return cursor.rowcount > 0


def get_all_player_chips() -> dict:
    """Return {player_id: chips} for all active players."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, chips FROM players WHERE status = 'active'")
        return {r["id"]: r["chips"] for r in cursor.fetchall()}


# ── Leaderboard ───────────────────────────────────────────

def get_leaderboard(limit: int = 20) -> list[dict]:
    """Top players by chips."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.phone, p.chips, p.status,
                   COUNT(g.id) as games_played,
                   SUM(CASE WHEN gp.chip_change > 0 THEN 1 ELSE 0 END) as wins,
                   COALESCE(SUM(gp.chip_change), 0) as total_change
            FROM players p
            LEFT JOIN game_participants gp ON gp.player_id = p.id
            LEFT JOIN games g ON g.id = gp.game_id
            WHERE p.status = 'active'
            GROUP BY p.id
            ORDER BY p.chips DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"] or r["phone"],
                "chips": r["chips"],
                "status": r["status"],
                "games_played": r["games_played"] or 0,
                "wins": r["wins"] or 0,
                "total_change": r["total_change"] or 0,
                "win_rate": round((r["wins"] or 0) / max(r["games_played"] or 1, 1) * 100, 1),
            }
            for r in rows
        ]


# ── Player Game History ───────────────────────────────────

def get_player_games(player_id: str, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    """Games a player participated in."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM games g JOIN game_participants gp ON gp.game_id = g.id WHERE gp.player_id = ?", (player_id,))
        total = cursor.fetchone()[0]
        cursor.execute("""
            SELECT g.id, g.winner_id, g.winner_name,
                   g.win_type, g.created_at,
                   gp.chip_change,
                   GROUP_CONCAT(gp2.player_id || ':' || COALESCE(gp2.chip_change, 0)) as all_players
            FROM games g
            JOIN game_participants gp ON gp.game_id = g.id
            JOIN game_participants gp2 ON gp2.game_id = g.id
            WHERE gp.player_id = ?
            GROUP BY g.id
            ORDER BY g.created_at DESC
            LIMIT ? OFFSET ?
        """, (player_id, limit, offset))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            all_players = []
            if r["all_players"]:
                for entry in (r["all_players"] or "").split(","):
                    if ":" in entry:
                        pid, change = entry.split(":", 1)
                        all_players.append({"player_id": pid, "chip_change": int(change) if change else 0})
            result.append({
                "id": r["id"],
                "winner_id": r["winner_id"],
                "winner_name": r["winner_name"],
                "win_type": r["win_type"],
                "ended_at": r["created_at"],
                "chip_change": r["chip_change"],
                "all_players": all_players,
                "is_winner": r["winner_id"] == player_id,
            })
        return result, total


# ── Tournaments ───────────────────────────────────────────

TOURNAMENTS = [
    {"id": 1, "name": "日挑战赛", "entry_fee": 500, "max_players": 50, "players_count": 0,
     "rounds": 8, "prize_pool": 50000, "status": "upcoming",
     "start_time": "2026-05-15 20:00", "desc": "每日晚8点，争夺排行榜"},
    {"id": 2, "name": "周冠军赛", "entry_fee": 2000, "max_players": 100, "players_count": 0,
     "rounds": 12, "prize_pool": 200000, "status": "upcoming",
     "start_time": "2026-05-18 19:00", "desc": "周末争霸，千元入场"},
    {"id": 3, "name": "新人杯", "entry_fee": 0, "max_players": 200, "players_count": 0,
     "rounds": 6, "prize_pool": 0, "status": "live",
     "start_time": "2026-05-10 14:00", "desc": "新手友好，免费参加"},
    {"id": 4, "name": "大师赛 #7", "entry_fee": 5000, "max_players": 30, "players_count": 18,
     "rounds": 16, "prize_pool": 500000, "status": "ended",
     "start_time": "2026-05-03 20:00", "desc": "每月大师赛，奖金翻倍"},
]


def list_tournaments() -> dict:
    live, upcoming, ended = [], [], []
    for t in TOURNAMENTS:
        if t["status"] == "live":
            live.append(t)
        elif t["status"] == "upcoming":
            upcoming.append(t)
        else:
            ended.append(t)
    return {"live": live, "upcoming": upcoming, "ended": ended}


def admin_get_stats() -> dict:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM players WHERE status = 'active'")
        active_players = c.fetchone()[0]
        c.execute("SELECT SUM(chips) FROM players WHERE status = 'active'")
        total_chips = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM rooms")
        total_rooms = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM rooms WHERE status = 'playing'")
        active_rooms = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM games")
        total_games = c.fetchone()[0]
        return {
            "active_players": active_players,
            "total_chips": total_chips,
            "total_rooms": total_rooms,
            "active_rooms": active_rooms,
            "total_games": total_games,
        }


# ── Rooms ────────────────────────────────────────────────

def upsert_room(room_id: str, name: str, max_players: int = 4,
                 initial_chips: int = 1000, status: str = "waiting") -> dict:
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute("""
        INSERT INTO rooms (id, name, status, max_players, current_players,
                          initial_chips, dealer_idx, round_num, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, ?, 0, 0, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, status=excluded.status,
            max_players=excluded.max_players,
            initial_chips=excluded.initial_chips, updated_at=excluded.updated_at
    """, (room_id, name, status, max_players, initial_chips, now, now))
    conn.commit()
    return get_room(room_id)


def get_room(room_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rooms WHERE id = ?", (room_id,))
        row = cursor.fetchone()
        return row_to_room(row) if row else None


def list_rooms(status: str = None, search: str = None,
               limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    with get_db() as conn:
        cursor = conn.cursor()
        where, params = [], []
        if status:
            where.append("status = ?")
            params.append(status)
        if search:
            where.append("(name LIKE ? OR id LIKE ?)")
            s = f"%{search}%"
            params.extend([s, s])
        base = "SELECT * FROM rooms"
        if where:
            base += " WHERE " + " AND ".join(where)
        cursor.execute("SELECT COUNT(*) FROM rooms" +
                       (" WHERE " + " AND ".join(where) if where else ""),
                       params)
        total = cursor.fetchone()[0]
        cursor.execute(base + " ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                       params + [limit, offset])
        return [row_to_room(r) for r in cursor.fetchall()], total


def update_room(room_id: str, name: str = None, status: str = None,
                current_players: int = None, round_num: int = None,
                reset_game: bool = False) -> dict | None:
    now = datetime.utcnow().isoformat()
    fields, params = ["updated_at = ?"], [now]
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if current_players is not None:
        fields.append("current_players = ?")
        params.append(current_players)
    if round_num is not None:
        fields.append("round_num = ?")
        params.append(round_num)
    if reset_game:
        fields.extend(["status = ?", "current_players = ?", "round_num = ?"])
        params.extend(["waiting", 0, 0])
    params.append(room_id)
    conn = get_conn()
    conn.execute("UPDATE rooms SET " + ", ".join(fields) + " WHERE id = ?", params)
    conn.commit()
    return get_room(room_id)


# ── Games ────────────────────────────────────────────────

def save_game(game_id: str, room_id: str, room_name: str,
              winner_id: str, winner_name: str, win_type: str,
              final_scores: dict, chip_changes: dict,
              han_details: list, total_rounds: int) -> dict:
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute("""
        INSERT INTO games (id, room_id, room_name, winner_id, winner_name,
                         win_type, final_scores, chip_changes, han_details,
                         total_rounds, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (game_id, room_id, room_name, winner_id, winner_name, win_type,
          json.dumps(final_scores, ensure_ascii=False),
          json.dumps(chip_changes, ensure_ascii=False),
          json.dumps(han_details, ensure_ascii=False),
          total_rounds, now))
    conn.commit()
    return get_game(game_id)


def save_game_participant(game_id: str, player_id: str, player_name: str,
                          final_score: int, chip_change: int,
                          is_winner: bool, hand_tiles: list, melds: list):
    conn = get_conn()
    conn.execute("""
        INSERT INTO game_participants
        (game_id, player_id, player_name, final_score, chip_change,
         is_winner, hand_tiles, melds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (game_id, player_id, player_name, final_score, chip_change,
          1 if is_winner else 0,
          json.dumps(hand_tiles, ensure_ascii=False),
          json.dumps(melds, ensure_ascii=False)))
    conn.commit()


def get_game(game_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        return row_to_game(row) if row else None


def list_games(room_id: str = None, winner_id: str = None,
               limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    with get_db() as conn:
        cursor = conn.cursor()
        where, params = [], []
        if room_id:
            where.append("room_id = ?")
            params.append(room_id)
        if winner_id:
            where.append("winner_id = ?")
            params.append(winner_id)
        base = "SELECT * FROM games"
        if where:
            base += " WHERE " + " AND ".join(where)
        cursor.execute("SELECT COUNT(*) FROM games" +
                       (" WHERE " + " AND ".join(where) if where else ""),
                       params)
        total = cursor.fetchone()[0]
        cursor.execute(base + " ORDER BY created_at DESC LIMIT ? OFFSET ?",
                       params + [limit, offset])
        return [row_to_game(r) for r in cursor.fetchall()], total


def get_game_participants(game_id: str) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM game_participants WHERE game_id = ? ORDER BY id",
            (game_id,))
        return [{
            "player_id": r["player_id"],
            "player_name": r["player_name"],
            "final_score": r["final_score"],
            "chip_change": r["chip_change"],
            "is_winner": bool(r["is_winner"]),
            "hand_tiles": json.loads(r["hand_tiles"]),
            "melds": json.loads(r["melds"]),
        } for r in cursor.fetchall()]


def get_player_game_stats(player_id: str) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM game_participants WHERE player_id = ? AND is_winner = 1",
            (player_id,))
        wins = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM game_participants WHERE player_id = ?", (player_id,))
        total = cursor.fetchone()[0]
        cursor.execute(
            "SELECT SUM(chip_change) FROM game_participants WHERE player_id = ?",
            (player_id,))
        total_change = cursor.fetchone()[0] or 0
        return {"wins": wins, "total": total, "total_change": total_change}


# Initialise on import
init_db()


# ── Auth helpers (used by routes.py / models.py) ────────────────────────────

def verify_password(username: str, password: str):
    """Verify username + password. Returns player dict or None."""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT id, phone, name, chips, status, username, password_hash FROM players WHERE username = ?",
            (username,)
        )
        row = cur.fetchone()
        if not row:
            return None
        d = dict(zip(["id","phone","name","chips","status","username","password_hash"], row))
        if d["password_hash"] and d["password_hash"] == password:
            return d
        return None
