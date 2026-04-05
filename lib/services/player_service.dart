import 'dart:async';

import 'package:audio_service/audio_service.dart' show MediaItem;
import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:youtube_player_iframe/youtube_player_iframe.dart' as yt;
import '../models/song.dart';
import 'audio_cache_service.dart';

enum QueueRepeatMode { off, all, one }

class PlayerService {
  static final PlayerService _instance = PlayerService._internal();
  factory PlayerService() => _instance;

  yt.YoutubePlayerController? _controller;
  final AudioPlayer _audioPlayer = AudioPlayer();
  final AudioCacheService _cache = AudioCacheService();

  static const Map<String, String> _defaultStreamHeaders = {
    'User-Agent':
        'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
    'Referer': 'https://music.youtube.com/',
    'Origin': 'https://music.youtube.com',
  };

  StreamSubscription<yt.YoutubePlayerValue>? _controllerStateSubscription;
  StreamSubscription<yt.YoutubeVideoState>? _videoStateSubscription;
  StreamSubscription<PlayerState>? _audioStateSubscription;
  StreamSubscription<Duration>? _audioPositionSubscription;
  StreamSubscription<Duration?>? _audioDurationSubscription;

  Song? _currentSong;
  bool _isPlaying = false;
  bool _isReady = false;
  bool _usingAudioEngine = false;
  yt.YoutubeError? _lastYoutubeError;

  // Listeners for UI updates
  final ValueNotifier<bool> _playingNotifier = ValueNotifier(false);
  final ValueNotifier<bool> _readyNotifier = ValueNotifier(false);
  final ValueNotifier<yt.PlayerState> _playerStateNotifier = ValueNotifier(
    yt.PlayerState.unknown,
  );
  final ValueNotifier<Duration> _positionNotifier = ValueNotifier(
    Duration.zero,
  );
  final ValueNotifier<Duration> _durationNotifier = ValueNotifier(
    Duration.zero,
  );

  PlayerService._internal();

  MediaItem _buildMediaItem(Song song, String sourceId) {
    return MediaItem(
      id: sourceId,
      title: song.title,
      artist: song.artist ?? 'Unknown Artist',
      album: song.albumName ?? 'KoiWave',
      artUri: (song.coverUrl != null && song.coverUrl!.isNotEmpty)
          ? Uri.tryParse(song.coverUrl!)
          : null,
      duration: (song.duration != null && song.duration! > 0)
          ? Duration(seconds: song.duration!)
          : null,
      extras: {'song_id': song.id},
    );
  }

  void _ensureController() {
    if (_controller != null) return;

    _controller = yt.YoutubePlayerController(
      params: const yt.YoutubePlayerParams(
        showControls: false,
        showFullscreenButton: false,
        mute: false,
        playsInline: true,
        strictRelatedVideos: true,
      ),
    );

    _controllerStateSubscription?.cancel();
    _videoStateSubscription?.cancel();

    _controllerStateSubscription = _controller!.listen((state) {
      _playerStateNotifier.value = state.playerState;

      final bool isPlayerReady =
          state.playerState != yt.PlayerState.unknown &&
          state.playerState != yt.PlayerState.unStarted;
      if (isPlayerReady != _isReady) {
        _isReady = isPlayerReady;
        _readyNotifier.value = _isReady;
      }

      final bool isCurrentlyPlaying =
          state.playerState == yt.PlayerState.playing;
      if (isCurrentlyPlaying != _isPlaying) {
        _isPlaying = isCurrentlyPlaying;
        _playingNotifier.value = _isPlaying;
      }

      final Duration metaDuration = state.metaData.duration;
      if (metaDuration > Duration.zero &&
          metaDuration != _durationNotifier.value) {
        _durationNotifier.value = metaDuration;
      }

      if (state.hasError) {
        _lastYoutubeError = state.error;
        debugPrint('[PlayerService] Error: ${state.error}');
      } else if (state.playerState == yt.PlayerState.playing) {
        _lastYoutubeError = null;
      }
    });

    _videoStateSubscription = _controller!.videoStateStream.listen((
      videoState,
    ) {
      _positionNotifier.value = videoState.position;
    });
  }

