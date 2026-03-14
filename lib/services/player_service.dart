import 'package:just_audio/just_audio.dart';

class PlayerService {
  static final PlayerService _instance = PlayerService._internal();
  factory PlayerService() => _instance;

  final AudioPlayer player = AudioPlayer();

  PlayerService._internal();

  Future<void> play(String url) async {
    await player.setUrl(url);
    player.play();
  }

  void pause() {
    player.pause();
  }

  void resume() {
    player.play();
  }

  void stop() {
    player.stop();
  }
}