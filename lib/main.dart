import 'package:flutter/material.dart';

void main() {
  runApp(MyApp());
}

//====================== MyApp ======================//
class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Music App',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF121212),
        bottomNavigationBarTheme: const BottomNavigationBarThemeData(
          backgroundColor: Color(0xFF1A1A1A),
          selectedItemColor: Color(0xFF1DB954),
          unselectedItemColor: Colors.grey,
        ),
        colorScheme: ColorScheme.dark(
          primary: const Color(0xFF1DB954),
          secondary: const Color(0xFF1DB954),
          surface: const Color(0xFF1A1A1A),
        ),
      ),
      home: MainScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

//====================== MiniPlayer ======================//
class MiniPlayer extends StatefulWidget {
  final VoidCallback onTap;

  MiniPlayer({required this.onTap});

  @override
  State<MiniPlayer> createState() => _MiniPlayerState();
}

class _MiniPlayerState extends State<MiniPlayer>
    with SingleTickerProviderStateMixin {
  bool isPlaying = false;
  bool isLiked = false;
  late AnimationController _progressController;

  @override
  void initState() {
    super.initState();
    _progressController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    );
  }

  @override
  void dispose() {
    _progressController.dispose();
    super.dispose();
  }

  void _togglePlay() {
    setState(() {
      isPlaying = !isPlaying;
      if (isPlaying) {
        _progressController.forward();
      } else {
        _progressController.stop();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF2A2A2A), Color(0xFF1E1E1E)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.4),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 10, 6, 8),
              child: Row(
                children: [
                  // Album Art with subtle glow
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(8),
                      gradient: const LinearGradient(
                        colors: [Color(0xFF1DB954), Color(0xFF148A3D)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF1DB954).withOpacity(0.3),
                          blurRadius: 8,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: const Icon(Icons.music_note_rounded,
                        color: Colors.white, size: 24),
                  ),
                  const SizedBox(width: 12),

                  // Song info with marquee-style feel
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "Blinding Lights",
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            color: Colors.white,
                            fontSize: 14,
                            letterSpacing: 0.2,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          "The Weeknd",
                          style: TextStyle(
                              color: Colors.grey[400],
                              fontSize: 12,
                              letterSpacing: 0.1),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),

                  // Like button
                  IconButton(
                    icon: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 200),
                      transitionBuilder: (child, anim) =>
                          ScaleTransition(scale: anim, child: child),
                      child: Icon(
                        isLiked ? Icons.favorite : Icons.favorite_border,
                        key: ValueKey(isLiked),
                        color:
                            isLiked ? const Color(0xFF1DB954) : Colors.grey[400],
                        size: 22,
                      ),
                    ),
                    onPressed: () => setState(() => isLiked = !isLiked),
                    splashRadius: 20,
                    padding: EdgeInsets.zero,
                    constraints:
                        const BoxConstraints(minWidth: 36, minHeight: 36),
                  ),

                  // Play/Pause button
                  Container(
                    width: 36,
                    height: 36,
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      icon: AnimatedSwitcher(
                        duration: const Duration(milliseconds: 200),
                        transitionBuilder: (child, anim) =>
                            ScaleTransition(scale: anim, child: child),
                        child: Icon(
                          isPlaying
                              ? Icons.pause_rounded
                              : Icons.play_arrow_rounded,
                          key: ValueKey(isPlaying),
                          color: Colors.black,
                          size: 20,
                        ),
                      ),
                      onPressed: _togglePlay,
                      padding: EdgeInsets.zero,
                    ),
                  ),
                  const SizedBox(width: 4),
                ],
              ),
            ),

            // Progress bar
            AnimatedBuilder(
              animation: _progressController,
              builder: (context, child) {
                return Container(
                  height: 3,
                  margin: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(2),
                    color: Colors.grey[800],
                  ),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: FractionallySizedBox(
                      widthFactor: _progressController.value.clamp(0.0, 1.0),
                      child: Container(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(2),
                          color: const Color(0xFF1DB954),
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
            const SizedBox(height: 6),
          ],
        ),
      ),
    );
  }
}

//====================== Full Player ======================//
class FullPlayerScreen extends StatefulWidget {
  final VoidCallback onClose;

  const FullPlayerScreen({required this.onClose});

  @override
  State<FullPlayerScreen> createState() => _FullPlayerScreenState();
}

