import '../models/song.dart';
import '../models/album.dart';
import '../models/artist.dart';
import 'api_service.dart';

class MusicService {
  static final MusicService _instance = MusicService._internal();
  factory MusicService() => _instance;
  MusicService._internal();

  final ApiService _api = ApiService();

  // --- Search ---
  Future<List<Song>> searchSongs(String query) async {
    final result = await _api.get('/music/search?q=${Uri.encodeComponent(query)}&type=songs');
    if (result['success'] == true && result['data'] != null) {
      final List<dynamic> items = result['data'] is List ? result['data'] : [];
      return items.map((e) => Song.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<List<Album>> searchAlbums(String query) async {
    final result = await _api.get('/music/search?q=${Uri.encodeComponent(query)}&type=albums');
    // YouTube Music backend returns empty list for albums
    return [];
  }

  Future<List<Artist>> searchArtists(String query) async {
    final result = await _api.get('/music/search?q=${Uri.encodeComponent(query)}&type=artists');
    // YouTube Music backend returns empty list for artists
    return [];
  }

  // --- Individual fetch ---
  Future<Song?> getSong(String songId) async {
    final result = await _api.get('/music/song/$songId');
    if (result['success'] == true && result['data'] != null) {
      return Song.fromJson(result['data'] as Map<String, dynamic>);
    }
    return null;
  }

  Future<String?> getStreamUrl(String songId) async {
    final result = await _api.get('/music/stream/$songId');
    if (result['success'] == true && result['data'] != null) {
      final data = result['data'];
      return data['stream_url'] as String? ?? data['streamUrl'] as String?;
    }
    return null;
  }

  /// Try to get a stream URL for [songId]. If [titleHint] is provided,
  /// ask the backend to use the search-based resolver which is more reliable
  /// for music entries and avoids consent/cookie issues.
  Future<String?> getStreamUrlWithHint(String songId, String? titleHint) async {
    // First try direct video id resolution
    String? url = await getStreamUrl(songId);
    print('[MusicService] getStreamUrl direct result for $songId: $url');
    if (url != null && url.isNotEmpty) return url;

    // If we have a title hint, call backend with q param to use search-based resolver
    if (titleHint != null && titleHint.isNotEmpty) {
      final encoded = Uri.encodeComponent(titleHint);
      final result = await _api.get('/music/stream/$songId?q=$encoded');
      print('[MusicService] backend stream result: $result');
      if (result['success'] == true && result['data'] != null) {
        final data = result['data'];
        return data['stream_url'] as String? ?? data['streamUrl'] as String?;
      }
    }
    return null;
  }

  Future<Album?> getAlbum(String albumId) async {
    final result = await _api.get('/music/album/$albumId');
    if (result['success'] == true && result['data'] != null) {
      return Album.fromJson(result['data'] as Map<String, dynamic>);
    }
    return null;
  }

  Future<Artist?> getArtist(String artistId) async {
    final result = await _api.get('/music/artist/$artistId');
    if (result['success'] == true && result['data'] != null) {
      return Artist.fromJson(result['data'] as Map<String, dynamic>);
    }
    return null;
  }

  // --- Trending / Home ---
  Future<List<Song>> getTrending() async {
    final result = await _api.get('/music/trending');
    if (result['success'] == true && result['data'] != null) {
      final data = result['data'];
      final List<dynamic> items =
          data is List ? data : (data['songs'] ?? data['trending'] ?? []);
      return items.map((e) => Song.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }

  // --- Library ---
  Future<Map<String, dynamic>> likeSong(
      String songId, Map<String, dynamic> metadata) async {
    return _api.post('/library/like/$songId', metadata);
  }

  Future<Map<String, dynamic>> unlikeSong(String songId) async {
    return _api.delete('/library/like/$songId');
  }

  Future<bool> checkLiked(String songId) async {
    final result = await _api.get('/library/liked/check/$songId');
    return result['data']?['liked'] == true;
  }

  Future<List<Song>> getLikedSongs() async {
    final result = await _api.get('/library/liked');
    if (result['success'] == true && result['data'] != null) {
      final List<dynamic> items = result['data'] as List<dynamic>? ?? [];
      return items.map((e) => Song.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }

  // --- History / Suggestions ---
  Future<Map<String, dynamic>> trackListen(String songId,
      Map<String, dynamic> metadata, int listenedSeconds, int totalDuration) async {
    return _api.post('/listen/track', {
      'song_id': songId,
      'metadata': metadata,
      'listened_seconds': listenedSeconds,
      'total_duration': totalDuration,
    });
  }

  Future<List<Song>> getRecentHistory() async {
    final result = await _api.get('/history/recent');
    if (result['success'] == true && result['data'] != null) {
      final List<dynamic> items = result['data'] as List<dynamic>? ?? [];
      return items.map((e) {
        final song = e['song'] ?? e;
        return Song.fromJson(song as Map<String, dynamic>);
      }).toList();
    }
    return [];
  }

  Future<List<Song>> getSuggestions() async {
    final result = await _api.get('/suggestions');
    if (result['success'] == true && result['data'] != null) {
      final List<dynamic> items = result['data'] as List<dynamic>? ?? [];
      return items.map((e) => Song.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }
}
