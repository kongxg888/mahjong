"""
In-memory models backed by SQLite (database.py).
These mirror the original in-memory class shapes so routes.py / websocket.py
don't need to change their field access patterns.
"""
import uuid
import random
import string
from datetime import datetime
from . import database


def new_id(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:10]}"

def gen_player_id():
    return f"p_{uuid.uuid4().hex[:12]}"

def gen_room_id():
    return f"room_{uuid.uuid4().hex[:10]}"

def gen_game_id():
    return f"game_{uuid.uuid4().hex[:10]}"

def now_iso():
    return datetime.utcnow().isoformat()


class Player:
    def __init__(self, id=None, phone="", name="", chips=10000,
                 role="player", status="active", note=""):
        self.id = id or gen_player_id()
        self.phone = phone
        self.name = name or f"玩家{self.id[-4:]}"
        self.chips = chips
        self.role = role
        self.status = status  # active | banned
        self.note = note
        self.created_at = now_iso()
        self.updated_at = now_iso()

    def to_dict(self):
        return {
            "id": self.id,
            "phone": self.phone,
            "name": self.name,
            "chips": self.chips,
            "role": self.role,
            "status": self.status,
            "note": self.note,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(d):
        p = Player()
        p.id = d.get("id", p.id)
        p.phone = d.get("phone", "")
        p.name = d.get("name", p.name)
        p.chips = d.get("chips", 10000)
        p.role = d.get("role", "player")
        p.status = d.get("status", "active")
        p.note = d.get("note", "")
        p.created_at = d.get("created_at", now_iso())
        p.updated_at = d.get("updated_at", now_iso())
        return p


class Room:
    def __init__(self, id=None, name="", max_players=4,
                 initial_chips=1000, status="waiting"):
        self.id = id or gen_room_id()
        self.name = name
        self.max_players = max_players
        self.current_players = 0
        self.initial_chips = initial_chips
        self.status = status  # waiting | playing | ended
        self.dealer_idx = 0
        self.round_num = 0
        self.created_at = now_iso()
        self.updated_at = now_iso()
        self.players = []       # list[Player]
        self.seats = {}         # player_id -> seat_index

    def to_dict(self, include_secrets=False):
        return {
            "id": self.id,
            "name": self.name,
            "max_players": self.max_players,
            "current_players": self.current_players,
            "initial_chips": self.initial_chips,
            "status": self.status,
            "dealer_idx": self.dealer_idx,
            "round_num": self.round_num,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(d):
        r = Room()
        r.id = d.get("id", r.id)
        r.name = d.get("name", "")
        r.max_players = d.get("max_players", 4)
        r.current_players = d.get("current_players", 0)
        r.initial_chips = d.get("initial_chips", 1000)
        r.status = d.get("status", "waiting")
        r.dealer_idx = d.get("dealer_idx", 0)
        r.round_num = d.get("round_num", 0)
        r.created_at = d.get("created_at", now_iso())
        r.updated_at = d.get("updated_at", now_iso())
        r.players = []
        r.seats = {}
        return r


# ── helpers that delegate to database.py ──────────────────────────────

def upsert_player(player_id, phone, name=""):
    return database.upsert_player(player_id, phone, name)

def get_player(player_id):
    return database.get_player(player_id)

def list_players(status=None, search=None, limit=50, offset=0):
    return database.list_players(status=status, search=search, limit=limit, offset=offset)

def update_player(player_id, chips=None, status=None, note=None, name=None):
    return database.update_player(player_id, chips=chips, status=status, note=note, name=name)

def get_player_by_phone(phone):
    return database.get_player_by_phone(phone)

def update_player_chips(player_id, chips):
    return database.update_player(player_id, chips=chips)

def reset_player_chips(player_id, amount=10000):
    return database.reset_player_chips(player_id, amount)

def get_all_player_chips():
    return database.get_all_player_chips()

def upsert_room(room_id, name, max_players=4, initial_chips=1000, status="waiting"):
    return database.upsert_room(room_id, name, max_players, initial_chips, status)

def get_room(room_id):
    return database.get_room(room_id)

def list_rooms(status=None, search=None, limit=50, offset=0):
    return database.list_rooms(status=status, search=search, limit=limit, offset=offset)

def update_room(room_id, **kwargs):
    return database.update_room(room_id, **kwargs)

def save_game(game_id, room_id, room_name, winner_id, winner_name,
             win_type, final_scores, chip_changes, han_details, total_rounds):
    return database.save_game(game_id, room_id, room_name, winner_id,
                              winner_name, win_type, final_scores,
                              chip_changes, han_details, total_rounds)

def save_game_participant(game_id, player_id, player_name,
                         final_score, chip_change, is_winner,
                         hand_tiles, melds):
    database.save_game_participant(game_id, player_id, player_name,
                                   final_score, chip_change,
                                   is_winner, hand_tiles, melds)

def get_game(game_id):
    return database.get_game(game_id)

def get_game_participants(game_id):
    return database.get_game_participants(game_id)

def admin_get_stats():
    return database.admin_get_stats()

def get_leaderboard(limit=20):
    return database.get_leaderboard(limit=limit)

def get_player_games(player_id, limit=20, offset=0):
    return database.get_player_games(player_id, limit=limit, offset=offset)

def list_tournaments():
    return database.list_tournaments()


def verify_password(username: str, password: str):
    return database.verify_password(username, password)


def list_rooms(status: str = None, search: str = None, limit: int = 50, offset: int = 0):
    return database.list_rooms(status, search, limit, offset)


def get_leaderboard(limit: int = 50):
    return database.get_leaderboard(limit)


def create_or_get_guest(guest_id: str, name: str = "游客") -> dict:
    """创建或获取游客"""
    existing = database.get_player(guest_id)
    if existing:
        return existing
    return database.create_guest(guest_id, name)
