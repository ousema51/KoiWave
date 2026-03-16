import 'package:flutter/material.dart';
import 'dart:async';
import '../models/song.dart';
import '../models/album.dart';
import '../models/artist.dart';
import '../services/music_service.dart';
import '../widgets/song_tile.dart';
import '../widgets/album_card.dart';
import 'album_screen.dart';
import 'artist_screen.dart';

class SearchScreen extends StatefulWidget {
  final Function(Song) onSongSelected;

  const SearchScreen({super.key, required this.onSongSelected});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _searchController = TextEditingController();
  final MusicService _musicService = MusicService();
  Timer? _debounce;

  List<Song> _songResults = [];
  List<Album> _albumResults = [];
  List<Artist> _artistResults = [];
  bool _isSearching = false;
  bool _hasSearched = false;

  final List<String> _genres = [
    'Pop', 'Hip Hop', 'Rock', 'Indie',
    'Jazz', 'Electronic', 'Classical', 'R&B',
  ];

  final List<Color> _genreColors = [
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
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _search(String query) async {
    if (query.trim().isEmpty) {
      setState(() {
        _songResults = [];
        _albumResults = [];
        _artistResults = [];
        _hasSearched = false;
      });
      return;
    }

    setState(() => _isSearching = true);

    try {
      final songs = await _musicService.searchSongs(query);
      if (mounted) {
        setState(() {
          _songResults = songs;
          _hasSearched = true;
          _isSearching = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSearching = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Search failed: $e'),
            backgroundColor: Colors.red[700],
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Search',
              style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _searchController,
              style: const TextStyle(color: Colors.white),
              onChanged: (value) {
                // Update UI (clear button) immediately
                if (mounted) setState(() {});
                // Debounce the search calls
                _debounce?.cancel();
                _debounce = Timer(const Duration(milliseconds: 500), () {
                  if (_searchController.text == value) {
                    _search(value);
                  }
                });
              },
              onSubmitted: _search,
              decoration: InputDecoration(
                hintText: 'What do you want to listen to?',
                hintStyle: TextStyle(color: Colors.grey[500]),
                prefixIcon:
                    Icon(Icons.search_rounded, color: Colors.grey[400]),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: Icon(Icons.clear_rounded,
                            color: Colors.grey[400]),
                        onPressed: () {
                          _searchController.clear();
                          if (mounted) setState(() {});
                          _search('');
                        },
                      )
                    : null,
                filled: true,
                fillColor: const Color(0xFF282828),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
            const SizedBox(height: 20),
            if (_isSearching)
              const Center(
                child: CircularProgressIndicator(color: Color(0xFF0B3B8C)),
              )
            else if (_hasSearched)
              Expanded(child: _buildSearchResults())
            else
              Expanded(child: _buildBrowseAll()),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchResults() {
    return ListView(
      children: [
        if (_songResults.isNotEmpty) ...[
          const Text(
            'Songs',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ..._songResults.map((song) => SongTile(
                song: song,
                onTap: () => widget.onSongSelected(song),
              )),
          const SizedBox(height: 20),
        ],
        if (_songResults.isEmpty)
          const Center(
            child: Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Text(
                'No results found',
                style: TextStyle(color: Colors.grey, fontSize: 16),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildBrowseAll() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Browse all',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: GridView.builder(
            itemCount: _genres.length,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 1.8,
            ),
            itemBuilder: (context, index) {
              final color = _genreColors[index];
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
                    _genres[index],
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
