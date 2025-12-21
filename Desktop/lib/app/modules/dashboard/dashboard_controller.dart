import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../models/activity_log_entry.dart';
import '../../models/inference_result.dart';
import '../../services/api_service.dart';

class DashboardController extends GetxController {
  DashboardController(this.apiService);

  final ApiService apiService;

  final logs = <ActivityLogEntry>[].obs;
  final isInferencing = false.obs;
  final Rxn<InferenceResult> lastInference = Rxn<InferenceResult>();
  final RxnString lastInferenceImagePath = RxnString();
  final Rxn<InferenceResult> liveAnalysis = Rxn<InferenceResult>();
  final Rxn<Uint8List> liveFrame = Rxn<Uint8List>();
  final liveEnabled = true.obs;

  Timer? _liveTimer;
  Timer? _analysisTimer;
  WebSocketChannel? _wsChannel;
  StreamSubscription? _wsSubscription;
  bool _liveWarningShown = false;
  bool _liveAnalysisWarningShown = false;

  @override
  void onInit() {
    super.onInit();
    _startWebSocketStream();
  }

  @override
  void onClose() {
    _liveTimer?.cancel();
    _analysisTimer?.cancel();
    _wsSubscription?.cancel();
    _wsChannel?.sink.close();
    super.onClose();
  }

  void toggleLiveStream(bool enabled) {
    liveEnabled.value = enabled;
    if (enabled) {
      _startWebSocketStream();
    } else {
      _stopWebSocketStream();
      _analysisTimer?.cancel();
    }
  }

  Future<void> refreshLiveFrame() async {
    await _pullLiveFrame();
    await _pullLiveAnalysis();
  }

  void _startWebSocketStream() {
    _stopWebSocketStream();
    if (!liveEnabled.value) return;

    try {
      _wsChannel = apiService.createVideoStreamChannel();
      if (_wsChannel == null) {
        _addLog('Không thể kết nối WebSocket, chuyển sang polling',
            level: ActivityLogLevel.warning);
        _startHttpPollingFallback();
        return;
      }

      _wsSubscription = _wsChannel!.stream.listen(
        (message) {
          try {
            final data = json.decode(message as String) as Map<String, dynamic>;
            if (data['type'] == 'frame' && data['data'] != null) {
              final frameBase64 = data['data'] as String;
              final frameBytes = base64Decode(frameBase64);
              liveFrame.value = Uint8List.fromList(frameBytes);
              _liveWarningShown = false;
            }
          } catch (e) {
            if (!_liveWarningShown) {
              _addLog('Lỗi decode WebSocket frame: $e',
                  level: ActivityLogLevel.warning);
              _liveWarningShown = true;
            }
          }
        },
        onError: (error) {
          if (!_liveWarningShown) {
            _addLog('WebSocket lỗi: $error, fallback về polling',
                level: ActivityLogLevel.warning);
            _liveWarningShown = true;
          }
          _stopWebSocketStream();
          _startHttpPollingFallback();
        },
        onDone: () {
          if (liveEnabled.value) {
            _addLog('WebSocket đóng, đang thử kết nối lại...',
                level: ActivityLogLevel.warning);
            _stopWebSocketStream();
            Future.delayed(const Duration(seconds: 2), () {
              if (liveEnabled.value) {
                _startWebSocketStream();
              }
            });
          }
        },
      );

      _addLog('Đã kết nối WebSocket stream', level: ActivityLogLevel.success);
    } catch (e) {
      _addLog('Lỗi khởi tạo WebSocket: $e, fallback về polling',
          level: ActivityLogLevel.warning);
      _startHttpPollingFallback();
    }

    _analysisTimer?.cancel();
    _analysisTimer =
        Timer.periodic(const Duration(milliseconds: 600), (_) async {
      await _pullLiveAnalysis();
    });
  }

  void _stopWebSocketStream() {
    _wsSubscription?.cancel();
    _wsSubscription = null;
    _wsChannel?.sink.close();
    _wsChannel = null;
    _liveTimer?.cancel();
  }

  void _startHttpPollingFallback() {
    _liveTimer?.cancel();
    _liveTimer =
        Timer.periodic(const Duration(milliseconds: 120), (_) async {
      await _pullLiveFrame();
    });
  }

  Future<void> _pullLiveFrame() async {
    try {
      final frame = await apiService.fetchLiveFrame();
      if (frame != null) {
        liveFrame.value = frame;
        _liveWarningShown = false;
      } else if (!_liveWarningShown) {
        _addLog('Không nhận được frame từ camera',
            level: ActivityLogLevel.warning);
        _liveWarningShown = true;
      }
    } catch (error) {
      if (!_liveWarningShown) {
        _addLog('Stream lỗi: $error', level: ActivityLogLevel.error);
        _liveWarningShown = true;
      }
    }
  }

  Future<void> _pullLiveAnalysis() async {
    try {
      final result = await apiService.fetchLiveAnalysis();
      if (result != null) {
        liveAnalysis.value = result;
        _liveAnalysisWarningShown = false;
      }
    } catch (error) {
      if (!_liveAnalysisWarningShown) {
        _addLog('Live analysis lỗi: $error',
            level: ActivityLogLevel.warning);
        _liveAnalysisWarningShown = true;
      }
    }
  }

  Future<void> runInference() async {
    final pickResult = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      type: FileType.image,
      withData: false,
    );
    if (pickResult == null) return;
    final path = pickResult.files.single.path;
    if (path == null) return;

    isInferencing.value = true;
    try {
      final result = await apiService.runInference(File(path));
      if (result == null) {
        _addLog('Backend chưa sẵn sàng để infer',
            level: ActivityLogLevel.warning);
        _notify('Inference thất bại', 'Không nhận được kết quả từ server');
        return;
      }
      lastInference.value = result;
      lastInferenceImagePath.value = path;
      final verdict = result.isDefective ? 'LỖI' : 'OK';
      _addLog(
        'Kết quả inference: $verdict (conf ${result.confidence.toStringAsFixed(2)})',
        level: ActivityLogLevel.info,
      );
    } catch (error) {
      final errorMsg = error.toString();
      _addLog('Inference lỗi: $errorMsg', level: ActivityLogLevel.error);
      _notify('Inference lỗi', errorMsg);
    } finally {
      isInferencing.value = false;
    }
  }

  void _addLog(String message,
      {ActivityLogLevel level = ActivityLogLevel.info}) {
    logs.insert(
      0,
      ActivityLogEntry(
        level: level,
        message: message,
        timestamp: DateTime.now(),
      ),
    );
    if (logs.length > 50) {
      logs.removeRange(50, logs.length);
    }
  }

  void _notify(String title, String message) {
    if (Get.overlayContext != null) {
      Get.snackbar(
        title,
        message,
        snackPosition: SnackPosition.BOTTOM,
        duration: const Duration(seconds: 3),
      );
    } else {
      _addLog('$title: $message', level: ActivityLogLevel.info);
    }
  }
}
