# Testing Guide - Spotify Clone Fixes

## Quick Start

### 1. Start the Backend Server

```bash
cd backend
pip install -r requirements.txt
export MONGODB_URI=<your_mongodb_connection_string>  # Linux/Mac
set MONGODB_URI=<your_mongodb_connection_string>     # Windows PowerShell
python api/index.py
```

Backend should be running on: `http://localhost:5000`

Verify with:
```bash
curl http://localhost:5000/api/health
```

### 2. Run Flutter App

```bash
flutter pub get
flutter run
```

---

## Test Cases

### Test 1: Backend Connectivity ✅
**Expected**: App connects to backend, no errors in console

```steps:
1. Open app
2. Check Flutter console output
3. Should see no connection errors
```

**Result**: If successful, no red errors in console

---

### Test 2: Song Search ✅
**Expected**: Search returns songs with correct titles

```steps:
1. Navigate to Search screen
2. Type a song name (e.g., "Bohemian Rhapsody")
3. Press Search or wait for debounce
4. Verify song titles appear correctly (no garbled text)
5. Check that thumbnails load
```

**Success Criteria**:
- [ ] Songs are returned within 2 seconds
- [ ] Titles are readable (no random characters)
- [ ] Thumbnails show album art or music note fallback
- [ ] Artist names display correctly

**If Fails**:
- Check backend is running: `curl http://localhost:5000/api/health`
- Check network connectivity
- Look for UTF-8 encoding in console logs

---

### Test 3: Song Selection & Playback ✅ (CRITICAL)
**Expected**: Selecting a song starts playback immediately

```steps:
1. Search for any song
2. Tap on a song result
3. Full player screen appears
4. Watch play button
5. Music should start within 1 second
```

**Success Criteria**:
- [ ] Full player transitions smoothly
- [ ] Audio starts playing immediately
- [ ] Play button shows as "pause" (filled circle)
- [ ] Album art displays correctly
- [ ] Song title and artist show clearly

**Debug Output** (check Flutter console):
```
[MainScreen] playing song: <title> (<video_id>)
[PlayerService] Loading song: <title> (ID: <id>)
[PlayerService] Player ready for: <title>
[PlayerService] Now playing: <title>
```

**If Doesn't Play**:
1. Check YouTube video ID is valid
2. Verify youtube_player_iframe shows no errors
3. Check player controller is initialized:
   ```
   debugPrint('[PlayerService] Loading song: ...')
   debugPrint('[PlayerService] Player ready for: ...')
   ```
4. Look for errors in youtube_player_iframe logs

---

### Test 4: Play/Pause Controls ✅
**Expected**: Play and pause buttons work correctly

```steps:
1. Song is playing
2. Tap pause button → Should pause immediately
3. Verify pause icon appears (||)
4. Tap play button → Should resume
5. Verify play icon appears (▶)
6. Tap pause again → Should stop
```

**Success Criteria**:
- [ ] Play/Pause icon changes immediately
- [ ] No lag when tapping button
- [ ] State matches visual state

---

### Test 5: Thumbnail Reliability 🖼️ ✅
**Expected**: Thumbnails always display (either real image or fallback)

```steps:
1. Search for variety of songs
2. Observe thumbnails in song tiles
3. Open full player for each
4. Check album art displays
```

**Expected Display Types**:
- [ ] Real album art (if available from YouTube)
- [ ] YouTube CDN fallback image
- [ ] Music note icon (true fallback)
- [ ] Never shows broken/missing image

**If Thumbnails Not Loading**:
1. Check YouTube CDN is accessible:
   ```bash
   curl https://img.youtube.com/vi/<video_id>/hqdefault.jpg
   ```
2. Check backend returns thumbnail URLs:
   ```bash
   curl "http://localhost:5000/api/music/search?q=test&type=songs"
   ```
3. Verify URLs start with `https://`

---

### Test 6: International Characters 🌍 ✅
**Expected**: Non-ASCII characters display correctly

```steps:
1. Search for songs with special characters:
   - "Café"
   - "Björk"
   - "José"
   - "日本語" (or other non-Latin scripts)
2. Verify characters display correctly
3. No garbled text
```

**Success**: All character encoding works properly

---

### Test 7: Error Handling ✅
**Expected**: App handles errors gracefully

