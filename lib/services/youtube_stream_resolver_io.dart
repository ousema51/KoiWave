import 'package:youtube_explode_dart/youtube_explode_dart.dart' as yte;

String? _extractVideoId(String raw) {
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

Future<Map<String, dynamic>?> _resolveByVideoId(
  yte.YoutubeExplode yt,
  String videoId,
  Map<String, String> defaultHeaders,
) async {
  final manifest = await yt.videos.streams.getManifest(
    videoId,
    ytClients: [
      yte.YoutubeApiClient.android,
      yte.YoutubeApiClient.ios,
      yte.YoutubeApiClient.safari,
      yte.YoutubeApiClient.tv,
    ],
    requireWatchPage: true,
  );

  if (manifest.audioOnly.isEmpty) {
    return null;
  }

  final bestAudio = manifest.audioOnly.withHighestBitrate();
  final url = bestAudio.url.toString();
  if (url.isEmpty) {
    return null;
  }

  return {
    'audio_url': url,
    'headers': Map<String, String>.from(defaultHeaders),
    'source': 'youtube-explode',
    'video_id': videoId,
  };
}

Future<Map<String, dynamic>?> resolveStream({
  required String songId,
  String? titleHint,
  required Map<String, String> defaultHeaders,
}) async {
  final yt = yte.YoutubeExplode();
  try {
    final candidateIds = <String>[];
    final seen = <String>{};

    final directId = _extractVideoId(songId);
    if (directId != null && seen.add(directId)) {
      candidateIds.add(directId);
    }

    final query = (titleHint ?? '').trim();
    if (query.isNotEmpty) {
      try {
        final searchResults = await yt.search.search(query);
        for (final video in searchResults.take(8)) {
          final candidateId = video.id.value;
          if (candidateId.isNotEmpty && seen.add(candidateId)) {
            candidateIds.add(candidateId);
          }
        }
      } catch (_) {}
    }

    for (final videoId in candidateIds) {
      try {
        final resolved = await _resolveByVideoId(yt, videoId, defaultHeaders);
        if (resolved != null) {
          return resolved;
        }
      } catch (_) {}
    }

    return null;
  } finally {
    yt.close();
  }
}
