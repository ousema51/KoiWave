import 'package:flutter/foundation.dart';
import 'package:youtube_player_iframe/youtube_player_iframe.dart';
import '../models/song.dart';

class PlayerService {
  static final PlayerService _instance = PlayerService._internal();
  factory PlayerService() => _instance;

  YoutubePlayerController? _controller;
  Song? _currentSong;
  bool _isPlaying = false;
  bool _isReady = false;

  // Listeners for UI updates
  final ValueNotifier<bool> _playingNotifier = ValueNotifier(false);
  final ValueNotifier<bool> _readyNotifier = ValueNotifier(false);

  PlayerService._internal();

  /// Load a song and prepare for playback
  void loadSong(Song song) {
    _currentSong = song;
    
    // Clean up old controller
    if (_controller != null) {
      try {
        _controller!.close();
      } catch (_) {}
    }

    _isReady = false;
    _readyNotifier.value = false;
    _isPlaying = false;
    _playingNotifier.value = false;

    // Create new controller with the YouTube video ID
    _controller = YoutubePlayerController.fromVideoId(
      videoId: song.id,
      autoPlay: true,
      params: const YoutubePlayerParams(
        showControls: false,
        showFullscreenButton: false,
        mute: false,
        playsInline: true,
        strictRelatedVideos: true,
      ),
    );

    // Set up listeners for player state changes
    _controller?.listen((state) {
      if (state.isReady && !_isReady) {
        _isReady = true;
        _readyNotifier.value = true;
        debugPrint('[PlayerService] Player ready for: ${song.title}');
      }

      if (state.isPlaying && !_isPlaying) {
        _isPlaying = true;
        _playingNotifier.value = true;
        debugPrint('[PlayerService] Now playing: ${song.title}');
      } else if (!state.isPlaying && _isPlaying) {
        _isPlaying = false;
        _playingNotifier.value = false;
        debugPrint('[PlayerService] Paused: ${song.title}');
      }

      // Handle errors
      if (state.hasError) {
        debugPrint('[PlayerService] Error: ${state.error}');
      }
    });

    debugPrint('[PlayerService] Loading song: ${song.title} (ID: ${song.id})');
  }

  void play() {
    if (_controller == null) {
      debugPrint('[PlayerService] No controller available');
      return;
    }
    try {
      _controller!.playVideo();
      debugPrint('[PlayerService] Play requested');
    } catch (e) {
      debugPrint('[PlayerService] Play error: $e');
    }
  }

  void pause() {
    if (_controller == null) {
      debugPrint('[PlayerService] No controller available');
      return;
    }
    try {
      _controller!.pauseVideo();
      debugPrint('[PlayerService] Pause requested');
    } catch (e) {
      debugPrint('[PlayerService] Pause error: $e');
    }
  }

  void stop() {
    if (_controller != null) {
      try {
        _controller!.close();
      } catch (e) {
        debugPrint('[PlayerService] Stop error: $e');
      }
    }
    _isPlaying = false;
    _isReady = false;
    _playingNotifier.value = false;
    _readyNotifier.value = false;
    debugPrint('[PlayerService] Stopped');
  }

  // Getters
  YoutubePlayerController? get controller => _controller;
  Song? get currentSong => _currentSong;
  bool get isPlaying => _isPlaying;
  bool get isReady => _isReady;

  // UI streams for reactive updates
  ValueNotifier<bool> get playingNotifier => _playingNotifier;
  ValueNotifier<bool> get readyNotifier => _readyNotifier;

  @override
  String toString() => 'PlayerService(song: ${_currentSong?.title}, playing: $_isPlaying, ready: $_isReady)';
}
