import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/inference_result.dart';
import '../models/line_snapshot.dart';

class ApiService {
  ApiService({Dio? dio, this.baseUrl = 'http://127.0.0.1:8000'})
      : _dio = dio ?? Dio(BaseOptions(baseUrl: baseUrl));

  final Dio _dio;
  final String baseUrl;

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
      // Lấy detail từ response nếu có
      final detail = error.response?.data?['detail'] as String?;
      if (detail != null) {
        throw ApiException(detail);
      }
      throw ApiException(_describe(error));
    }
  }

  Future<Uint8List?> fetchLiveFrame() async {
    try {
      final response = await _dio.get<List<int>>(
        '/api/stream/frame',
        options: Options(
          responseType: ResponseType.bytes,
          receiveTimeout: const Duration(milliseconds: 2000),
          sendTimeout: const Duration(milliseconds: 2000),
        ),
      );
      final bytes = response.data;
      if (bytes == null) return null;
      return Uint8List.fromList(bytes);
    } on DioException catch (error) {
      if (error.type == DioExceptionType.connectionError ||
          error.type == DioExceptionType.receiveTimeout ||
          error.type == DioExceptionType.sendTimeout) {
        return null;
      }
      return null;
    }
  }

  /// Lấy URL của MJPEG stream (dùng cho WebView hoặc browser)
  String getMJPEGStreamUrl() {
    return '$baseUrl/api/stream/mjpeg';
  }

  Future<InferenceResult?> fetchLiveAnalysis() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/stream/analyze');
      final data = response.data;
      if (data == null) return null;
      return InferenceResult.fromJson(data);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404 ||
          error.response?.statusCode == 400 ||
          error.type == DioExceptionType.connectionError) {
        return null;
      }
      throw ApiException(_describe(error));
    }
  }

  String _describe(DioException error) {
    final status = error.response?.statusCode;
    final detail = error.response?.data;
    return 'API error (status: $status) -> $detail';
  }

  /// Tạo WebSocket connection cho video stream
  WebSocketChannel? createVideoStreamChannel() {
    try {
      final wsUrl = baseUrl.replaceFirst('http://', 'ws://').replaceFirst('https://', 'wss://');
      final channel = WebSocketChannel.connect(Uri.parse('$wsUrl/api/stream/ws'));
      return channel;
    } catch (e) {
      return null;
    }
  }

  // ===== Control Panel APIs =====
  
  Future<void> triggerTestDetection() async {
    try {
      await _dio.post('/api/line/test_detection');
    } on DioException catch (error) {
      final detail = error.response?.data?['detail'] as String?;
      throw ApiException(detail ?? _describe(error));
    }
  }

  Future<Map<String, dynamic>> getAvailablePorts() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/config/available_ports');
      return response.data ?? {};
    } on DioException catch (error) {
      throw ApiException(_describe(error));
    }
  }

  Future<void> switchCamera(int cameraIndex) async {
    try {
      await _dio.post('/api/config/camera', data: {'camera_index': cameraIndex});
    } on DioException catch (error) {
      final detail = error.response?.data?['detail'] as String?;
      throw ApiException(detail ?? _describe(error));
    }
  }

  Future<Map<String, dynamic>> getCameraInfo() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/config/camera');
      return response.data ?? {};
    } on DioException catch (error) {
      throw ApiException(_describe(error));
    }
  }

  Future<Map<String, dynamic>> getLineStatus() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/line/status');
      return response.data ?? {};
    } on DioException catch (error) {
      throw ApiException(_describe(error));
    }
  }

  Future<InferenceResult> getLastLineInference() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/line/last_inference');
      if (response.data == null) {
        throw ApiException('Chưa có inference nào từ băng tải');
      }
      return InferenceResult.fromJson(response.data!);
    } on DioException catch (error) {
      final detail = error.response?.data?['detail'] as String?;
      throw ApiException(detail ?? _describe(error));
    }
  }

  Future<LineSnapshot?> getLastLineSnapshot() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/line/last_snapshot');
      final data = response.data;
      if (data == null) {
        return null;
      }
      return LineSnapshot.fromJson(data);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return null;
      }
      final detail = error.response?.data?['detail'] as String?;
      throw ApiException(detail ?? _describe(error));
    }
  }
}

class ApiException implements Exception {
  ApiException(this.message);
  final String message;
  @override
  String toString() => message;
}
