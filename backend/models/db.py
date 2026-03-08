import os
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure

_client = None
_db = None

# Collection references (set after init_db is called)
users = None
sessions = None
liked_songs = None
playlists = None
playlist_follows = None
listening_history = None
followers = None


def get_db():
    global _client, _db
    if _db is None:
        init_db()
    return _db


def init_db():
    global _client, _db
    global users, sessions, liked_songs, playlists
    global playlist_follows, listening_history, followers

    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI environment variable is not set")

    _client = MongoClient(uri)
    _db = _client["music_app_db"]

    # Bind collection references
    users = _db["users"]
    sessions = _db["sessions"]
    liked_songs = _db["liked_songs"]
    playlists = _db["playlists"]
    playlist_follows = _db["playlist_follows"]
    listening_history = _db["listening_history"]
    followers = _db["followers"]

    # Create indexes
    users.create_index([("username", ASCENDING)], unique=True)
    liked_songs.create_index([("user_id", ASCENDING), ("song_id", ASCENDING)], unique=True)
    listening_history.create_index([("user_id", ASCENDING), ("song_id", ASCENDING)])
    playlist_follows.create_index([("user_id", ASCENDING), ("playlist_id", ASCENDING)], unique=True)
    followers.create_index([("follower_id", ASCENDING), ("following_id", ASCENDING)], unique=True)
