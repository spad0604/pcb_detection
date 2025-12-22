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

  // Control panel state
  final availablePorts = <String>[].obs;
  final selectedPort = '/dev/ttyACM0'.obs;
  final selectedCameraIndex = 4.obs;
  final isCameraOpened = false.obs;
  final isTestingDetection = false.obs;
  final Rxn<Map<String, dynamic>> lineStatus = Rxn<Map<String, dynamic>>();

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
    refreshAvailablePorts();
    _fetchCameraInfo();
    _startLineStatusPolling();
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
    // Không gọi _pullLiveAnalysis vì không detect liên tục
  }

  void _startWebSocketStream() {
    _stopWebSocketStream();
    if (!liveEnabled.value) return;

    // Không dùng WebSocket nữa, chỉ dùng HTTP polling để có annotated frames
    _addLog('Sử dụng HTTP polling cho stream (để hiển thị detection boxes)',
        level: ActivityLogLevel.info);
    _startHttpPollingFallback();

    // KHÔNG chạy analysis timer - chỉ detect khi có trigger (Arduino hoặc Test button)
    // Kết quả detection sẽ tự động hiển thị qua line status polling
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
        Timer.periodic(const Duration(milliseconds: 33), (_) {
      // Không await để không block timer
      _pullLiveFrame();
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
    // Chỉ log, không dùng snackbar để tránh lỗi overlay
    _addLog('$title: $message', level: ActivityLogLevel.info);
  }

  // ===== Control Panel Methods =====
  
  Future<void> triggerTestDetection() async {
    if (isTestingDetection.value) return;
    
    isTestingDetection.value = true;
    _addLog('Triggering manual detection test...', level: ActivityLogLevel.info);
    
    try {
      await apiService.triggerTestDetection();
      _addLog('Detection test triggered successfully', level: ActivityLogLevel.info);
      _notify('Test Detection', 'Đã trigger detection, đợi kết quả...');
      
      // Đợi 2s rồi lấy kết quả từ line status
      await Future.delayed(const Duration(seconds: 2));
      
      // Lấy kết quả detection
      try {
        final result = await apiService.getLastLineInference();
        liveAnalysis.value = result;
        _addLog('Detection result: ${result.isDefective ? "THIẾU" : "ĐỦ"} linh kiện', 
            level: result.isDefective ? ActivityLogLevel.warning : ActivityLogLevel.success);
      } catch (e) {
        _addLog('Chưa có kết quả detection', level: ActivityLogLevel.warning);
      }
    } catch (e) {
      _addLog('Test detection failed: $e', level: ActivityLogLevel.error);
      _notify('Lỗi', 'Không thể trigger detection: $e');
    } finally {
      isTestingDetection.value = false;
    }
  }

  Future<void> refreshAvailablePorts() async {
    try {
      final portsData = await apiService.getAvailablePorts();
      availablePorts.value = List<String>.from(portsData['ports'] ?? []);
      final current = portsData['current'] as String?;
      if (current != null) {
        selectedPort.value = current;
      }
      _addLog('Refreshed serial ports: ${availablePorts.length} found');
    } catch (e) {
      _addLog('Failed to refresh ports: $e', level: ActivityLogLevel.warning);
    }
  }

  void selectPort(String port) {
    selectedPort.value = port;
    _addLog('Selected port: $port (Note: Restart backend to apply)', 
        level: ActivityLogLevel.info);
    _notify('Port Selected', 'Chọn $port. Restart backend với NANO_PORT=$port');
  }

  Future<void> switchCamera(int index) async {
    try {
      _addLog('Switching to camera $index...');
      await apiService.switchCamera(index);
      selectedCameraIndex.value = index;
      _addLog('Switched to camera $index successfully', level: ActivityLogLevel.info);
      _notify('Camera Switched', 'Đã chuyển sang camera $index');
      await _fetchCameraInfo();
      await refreshLiveFrame();
    } catch (e) {
      _addLog('Failed to switch camera: $e', level: ActivityLogLevel.error);
      _notify('Lỗi', 'Không thể chuyển camera: $e');
    }
  }

  Future<void> _fetchCameraInfo() async {
    try {
      final info = await apiService.getCameraInfo();
      selectedCameraIndex.value = info['camera_index'] as int? ?? 4;
      isCameraOpened.value = info['is_opened'] as bool? ?? false;
    } catch (e) {
      _addLog('Failed to fetch camera info: $e', level: ActivityLogLevel.warning);
    }
  }

  void _startLineStatusPolling() {
    Timer.periodic(const Duration(seconds: 2), (timer) async {
      if (!liveEnabled.value) return;
      
      try {
        final status = await apiService.getLineStatus();
        lineStatus.value = status;
        
        // Update last inference if available
        final lastInf = status['lastInference'];
        if (lastInf != null) {
          liveAnalysis.value = InferenceResult.fromJson(lastInf as Map<String, dynamic>);
        }
      } catch (e) {
        // Silent fail, không spam logs
      }
    });
  }
}

