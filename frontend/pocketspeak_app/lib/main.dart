import 'package:flutter/material.dart';
import 'pages/binding_page.dart';

void main() {
  runApp(const PocketSpeakApp());
}

class PocketSpeakApp extends StatelessWidget {
  const PocketSpeakApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PocketSpeak',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF667EEA),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        fontFamily: 'SF Pro Display',
      ),
      home: const BindingPage(),
    );
  }
}

