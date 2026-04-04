# Developer Notes - Architecture & Implementation Details

## Project Architecture

```
spotify_clone/
├── lib/                          # Flutter app
│   ├── main.dart                # App entry point
│   ├── config/
│   │   └── api_config.dart      # API configuration (CHANGED)
│   ├── models/
│   │   ├── song.dart            # Song model with UTF-8 handling
│   │   ├── album.dart
│   │   └── artist.dart
│   ├── services/
│   │   ├── api_service.dart     # HTTP client
│   │   ├── music_service.dart   # Music business logic
│   │   ├── player_service.dart  # REWRITTEN - Playback engine
│   │   └── auth_service.dart    # Authentication
│   ├── screens/
│   │   ├── home_screen.dart
│   │   ├── search_screen.dart
│   │   ├── library_screen.dart
│   │   └── main_screen.dart
│   └── widgets/
│       ├── full_player.dart     # REWRITTEN - Main player UI
│       ├── mini_player.dart
│       ├── song_tile.dart       # Song list item
│       └── album_card.dart
│
├── backend/                      # Python backend
│   ├── api/
│   │   └── index.py             # Flask app
│   ├── routes/
│   │   ├── auth.py
│   │   ├── music.py
│   │   └── others...
│   ├── models/
│   │   └── db.py                # MongoDB models
│   ├── utils/
│   │   └── youtube_music.py     # IMPROVED - YTMusic integration
│   ├── middleware/
│   │   └── auth_middleware.py   # JWT middleware
│   ├── requirements.txt
│   └── vercel.json
│
├── FIXES_SUMMARY.md             # NEW - Complete fixes documentation
├── TESTING_GUIDE.md             # NEW - Testing instructions
└── README.md
```

---

## Key Components

### 1. PlayerService (lib/services/player_service.dart)

**Purpose**: Single source of truth for playback state

**Key Features** (NEW):
- Persistent singleton instance
- Reactive state management with `ValueNotifier`
- Player lifecycle management
- Error handling and debugging

**Properties**:
```dart
YoutubePlayerController? _controller       // YouTube player
Song? _currentSong                         // Currently playing song
bool _isPlaying                            // Play/pause state
bool _isReady                              // Initialization state (NEW)
ValueNotifier<bool> _playingNotifier       // Reactive stream (NEW)
ValueNotifier<bool> _readyNotifier         // Reactive stream (NEW)
```

**Methods**:
```dart
void loadSong(Song song)                   // Load and initialize song
void play()                                // Start playback
void pause()                               // Pause playback
void stop()                                // Stop and cleanup
```

**State Listeners** (NEW):
```dart
_controller?.listen((state) {
  if (state.isReady) { /* player ready */ }
  if (state.isPlaying) { /* playing */ }
  if (state.hasError) { /* error */ }
})
```

### 2. FullPlayerScreen (lib/widgets/full_player.dart)

**Purpose**: Main user interface for playback

**Key Changes**:
- Listens to `PlayerService.playingNotifier` for state updates
- Implements `_setupPlayer()` for proper initialization
- 500ms delay before playing ensures youtube_player_iframe readiness
- Hides player completely (0x0 size) for audio-only mode

**State Management**:
```dart
@override
void initState() {
  // 1. Setup animation
  // 2. Setup player if song exists
  // 3. Listen to player state changes
  _player.playingNotifier.addListener(_onPlayerStateChanged);
}

void _setupPlayer(Song song) {
  _player.loadSong(song);
  
  // Wait for initialization
  Future.delayed(const Duration(milliseconds: 500), () {
    _player.play();
  });
}
```

### 3. youtube_music.py (backend/utils/youtube_music.py)

**Purpose**: YouTube Music API integration with encoding/thumbnail fixes

**Key Improvements**:

#### UTF-8 Safe String Handling
```python
def _safe_str(value):
    """Ensure all strings are valid UTF-8"""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value.encode('utf-8')
            return value
        except UnicodeEncodeError:
            # Replace invalid chars
            return value.encode('utf-8', errors='replace').decode('utf-8')
    return str(value)
```

#### Thumbnail Extraction with Fallbacks
```python
def _get_thumbnail(r):
    # Try primary source (thumbnails array)
    # Try secondary source (thumbnail object)
    # Fallback to YouTube CDN: https://img.youtube.com/vi/{id}/hqdefault.jpg
    # Return None if all fail
```

#### Data Normalization
```python
def _normalize(r):
    return {
        "id": _safe_str(r.get("videoId")),
        "title": _safe_str(r.get("title")) or "Unknown",
        "artist": artist or "Unknown Artist",
        "duration": r.get("duration"),
        "thumbnail": _get_thumbnail(r),
        "image": _get_thumbnail(r),
        "cover_url": _get_thumbnail(r),
    }
```

---

## Data Flow

### Song Search Flow
```
SearchScreen
    ↓ (query)
MusicService.searchSongs()
    ↓ (HTTP GET)
ApiService.get("/music/search?q=...")
    ↓ (HTTP request)
Backend: music.py /search endpoint
    ↓
youtube_music.search_songs()
    ↓ (returns _normalize'd data)
Backend: _safe_str() ensures UTF-8
    ↓ (JSON response)
Flutter: JsonDecode
    ↓
Song.fromJson() 
    ↓
SearchScreen: Display in ListView
```

