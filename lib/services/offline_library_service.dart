import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/song.dart';

class OfflineLibraryService {
  static const String _likedSongsKey = 'offline_liked_songs_v1';
  static const String _playlistsKey = 'offline_playlists_v1';

  Future<int> cacheLikedSongs(List<Song> songs) async {
    final prefs = await SharedPreferences.getInstance();
    final payload = songs.map(_songToMap).toList(growable: false);
    await prefs.setString(_likedSongsKey, jsonEncode(payload));
    return payload.length;
  }

  Future<List<Song>> getCachedLikedSongs() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_likedSongsKey);
    if (raw == null || raw.isEmpty) return [];

    try {
      final decoded = jsonDecode(raw) as List<dynamic>;
      return decoded
          .whereType<Map>()
          .map((e) => Song.fromJson(Map<String, dynamic>.from(e)))
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<int> cachePlaylist(
    String playlistId,
    String playlistName,
    List<Song> songs,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final all = await _readPlaylistsMap();

    all[playlistId] = {
      'name': playlistName,
      'songs': songs.map(_songToMap).toList(growable: false),
      'updated_at': DateTime.now().toIso8601String(),
    };

    await prefs.setString(_playlistsKey, jsonEncode(all));
    return songs.length;
  }

  Future<Map<String, dynamic>?> getCachedPlaylist(String playlistId) async {
    final all = await _readPlaylistsMap();
    final item = all[playlistId];
    if (item is Map<String, dynamic>) return item;
    return null;
  }

  Future<Map<String, dynamic>> _readPlaylistsMap() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_playlistsKey);
    if (raw == null || raw.isEmpty) return <String, dynamic>{};

    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) return decoded;
      return <String, dynamic>{};
    } catch (_) {
      return <String, dynamic>{};
    }
  }

  Map<String, dynamic> _songToMap(Song song) {
    return {
      'id': song.id,
      'song_id': song.id,
      'title': song.title,
      'artist': song.artist,
      'cover_url': song.coverUrl,
      'duration': song.duration,
    };
  }
}
