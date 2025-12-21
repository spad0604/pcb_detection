// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'dart:io';
import 'dart:typed_data';

import 'package:desktop/app/models/inference_result.dart';
import 'package:desktop/app/services/api_service.dart';
import 'package:desktop/main.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.put<ApiService>(_FakeApiService());
  });

  testWidgets('Dashboard renders inference-only panels', (WidgetTester tester) async {
    await tester.pumpWidget(const PcbInspectorApp());

    expect(find.text('Live conveyor feed'), findsOneWidget);
    expect(find.text('Kiểm tra PCB (Upload ảnh)'), findsOneWidget);
    expect(find.text('Activity log'), findsOneWidget);
  });
}

class _FakeApiService extends ApiService {
  _FakeApiService() : super(dio: Dio(), baseUrl: '');

  @override
  WebSocketChannel? createVideoStreamChannel() => null;

  @override
  Future<Uint8List?> fetchLiveFrame() async => Uint8List(0);

  @override
  Future<InferenceResult?> fetchLiveAnalysis() async => InferenceResult(
        isDefective: false,
        confidence: 0.85,
        timestamp: DateTime.now(),
      );

  @override
  Future<InferenceResult?> runInference(File file) async => InferenceResult(
        isDefective: false,
        confidence: 0.95,
        timestamp: DateTime.now(),
      );
}
