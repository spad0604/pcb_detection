// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'dart:io';

import 'package:desktop/app/models/dataset_sample.dart';
import 'package:desktop/app/models/inference_result.dart';
import 'package:desktop/app/models/training_job.dart';
import 'package:desktop/app/services/api_service.dart';
import 'package:desktop/main.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.put<ApiService>(_FakeApiService());
  });

  testWidgets('Dashboard renders key panels', (WidgetTester tester) async {
    await tester.pumpWidget(const PcbInspectorApp());

    expect(find.text('Dataset'), findsOneWidget);
    expect(find.text('Training'), findsOneWidget);
    expect(find.text('Inference'), findsOneWidget);
  });
}

class _FakeApiService extends ApiService {
  _FakeApiService() : super(dio: Dio(), baseUrl: '');

  @override
  Future<List<DatasetSample>> fetchDataset() async => [];

  @override
  Future<DatasetSample?> uploadSample({required File file, required String label}) async => null;

  @override
  Future<String?> startTraining({required int epochs, required double testSplit}) async => 'job';

  @override
  Future<TrainingJobStatus> fetchTrainingStatus(String jobId) async => TrainingJobStatus.idle();

  @override
  Future<InferenceResult?> runInference(File file) async => InferenceResult(
        isDefective: false,
        confidence: 0.95,
        timestamp: DateTime.now(),
      );
}
