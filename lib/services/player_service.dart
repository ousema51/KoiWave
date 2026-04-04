import 'package:youtube_player_iframe/youtube_player_iframe.dart';
import '../models/song.dart';

class PlayerService {
  static final PlayerService _instance = PlayerService._internal();
  factory PlayerService() => _instance;

  YoutubePlayerController? _controller;
  Song? _currentSong;
  bool _isPlaying = false;

  PlayerService._internal();

  void loadSong(Song song) {
    _currentSong = song;
    _controller?.close();
    _controller = YoutubePlayerController.fromVideoId(
      videoId: song.id,
      autoPlay: true,
      params: YoutubePlayerParams(
        showControls: false,
        showFullscreenButton: false,
        mute: false,
      ),
    );
    _isPlaying = true;
    // TODO: Integrate with audio_service for background playback
  }

  void play() {
    _controller?.playVideo();
    _isPlaying = true;
    // TODO: Integrate with audio_service
  }

  void pause() {
    _controller?.pauseVideo();
    _isPlaying = false;
    // TODO: Integrate with audio_service
  }

  void stop() {
    _controller?.close();
    _isPlaying = false;
    // TODO: Integrate with audio_service
  }

  YoutubePlayerController? get controller => _controller;
  Song? get currentSong => _currentSong;
  bool get isPlaying => _isPlaying;

  // Streams for UI updates (stubbed, can be expanded)
  Stream<bool> get playingStream async* {
    yield _isPlaying;
  }
}
