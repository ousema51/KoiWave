import 'package:flutter/material.dart';
import '../models/song.dart';
import '../widgets/mini_player.dart';
import '../widgets/full_player.dart';
import 'home_screen.dart';
import 'search_screen.dart';
import 'library_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;
  bool _isFullPlayer = false;
  Song? _currentSong;

  void _onSongSelected(Song song) {
    setState(() => _currentSong = song);
  }

  void _toggleFullPlayer() {
    setState(() => _isFullPlayer = !_isFullPlayer);
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomeScreen(onSongSelected: _onSongSelected),
      SearchScreen(onSongSelected: _onSongSelected),
      LibraryScreen(onSongSelected: _onSongSelected),
    ];

    return Stack(
      children: [
        Scaffold(
          appBar: _selectedIndex == 0
              ? AppBar(
                  backgroundColor: const Color(0xFF121212),
                  elevation: 0,
                )
              : null,
          body: Column(
            children: [
              Expanded(child: pages[_selectedIndex]),
              MiniPlayer(
                onTap: _toggleFullPlayer,
                currentSong: _currentSong,
              ),
            ],
          ),
          bottomNavigationBar: BottomNavigationBar(
            currentIndex: _selectedIndex,
            onTap: (index) => setState(() => _selectedIndex = index),
            backgroundColor: const Color(0xFF1A1A1A),
            selectedItemColor: const Color(0xFF1DB954),
            unselectedItemColor: Colors.grey,
            type: BottomNavigationBarType.fixed,
            selectedFontSize: 12,
            unselectedFontSize: 12,
            items: const [
              BottomNavigationBarItem(
                icon: Icon(Icons.home_rounded),
                label: 'Home',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.search_rounded),
                label: 'Search',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.library_music_rounded),
                label: 'Library',
              ),
            ],
          ),
        ),
        if (_isFullPlayer)
          FullPlayerScreen(
            onClose: _toggleFullPlayer,
            currentSong: _currentSong,
          ),
      ],
    );
  }
}