```steps:
1. Search for non-existent song
2. Observe "No results found" message (not crash)
3. Try invalid server URL temporarily
4. App should show error snackbar (not crash)
5. User can recover by going back
```

**Success Criteria**:
- [ ] No crashes on error
- [ ] Helpful error messages shown
- [ ] User can continue using app

---

### Test 8: API Endpoint Verification ✅
**Expected**: All endpoints return correct data

**Test each endpoint manually:**

```bash
# Health check
curl http://localhost:5000/api/health

# Search songs
curl "http://localhost:5000/api/music/search?q=test&type=songs"

# Get song details
curl "http://localhost:5000/api/music/song/<video_id>"

# Get trending
curl http://localhost:5000/api/music/trending
```

**Expected Responses**:
```json
{
  "success": true,
  "data": [
    {
      "id": "<video_id>",
      "title": "<song_title>",
      "artist": "<artist_name>",
      "thumbnail": "<image_url>",
      "duration": <seconds>
    }
  ]
}
```

---

## Performance Metrics

### Test Playback Latency
Expected time from selection to audio playback: **< 1 second**

```javascript
// Measure in Flutter console:
Selection Time: T0
Player Ready: T0 + ~500ms
Audio Playing: T0 + ~600ms
```

### Test Search Response Time
Expected: **< 2 seconds per search**

```javascript
Query Submitted: T0
Results Received: T0 + ~1000ms
UI Updated: T0 + ~1100ms
```

---

## Debugging Tips

### 1. View Console Logs
```bash
flutter logs
```

Look for:
- PlayerService debug messages
- API request/response logs
- Error stack traces

### 2. Check API Responses
```bash
# Enable network logging
# Check Flutter console for http requests/responses
```

### 3. Verify Video ID Format
Video IDs should be 11 characters, alphanumeric:
- Valid: `dQw4w9WgXcQ`
- Invalid: `https://youtube.com/watch?v=dQw4w9WgXcQ`

### 4. Enable Player Logging
In `player_service.dart`, logs are prefixed with `[PlayerService]`:
```
[PlayerService] Loading song: <title> (ID: <id>)
[PlayerService] Player ready for: <title>
[PlayerService] Error: <error_message>
```

### 5. Test with Simple Data
Start with simple test cases:
- "Test" (generic search)
- "Music" (common term)
- "Song" (basic search)

---

## Common Issues & Solutions

### Issue: "Selected songs do not start playing"
**Solution**:
1. Verify backend is running: `curl http://localhost:5000/api/health`
2. Check PlayerService console logs for initialization messages
3. Ensure youtube_player_iframe is properly initialized
4. Try restarting the app

### Issue: "Garbled song titles"
**Solution**:
1. Backend now uses `_safe_str()` for all titles
2. Restart backend: `python api/index.py`
3. Clear app data and re-open
4. Verify UTF-8 encoding in MongoDB

### Issue: "Thumbnails not appearing"
**Solution**:
1. Check YouTube CDN is accessible
2. Verify backend returns thumbnail URLs
3. Check image URLs return 200 status:
   ```bash
   curl -I "https://img.youtube.com/vi/<id>/hqdefault.jpg"
   ```
4. Music note icon should display as fallback

### Issue: "App crashes on search"
**Solution**:
1. Check backend is responding
2. Look for null pointer exceptions in console
3. Verify API response format is valid JSON
4. Check for network errors

### Issue: "Play button doesn't respond"
**Solution**:
1. Verify player controller is initialized
2. Check for  "Player ready" message in logs
3. Add 500ms delay (already in code)
4. Try selecting a different song

---

## Final Verification Checklist

- [ ] Backend running on localhost:5000
- [ ] App connects without errors
- [ ] Can search songs (UTF-8 titles display correctly)
- [ ] Select song → immediate playback
- [ ] Play/Pause buttons work
- [ ] Thumbnails display for all songs
- [ ] No crashes during normal use
- [ ] Album art or music note icon always shows
- [ ] International characters display correctly
- [ ] Errors don't crash the app

---

## Next Steps After Testing

1. Deploy backend to production server
2. Update API URL in `lib/config/api_config.dart`
3. Implement full audio_service integration for background playback
4. Add platform-specific configurations (Android/iOS)
5. Implement skip next/previous functionality
6. Add progress bar and seeking