class _FullPlayerScreenState extends State<FullPlayerScreen>
    with TickerProviderStateMixin {
  bool isPlaying = false;
  bool isLiked = false;
  bool isShuffle = false;
  int repeatMode = 0; // 0 = off, 1 = all, 2 = one
  double _currentSliderValue = 0.35;
  late AnimationController _slideController;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _slideController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOutCubic,
    ));
    _slideController.forward();
  }

  @override
  void dispose() {
    _slideController.dispose();
    super.dispose();
  }

  void _close() async {
    await _slideController.reverse();
    widget.onClose();
  }

  String _formatTime(double fraction) {
    int totalSeconds = (fraction * 230).toInt(); // 3:50 song
    int minutes = totalSeconds ~/ 60;
    int seconds = totalSeconds % 60;
    return "$minutes:${seconds.toString().padLeft(2, '0')}";
  }

  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: _slideAnimation,
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF1A3A2A), Color(0xFF0D1B14), Color(0xFF121212)],
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              stops: [0.0, 0.4, 0.8],
            ),
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                children: [
                  // Top bar
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.keyboard_arrow_down_rounded,
                              size: 32, color: Colors.white),
                          onPressed: _close,
                        ),
                        Column(
                          children: [
                            Text("PLAYING FROM PLAYLIST",
                                style: TextStyle(
                                    fontSize: 11,
                                    letterSpacing: 1.2,
                                    color: Colors.grey[400],
                                    fontWeight: FontWeight.w500)),
                            const SizedBox(height: 2),
                            const Text("Today's Hits",
                                style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white)),
                          ],
                        ),
                        IconButton(
                          icon: Icon(Icons.more_vert_rounded,
                              color: Colors.grey[300]),
                          onPressed: () {},
                        ),
                      ],
                    ),
                  ),

                  const Spacer(flex: 2),

                  // Album art
                  Container(
                    width: MediaQuery.of(context).size.width * 0.78,
                    height: MediaQuery.of(context).size.width * 0.78,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      gradient: const LinearGradient(
                        colors: [Color(0xFF1DB954), Color(0xFF0A5C2B)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF1DB954).withOpacity(0.25),
                          blurRadius: 40,
                          offset: const Offset(0, 16),
                          spreadRadius: 4,
                        ),
                        BoxShadow(
                          color: Colors.black.withOpacity(0.5),
                          blurRadius: 30,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                    child: const Center(
                      child: Icon(Icons.music_note_rounded,
                          color: Colors.white70, size: 80),
                    ),
                  ),

                  const Spacer(flex: 2),

                  // Song info and like
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              "Blinding Lights",
                              style: TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                                letterSpacing: 0.3,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              "The Weeknd",
                              style: TextStyle(
                                fontSize: 16,
                                color: Colors.grey[400],
                                letterSpacing: 0.2,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: AnimatedSwitcher(
                          duration: const Duration(milliseconds: 200),
                          transitionBuilder: (child, anim) =>
                              ScaleTransition(scale: anim, child: child),
                          child: Icon(
                            isLiked ? Icons.favorite : Icons.favorite_border,
                            key: ValueKey(isLiked),
                            color: isLiked
                                ? const Color(0xFF1DB954)
                                : Colors.grey[400],
                            size: 28,
                          ),
                        ),
                        onPressed: () => setState(() => isLiked = !isLiked),
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),

                  // Slider / Progress bar
                  SliderTheme(
                    data: SliderTheme.of(context).copyWith(
                      activeTrackColor: Colors.white,
                      inactiveTrackColor: Colors.grey[700],
                      thumbColor: Colors.white,
                      thumbShape:
                          const RoundSliderThumbShape(enabledThumbRadius: 6),
                      overlayShape:
                          const RoundSliderOverlayShape(overlayRadius: 14),
                      trackHeight: 3,
                    ),
                    child: Slider(
                      value: _currentSliderValue,
                      onChanged: (val) =>
                          setState(() => _currentSliderValue = val),
                    ),
                  ),

                  // Time labels
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(_formatTime(_currentSliderValue),
                            style: TextStyle(
                                color: Colors.grey[400], fontSize: 12)),
                        Text("3:50",
                            style: TextStyle(
                                color: Colors.grey[400], fontSize: 12)),
                      ],
                    ),
                  ),

                  const SizedBox(height: 12),

                  // Main controls
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      // Shuffle
                      IconButton(
                        icon: Icon(Icons.shuffle_rounded,
                            color: isShuffle
                                ? const Color(0xFF1DB954)
                                : Colors.grey[400],
                            size: 24),
                        onPressed: () =>
                            setState(() => isShuffle = !isShuffle),
                      ),

                      // Previous
                      IconButton(
                        icon: const Icon(Icons.skip_previous_rounded,
                            color: Colors.white, size: 36),
                        onPressed: () {},
                      ),

                      // Play / Pause
                      GestureDetector(
                        onTap: () => setState(() => isPlaying = !isPlaying),
                        child: Container(
                          width: 64,
                          height: 64,
                          decoration: const BoxDecoration(
                            color: Colors.white,
                            shape: BoxShape.circle,
                          ),
                          child: AnimatedSwitcher(
                            duration: const Duration(milliseconds: 200),
                            transitionBuilder: (child, anim) =>
                                ScaleTransition(scale: anim, child: child),
                            child: Icon(
                              isPlaying
                                  ? Icons.pause_rounded
                                  : Icons.play_arrow_rounded,
                              key: ValueKey(isPlaying),
                              color: Colors.black,
                              size: 36,
                            ),
                          ),
                        ),
                      ),

                      // Next
                      IconButton(
                        icon: const Icon(Icons.skip_next_rounded,
                            color: Colors.white, size: 36),
                        onPressed: () {},
                      ),

                      // Repeat
                      IconButton(
                        icon: Icon(
                          repeatMode == 2
                              ? Icons.repeat_one_rounded
                              : Icons.repeat_rounded,
                          color: repeatMode > 0
                              ? const Color(0xFF1DB954)
                              : Colors.grey[400],
                          size: 24,
                        ),
                        onPressed: () => setState(
                            () => repeatMode = (repeatMode + 1) % 3),
                      ),
                    ],
                  ),

                  const SizedBox(height: 20),

                  // Bottom actions
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      IconButton(
                        icon: Icon(Icons.devices_rounded,
                            color: Colors.grey[400], size: 20),
                        onPressed: () {},
                      ),
                      Row(
                        children: [
                          IconButton(
                            icon: Icon(Icons.share_rounded,
                                color: Colors.grey[400], size: 20),
                            onPressed: () {},
                          ),
                          IconButton(
                            icon: Icon(Icons.queue_music_rounded,
                                color: Colors.grey[400], size: 20),
                            onPressed: () {},
                          ),
                        ],
                      ),
                    ],
                  ),
                  const Spacer(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

//====================== Home Page ======================//
class HomePage extends StatelessWidget {
  final List<String> albums = [
    "Chill Mix",
    "Workout",
    "Focus",
    "Indie",
    "Pop Hits",
    "Rock Classics"
  ];

  final List<String> recentlyPlayed = [
    "Album 1",
    "Album 2",
    "Album 3",
    "Album 4",
    "Album 5",
  ];

  final List<Color> albumColors = [
    const Color(0xFF1DB954),
    const Color(0xFFE91E63),
    const Color(0xFF2196F3),
    const Color(0xFFFF9800),
    const Color(0xFF9C27B0),
    const Color(0xFFFF5722),
  ];

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            Text(
              "Good evening",
              style: const TextStyle(
                  fontSize: 26, fontWeight: FontWeight.bold, letterSpacing: 0.3),
            ),
            const SizedBox(height: 20),

            // Albums grid — compact cards like Spotify
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: albums.length,
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 3.2,
              ),
              itemBuilder: (context, index) {
                return albumCard(albums[index], albumColors[index]);
              },
            ),

            const SizedBox(height: 30),
            const Text(
              "Recently Played",
              style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.2),
            ),
            const SizedBox(height: 14),

            SizedBox(
              height: 160,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                itemCount: recentlyPlayed.length,
                itemBuilder: (context, index) {
                  return recentCard(recentlyPlayed[index]);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget albumCard(String title, Color color) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF282828),
        borderRadius: BorderRadius.circular(6),
      ),
      clipBehavior: Clip.antiAlias,
      child: Row(
        children: [
          Container(
            width: 48,
            height: double.infinity,
            color: color.withOpacity(0.8),
            child: const Icon(Icons.music_note, color: Colors.white, size: 20),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                  fontWeight: FontWeight.w600, fontSize: 13, color: Colors.white),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  Widget recentCard(String title) {
    return Container(
      width: 120,
      margin: const EdgeInsets.only(right: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              color: const Color(0xFF282828),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.album_rounded,
                color: Colors.grey, size: 40),
          ),
          const SizedBox(height: 8),
          Text(
            title,
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

//====================== Search Page ======================//
class SearchPage extends StatelessWidget {
  final List<String> genres = [
    "Pop",
    "Hip Hop",
    "Rock",
    "Indie",
    "Jazz",
    "Electronic",
    "Classical",
    "R&B"
  ];

  final List<Color> genreColors = [
    const Color(0xFFE91E63),
    const Color(0xFFBA68C8),
    const Color(0xFFEF5350),
    const Color(0xFF66BB6A),
    const Color(0xFFFFCA28),
    const Color(0xFF29B6F6),
    const Color(0xFF8D6E63),
    const Color(0xFF7E57C2),
  ];

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Search",
              style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 20),
            TextField(
              decoration: InputDecoration(
                hintText: "What do you want to listen to?",
                hintStyle: TextStyle(color: Colors.grey[500]),
                prefixIcon:
                    Icon(Icons.search_rounded, color: Colors.grey[400]),
                filled: true,
                fillColor: const Color(0xFF282828),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              "Browse all",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: GridView.builder(
                itemCount: genres.length,
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  childAspectRatio: 1.8,
                ),
                itemBuilder: (context, index) {
                  return genreCard(genres[index], genreColors[index]);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget genreCard(String genre, Color color) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color, color.withOpacity(0.7)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.all(14),
      child: Align(
        alignment: Alignment.bottomLeft,
        child: Text(
          genre,
          style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Colors.white),
        ),
      ),
    );
  }
}

//====================== Library Page ======================//
class LibraryPage extends StatefulWidget {
  @override
  _LibraryPageState createState() => _LibraryPageState();
}

class _LibraryPageState extends State<LibraryPage> {
  List<String> playlists = ["Liked Songs"];

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text("Your Library",
                    style:
                        TextStyle(fontSize: 26, fontWeight: FontWeight.bold)),
                IconButton(
                  icon: const Icon(Icons.add_rounded, size: 28),
                  onPressed: () {
                    showDialog(
                      context: context,
                      builder: (context) {
                        String newName = "";
                        return AlertDialog(
                          backgroundColor: const Color(0xFF282828),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16)),
                          title: const Text("New Playlist"),
                          content: TextField(
                            onChanged: (value) => newName = value,
                            decoration: InputDecoration(
                              hintText: "Playlist Name",
                              hintStyle: TextStyle(color: Colors.grey[500]),
                              filled: true,
                              fillColor: const Color(0xFF3A3A3A),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(10),
                                borderSide: BorderSide.none,
                              ),
                            ),
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(context),
                              child: Text("Cancel",
                                  style:
                                      TextStyle(color: Colors.grey[400])),
                            ),
                            TextButton(
                              onPressed: () {
                                if (newName.isNotEmpty) {
                                  setState(() => playlists.add(newName));
                                }
                                Navigator.pop(context);
                              },
                              child: const Text("Add",
                                  style:
                                      TextStyle(color: Color(0xFF1DB954))),
                            ),
                          ],
                        );
                      },
                    );
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),
            Expanded(
              child: ListView.builder(
                itemCount: playlists.length,
                itemBuilder: (context, index) {
                  final isLiked = index == 0;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 4),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 4, vertical: 4),
                      leading: Container(
                        width: 52,
                        height: 52,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(6),
                          gradient: isLiked
                              ? const LinearGradient(
                                  colors: [
                                    Color(0xFF7B4FFF),
                                    Color(0xFF1DB954)
                                  ],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                )
                              : null,
                          color: isLiked ? null : const Color(0xFF282828),
                        ),
                        child: Icon(
                          isLiked
                              ? Icons.favorite_rounded
                              : Icons.music_note_rounded,
                          color: Colors.white,
                          size: 24,
                        ),
                      ),
                      title: Text(
                        playlists[index],
                        style: const TextStyle(
                            fontWeight: FontWeight.w500, fontSize: 15),
                      ),
                      subtitle: Text(
                        isLiked ? "Playlist • 24 songs" : "Playlist",
                        style: TextStyle(
                            color: Colors.grey[500], fontSize: 13),
                      ),
                      onTap: () {},
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

//====================== MainScreen ======================//
class MainScreen extends StatefulWidget {
  @override
  _MainScreenState createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;
  bool _isFullPlayer = false;

  late List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      HomePage(),
      SearchPage(),
      LibraryPage(),
    ];
  }

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  void _toggleFullPlayer() {
    setState(() {
      _isFullPlayer = !_isFullPlayer;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Scaffold(
          body: Column(
            children: [
              Expanded(child: _pages[_selectedIndex]),
              MiniPlayer(onTap: _toggleFullPlayer),
            ],
          ),
          bottomNavigationBar: BottomNavigationBar(
            currentIndex: _selectedIndex,
            onTap: _onItemTapped,
            backgroundColor: const Color(0xFF1A1A1A),
            selectedItemColor: const Color(0xFF1DB954),
            unselectedItemColor: Colors.grey,
            type: BottomNavigationBarType.fixed,
            selectedFontSize: 12,
            unselectedFontSize: 12,
            items: const [
              BottomNavigationBarItem(
                icon: Icon(Icons.home_rounded),
                label: "Home",
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.search_rounded),
                label: "Search",
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.library_music_rounded),
                label: "Library",
              ),
            ],
          ),
        ),

        // Full player overlay
        if (_isFullPlayer)
          FullPlayerScreen(onClose: _toggleFullPlayer),
      ],
    );
  }
}