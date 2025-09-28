// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:pocketspeak_app/main.dart';
import 'package:pocketspeak_app/pages/chat_page.dart';

void main() {
  testWidgets('PocketSpeak app starts with BindingPage', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const PocketSpeakApp());

    // Verify that the app shows the binding page with title
    expect(find.text('PocketSpeak'), findsOneWidget);
  });

  testWidgets('ChatPage displays correctly', (WidgetTester tester) async {
    // Build our chat page and trigger a frame.
    await tester.pumpWidget(const MaterialApp(home: ChatPage()));

    // Verify that the chat page shows correctly
    expect(find.text('小智AI'), findsOneWidget);
    expect(find.text('英语学习助手'), findsOneWidget);
    expect(find.text('输入英语消息...'), findsOneWidget);
  });
}