### Playback Flow
```
SearchScreen: User taps song
    ↓
SearchScreen.onSongSelected(song)
    ↓
MainScreen._onSongSelected(song)
    ↓
MainScreen._loadAndPlay(song)
    ├─ MusicService.getSong() - refresh metadata
    ├─ MusicService.getStreamUrlWithHint() - get stream URL
    └─ PlayerService.loadSong(song)
        ├─ Create YoutubePlayerController
        ├─ Setup state listener
        └─ Wait 500ms
            └─ PlayerService.play()
                └─ _controller.playVideo()
                    ↓
                    FullPlayerScreen shows playing state
                    ↓
                    Audio plays
```

---

## API Response Format

### Search Response
```json
{
  "success": true,
  "data": [
    {
      "id": "dQw4w9WgXcQ",           // 11-char video ID
      "title": "Example Song",        // UTF-8 encoded title
      "name": "Example Song",         // Alternative title field
      "artist": "Artist Name",        // UTF-8 encoded artist
      "duration": 212,                // Seconds
      "thumbnail": "https://...",     // HTTPS absolute URL or fallback
      "image": "https://...",         // Duplicate field for compatibility
      "cover_url": "https://..."      // Duplicate field for compatibility
    }
  ]
}
```

### Error Response
```json
{
  "success": false,
  "message": "Search failed: <reason>"
}
```

---

## Configuration

### LocalHost Development
```dart
// lib/config/api_config.dart
static const String baseUrl = 'http://localhost:5000/api';
```

### Backend Environment
```bash
export MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/db
python api/index.py
```

### Vercel Deployment
```json
{
  "builds": [{
    "src": "api/index.py",
    "use": "@vercel/python"
  }],
  "routes": [{
    "src": "/api/(.*)",
    "dest": "api/index.py"
  }]
}
```

---

## Video ID Format

YouTube video IDs are **exactly 11 alphanumeric characters**:
- Valid: `dQw4w9WgXcQ`, `9bZkp7q19f0`
- Invalid: Full URL, missing characters, special chars

---

## Error Handling Strategy

### Frontend (lib layer)
```dart
try {
  final songs = await MusicService().searchSongs(query);
  setState(() => _songResults = songs);
} catch (e) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Error: $e'))
  );
}
```

### Backend (Python layer)
```python
try:
  result = youtube_music.search_songs(query)
  return jsonify({"success": True, "data": result})
except Exception as e:
  logger.error(f"Search error: {e}")
  return jsonify({"success": False, "message": str(e)})
```

---

## Performance Considerations

### 1. Player Initialization Delay
```dart
// 500ms delay ensures youtube_player_iframe is ready
Future.delayed(const Duration(milliseconds: 500), () {
  _player.play();
});
```

### 2. String Encoding Check
```python
# Validates UTF-8 in Python before sending (faster than fixing in Flutter)
try:
    value.encode('utf-8')
    return value
except UnicodeEncodeError:
    # Fix now, not later
    return value.encode('utf-8', errors='replace').decode('utf-8')
```

### 3. Reactive State Management
```dart
// Use ValueNotifier instead of StreamController
// More efficient for simple state changes
ValueNotifier<bool> _playingNotifier = ValueNotifier(false);
_playingNotifier.addListener(_callback);  // Direct callback
```

---

## Future Improvements

### Short Term
- [ ] Implement skip next/previous
- [ ] Add progress bar seeking
- [ ] Queue management
- [ ] Shuffle and repeat modes

### Medium Term
- [ ] Full audio_service integration
- [ ] Background playback
- [ ] Wakelock (prevent screen sleep)
- [ ] Media controls notification (Android/iOS)

### Long Term
- [ ] Caching layer for frequently played songs
- [ ] Offline playback
- [ ] Multi-device sync
- [ ] Advanced analytics

---

## Testing Strategy

### Unit Tests (Recommended)
```dart
group('PlayerService', () {
  test('loadSong initializes controller', () {
    final service = PlayerService();
    final song = Song(...);
    service.loadSong(song);
    
    expect(service.controller, isNotNull);
    expect(service.currentSong, equals(song));
  });
});
```

### Integration Tests
```dart
testWidgets('Song plays when selected', (WidgetTester tester) async {
  await tester.pumpWidget(MyApp());
  await tester.tap(searchField);
  // ... assertions
});
```

### Backend Tests
```python
def test_search_songs():
    result = search_songs("test")
    assert result["success"] == True
    assert len(result["data"]) > 0
    for song in result["data"]:
        assert "id" in song
        assert "title" in song
```

---

## Debugging Checklist

When troubleshooting:

1. **Check backend is running**
   ```bash
   curl http://localhost:5000/api/health
   ```

2. **Verify Flutter console logs**
   ```
   [PlayerService] Loading song: ...
   [PlayerService] Player ready for: ...
   ```

3. **Test API endpoints directly**
   ```bash
   curl "http://localhost:5000/api/music/search?q=test&type=songs"
   ```

4. **Inspect network requests**
   - Check Firefox/Chrome DevTools
   - Look for failed requests or 500 errors

5. **Verify data format**
   - Ensure JSON response is valid
   - Check video IDs are 11 characters
   - Confirm URLs start with `https://`

---

## Important Notes

1. **YouTube Player Limitations**
   - Requires valid YouTube video IDs
   - Cannot play restricted videos
   - Regional restrictions apply

2. **Encoding Important**
   - All strings go through `_safe_str()` on backend
   - Prevents corruption in MongoDB and responses
   - Critical for international user support

3. **Thumbnail Reliability**
   - YouTube CDN might change URL format
   - Fallback system ensures something always displays
   - Music note icon is final fallback

4. **Performance**
   - 500ms delay is conservative but reliable
   - Can be reduced to 300ms after testing
   - Adjust based on device performance

