import 'package:flutter/material.dart';
import 'screens/main_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Spotify Clone',
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
      debugShowCheckedModeBanner: false,
      routes: {
        '/main': (context) => const MainScreen(),
      },
      home: const MainScreen(),
    );
  }
}
