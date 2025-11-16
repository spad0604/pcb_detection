import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../models/dataset_sample.dart';
import '../models/inference_result.dart';
import '../models/training_job.dart';

class ApiService {
  ApiService({Dio? dio, this.baseUrl = 'http://127.0.0.1:8000'})
      : _dio = dio ?? Dio(BaseOptions(baseUrl: baseUrl));

  final Dio _dio;
  final String baseUrl;

  Future<List<DatasetSample>> fetchDataset() async {
    try {
      final response = await _dio.get('/api/dataset');
      final data = response.data as List<dynamic>? ?? [];
      return data
          .map((entry) =>
              DatasetSample.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      throw ApiException(_describe(error));
    }
  }

  Future<DatasetSample?> uploadSample({
    required File file,
    required String label,
  }) async {
    if (!file.existsSync()) return null;
    final fileName = file.path.split(Platform.pathSeparator).last;
    final formData = FormData.fromMap({
      'label': label,
      'file': await MultipartFile.fromFile(file.path, filename: fileName),
    });
    try {
      final response = await _dio.post('/api/dataset', data: formData);
      return DatasetSample.fromJson(
        response.data as Map<String, dynamic>? ?? {},
      );
    } on DioException catch (error) {
      if (error.type == DioExceptionType.connectionError) {
        return null;
      }
      throw ApiException(_describe(error));
    }
  }

  Future<String?> startTraining({
    required int epochs,
    required double testSplit,
  }) async {
    try {
      final response = await _dio.post('/api/train', data: {
        'epochs': epochs,
        'testSplit': testSplit,
      });
      return response.data['jobId'] as String?;
    } on DioException catch (error) {
      if (error.type == DioExceptionType.connectionError) {
        return null;
      }
      throw ApiException(_describe(error));
    }
  }

  Future<TrainingJobStatus> fetchTrainingStatus(String jobId) async {
    try {
      final response = await _dio.get('/api/train/$jobId');
      return TrainingJobStatus.fromJson(
        response.data as Map<String, dynamic>? ?? {},
      );
    } on DioException catch (error) {
      throw ApiException(_describe(error));
    }
  }

  Future<InferenceResult?> runInference(File file) async {
    if (!file.existsSync()) return null;
    final fileName = file.path.split(Platform.pathSeparator).last;
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path, filename: fileName),
    });
    try {
      final response = await _dio.post('/api/inference', data: formData);
      return InferenceResult.fromJson(
        response.data as Map<String, dynamic>? ?? {},
      );
    } on DioException catch (error) {
      if (error.type == DioExceptionType.connectionError) {
        return null;
      }
      throw ApiException(_describe(error));
    }
  }

  Future<Uint8List?> fetchLiveFrame() async {
    try {
      final response = await _dio.get<List<int>>(
        '/api/stream/frame',
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = response.data;
      if (bytes == null) return null;
      return Uint8List.fromList(bytes);
    } on DioException catch (error) {
      if (error.type == DioExceptionType.connectionError) {
        return null;
      }
      return null;
    }
  }

  String _describe(DioException error) {
    final status = error.response?.statusCode;
    final detail = error.response?.data;
    return 'API error (status: $status) -> $detail';
  }
}

class ApiException implements Exception {
  ApiException(this.message);
  final String message;
  @override
  String toString() => message;
}