  void _ensureAudioListeners() {
    _audioStateSubscription ??= _audioPlayer.playerStateStream.listen((state) {
      final bool playing = state.playing;
      if (playing != _isPlaying) {
        _isPlaying = playing;
        _playingNotifier.value = _isPlaying;
      }

      if (state.processingState == ProcessingState.completed) {
        _playerStateNotifier.value = yt.PlayerState.ended;
        _isPlaying = false;
        _playingNotifier.value = false;
      }
    });

    _audioPositionSubscription ??= _audioPlayer.positionStream.listen((pos) {
      _positionNotifier.value = pos;
    });

    _audioDurationSubscription ??= _audioPlayer.durationStream.listen((dur) {
      if (dur != null && dur > Duration.zero) {
        _durationNotifier.value = dur;
      }
    });
  }

  Map<String, String> _buildStreamHeaders(Map<String, String>? streamHeaders) {
    final merged = <String, String>{..._defaultStreamHeaders};
    if (streamHeaders == null) return merged;

    streamHeaders.forEach((key, value) {
      final k = key.trim();
      final v = value.trim();
      if (k.isNotEmpty && v.isNotEmpty) {
        merged[k] = v;
      }
    });

    return merged;
  }

  Future<void> _stopCurrentEngine() async {
    if (_usingAudioEngine) {
      try {
        await _audioPlayer.stop();
      } catch (_) {}
    } else {
      if (_controller != null) {
        try {
          await _controller!.stopVideo();
        } catch (_) {}
      }
    }
  }

  String? _extractYoutubeVideoId(String raw) {
    final input = raw.trim();
    if (input.isEmpty) return null;

    final idRegex = RegExp(r'^[A-Za-z0-9_-]{11}$');
    if (idRegex.hasMatch(input)) {
      return input;
    }

    final uri = Uri.tryParse(input);
    if (uri != null) {
      final fromQuery = uri.queryParameters['v'];
      if (fromQuery != null && idRegex.hasMatch(fromQuery)) {
        return fromQuery;
      }

      if (uri.pathSegments.isNotEmpty) {
        final last = uri.pathSegments.last;
        if (idRegex.hasMatch(last)) {
          return last;
        }
      }
    }

    final loose = RegExp(r'([A-Za-z0-9_-]{11})').firstMatch(input);
    return loose?.group(1);
  }

  bool _isFatalYoutubeError(yt.YoutubeError? error) {
    if (error == null || error == yt.YoutubeError.none) {
      return false;
    }

    switch (error) {
      case yt.YoutubeError.invalidParam:
      case yt.YoutubeError.videoNotFound:
      case yt.YoutubeError.notEmbeddable:
      case yt.YoutubeError.cannotFindVideo:
      case yt.YoutubeError.sameAsNotEmbeddable:
        return true;
      case yt.YoutubeError.html5Error:
      case yt.YoutubeError.unknown:
      case yt.YoutubeError.none:
        return false;
    }
  }

  Future<bool> _waitForYoutubePlaybackStart({
    Duration timeout = const Duration(seconds: 6),
  }) async {
    final stopwatch = Stopwatch()..start();

    while (stopwatch.elapsed < timeout) {
      final state = _playerStateNotifier.value;
      if (state == yt.PlayerState.playing) {
        return true;
      }

      // Buffering with known position indicates the stream has started.
      if (state == yt.PlayerState.buffering &&
          _positionNotifier.value > Duration.zero) {
        return true;
      }

      if (_isFatalYoutubeError(_lastYoutubeError)) {
        return false;
      }

      await Future<void>.delayed(const Duration(milliseconds: 150));
    }

    return _playerStateNotifier.value == yt.PlayerState.playing;
  }

  Future<void> _playYoutubeWithRetries(
    yt.YoutubePlayerController controller, {
    required String videoId,
  }) async {
    final bool isAndroid =
        !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
    final int maxAttempts = isAndroid ? 5 : 3;

    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      _lastYoutubeError = null;

      if (attempt == 1) {
        await controller.cueVideoById(videoId: videoId);
      } else if (attempt == 3) {
        await controller.loadVideoByUrl(
          mediaContentUrl: 'https://www.youtube.com/watch?v=$videoId',
        );
      } else {
        await controller.loadVideoById(videoId: videoId);
      }

      if (isAndroid) {
        await Future<void>.delayed(const Duration(milliseconds: 350));
      }

      final bool mutedAttempt = isAndroid && attempt >= 4;
      if (mutedAttempt) {
        await controller.mute();
      }

      await controller.playVideo();

      final started = await _waitForYoutubePlaybackStart(
        timeout: Duration(
          milliseconds: isAndroid ? 3000 + (attempt * 1200) : 1600,
        ),
      );
      if (started) {
        if (mutedAttempt) {
          unawaited(controller.unMute());
        }
        return;
      }

      if (_isFatalYoutubeError(_lastYoutubeError)) {
        break;
      }

      await Future<void>.delayed(const Duration(milliseconds: 450));
    }

