import 'package:flutter/material.dart';
import 'package:get/get.dart';

import 'app/routes/app_pages.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const PcbInspectorApp());
}

class PcbInspectorApp extends StatelessWidget {
  const PcbInspectorApp({super.key});

  @override
  Widget build(BuildContext context) {
    final baseTheme = ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff0b6ef6)),
      useMaterial3: true,
      fontFamily: 'Roboto',
    );

    return GetMaterialApp(
      title: 'PCB Inspector',
      debugShowCheckedModeBanner: false,
      theme: baseTheme.copyWith(
        scaffoldBackgroundColor: const Color(0xfff7f9fc),
        appBarTheme: baseTheme.appBarTheme.copyWith(
          backgroundColor: Colors.white,
          foregroundColor: Colors.black87,
          elevation: 0,
        ),
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
          isDense: true,
        ),
      ),
      defaultTransition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 250),
      initialRoute: AppPages.initial,
      getPages: AppPages.routes,
    );
  }
}