    final state = _playerStateNotifier.value;
    final errorText = _lastYoutubeError?.toString() ?? 'none';
    throw StateError(
      'YouTube playback did not start for $videoId (state: $state, error: $errorText)',
    );
  }

  Future<void> _loadSongWithYoutubeIFrame(Song song) async {
    _usingAudioEngine = false;
    _ensureController();

    final resolvedVideoId = _extractYoutubeVideoId(song.id);
    if (resolvedVideoId == null) {
      throw FormatException('Invalid YouTube video id: ${song.id}');
    }

    _lastYoutubeError = null;
    final controller = _controller!;
    await _playYoutubeWithRetries(controller, videoId: resolvedVideoId);

    if (!_isReady) {
      _isReady = true;
      _readyNotifier.value = true;
    }

    debugPrint(
      '[PlayerService] Loading YouTube iframe playback: ${song.title} (ID: $resolvedVideoId)',
    );
  }

  /// Load a song and start playback using the same shared controller.
  Future<void> loadSong(
    Song song, {
    String? streamUrl,
    Map<String, String>? streamHeaders,
  }) async {
    _currentSong = song;

    _isReady = false;
    _readyNotifier.value = false;
    _isPlaying = false;
    _playingNotifier.value = false;
    _playerStateNotifier.value = yt.PlayerState.unknown;
    _positionNotifier.value = Duration.zero;
    _durationNotifier.value = (song.duration != null && song.duration! > 0)
        ? Duration(seconds: song.duration!)
        : Duration.zero;

    await _stopCurrentEngine();

    if (kIsWeb) {
      try {
        await _loadSongWithYoutubeIFrame(song);
        return;
      } catch (e) {
        debugPrint('[PlayerService] Web YouTube load failed: $e');
      }
    }

    String? cachedPath;
    if (!kIsWeb) {
      try {
        cachedPath = await _cache.getCachedFilePath(song.id);
      } catch (e) {
        debugPrint('[PlayerService] Cache lookup skipped: $e');
      }
    }

    if (cachedPath != null) {
      try {
        _usingAudioEngine = true;
        _ensureAudioListeners();
        if (kIsWeb) {
          await _audioPlayer.setFilePath(cachedPath);
        } else {
          final sourceId = Uri.file(cachedPath).toString();
          await _audioPlayer.setAudioSource(
            AudioSource.file(cachedPath, tag: _buildMediaItem(song, sourceId)),
          );
        }
        _isReady = true;
        _readyNotifier.value = true;
        _playerStateNotifier.value = yt.PlayerState.cued;
        await _audioPlayer.play();
        debugPrint('[PlayerService] Playing cached audio for: ${song.title}');
        return;
      } catch (e) {
        debugPrint('[PlayerService] Cached playback failed, fallback: $e');
      }
    }

    if (streamUrl != null && streamUrl.isNotEmpty) {
      try {
        _usingAudioEngine = true;
        _ensureAudioListeners();
        final mergedHeaders = _buildStreamHeaders(streamHeaders);
        if (kIsWeb) {
          await _audioPlayer.setUrl(streamUrl, headers: mergedHeaders);
        } else {
          final uri = Uri.parse(streamUrl);
          await _audioPlayer.setAudioSource(
            AudioSource.uri(
              uri,
              headers: mergedHeaders,
              tag: _buildMediaItem(song, uri.toString()),
            ),
          );
        }
        _isReady = true;
        _readyNotifier.value = true;
        _playerStateNotifier.value = yt.PlayerState.cued;
        await _audioPlayer.play();
        if (!kIsWeb) {
          unawaited(
            _cache.cacheInBackground(
              song.id,
              streamUrl,
              headers: mergedHeaders,
            ),
          );
        }
        debugPrint('[PlayerService] Streaming audio for: ${song.title}');
        return;
      } catch (e) {
        debugPrint('[PlayerService] Stream playback failed, fallback: $e');
      }
    }

    try {
      await _loadSongWithYoutubeIFrame(song);
    } catch (e) {
      debugPrint('[PlayerService] Load song error: $e');
      rethrow;
    }
  }

  Future<void> play() async {
    try {
      if (_usingAudioEngine) {
        await _audioPlayer.play();
      } else {
        if (_controller == null) {
          debugPrint('[PlayerService] No controller available');
          return;
        }
        await _controller!.playVideo();
      }
      debugPrint('[PlayerService] Play requested');
    } catch (e) {
      debugPrint('[PlayerService] Play error: $e');
    }
  }

  Future<void> pause() async {
    try {
      if (_usingAudioEngine) {
        await _audioPlayer.pause();
      } else {
        if (_controller == null) {
          debugPrint('[PlayerService] No controller available');
          return;
        }
        await _controller!.pauseVideo();
      }
      debugPrint('[PlayerService] Pause requested');
    } catch (e) {
      debugPrint('[PlayerService] Pause error: $e');
    }
  }

  Future<void> stop() async {
    try {
      if (_usingAudioEngine) {
        await _audioPlayer.stop();
      } else if (_controller != null) {
        await _controller!.stopVideo();
      }
    } catch (e) {
      debugPrint('[PlayerService] Stop error: $e');
    }
    _isPlaying = false;
    _isReady = false;
    _playingNotifier.value = false;
    _readyNotifier.value = false;
    _playerStateNotifier.value = yt.PlayerState.unknown;
    _positionNotifier.value = Duration.zero;
    debugPrint('[PlayerService] Stopped');
  }

  Future<void> seekToFraction(double fraction) async {
    try {
      Duration duration = _durationNotifier.value;
      if (duration <= Duration.zero) {
        if (_usingAudioEngine) {
          final dur = _audioPlayer.duration;
          if (dur != null) {
            duration = dur;
          }
        } else {
          if (_controller == null) return;
          final seconds = await _controller!.duration;
          duration = Duration(milliseconds: (seconds * 1000).round());
        }

        if (duration > Duration.zero) {
          _durationNotifier.value = duration;
        }
      }

      if (duration <= Duration.zero) return;

      final double clampedFraction = fraction.clamp(0.0, 1.0);
      final Duration target = Duration(
        milliseconds: (duration.inMilliseconds * clampedFraction).round(),
      );

      if (_usingAudioEngine) {
        await _audioPlayer.seek(target);
      } else {
        if (_controller == null) return;
        final double targetSeconds = target.inMilliseconds / 1000.0;
        await _controller!.seekTo(seconds: targetSeconds, allowSeekAhead: true);
      }

      _positionNotifier.value = target;
    } catch (e) {
      debugPrint('[PlayerService] Seek error: $e');
    }
  }

  double get progress {
    final total = _durationNotifier.value.inMilliseconds;
    if (total <= 0) return 0.0;
    return (_positionNotifier.value.inMilliseconds / total).clamp(0.0, 1.0);
  }

  Future<void> disposePlayer() async {
    await _controllerStateSubscription?.cancel();
    await _videoStateSubscription?.cancel();
    await _audioStateSubscription?.cancel();
    await _audioPositionSubscription?.cancel();
    await _audioDurationSubscription?.cancel();
    _controllerStateSubscription = null;
    _videoStateSubscription = null;
    _audioStateSubscription = null;
    _audioPositionSubscription = null;
    _audioDurationSubscription = null;

    if (_controller != null) {
      await _controller!.close();
      _controller = null;
    }
    await _audioPlayer.dispose();
  }

  // Getters
  yt.YoutubePlayerController? get controller {
    _ensureController();
    return _controller;
  }

  Song? get currentSong => _currentSong;
  bool get isPlaying => _isPlaying;
  bool get isReady => _isReady;
  Duration get position => _positionNotifier.value;
  Duration get duration => _durationNotifier.value;

  // UI streams for reactive updates
  ValueNotifier<bool> get playingNotifier => _playingNotifier;
  ValueNotifier<bool> get readyNotifier => _readyNotifier;
  ValueNotifier<yt.PlayerState> get playerStateNotifier => _playerStateNotifier;
  ValueNotifier<Duration> get positionNotifier => _positionNotifier;
  ValueNotifier<Duration> get durationNotifier => _durationNotifier;

  @override
  String toString() =>
      'PlayerService(song: ${_currentSong?.title}, playing: $_isPlaying, ready: $_isReady)';
}
