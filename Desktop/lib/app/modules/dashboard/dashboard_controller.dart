import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../models/activity_log_entry.dart';
import '../../models/dataset_sample.dart';
import '../../models/inference_result.dart';
import '../../models/training_job.dart';
import '../../services/api_service.dart';

class DashboardController extends GetxController {
  DashboardController(this.apiService);

  final ApiService apiService;

  final dataset = <DatasetSample>[].obs;
  final logs = <ActivityLogEntry>[].obs;
  final activeLabel = 'missing'.obs;
  final trainingStatus = TrainingJobStatus.idle().obs;
  final RxnString currentJobId = RxnString();
  final epochs = 20.obs;
  final testSplit = 0.2.obs;
  final isUploading = false.obs;
  final isTraining = false.obs;
  final isInferencing = false.obs;
  final Rxn<InferenceResult> lastInference = Rxn<InferenceResult>();
  final Rxn<InferenceResult> liveAnalysis = Rxn<InferenceResult>();
  final Rxn<Uint8List> liveFrame = Rxn<Uint8List>();
  final liveEnabled = true.obs;
  final boardName = ''.obs;
  late final TextEditingController boardNameController;

  Timer? _pollTimer;
  Timer? _liveTimer;
  Timer? _analysisTimer;
  bool _liveWarningShown = false;
  bool _liveAnalysisWarningShown = false;

  @override
  void onInit() {
    super.onInit();
    boardNameController = TextEditingController();
    boardNameController.addListener(() {
      boardName.value = boardNameController.text;
    });
    fetchDataset();
    _startLiveStream();
  }

  @override
  void onClose() {
    _pollTimer?.cancel();
    _liveTimer?.cancel();
    _analysisTimer?.cancel();
    boardNameController.dispose();
    super.onClose();
  }

  Future<void> fetchDataset() async {
    try {
      final remote = await apiService.fetchDataset();
      dataset.assignAll(remote);
      _addLog('Đồng bộ dữ liệu thành công: ${remote.length} ảnh',
          level: ActivityLogLevel.success);
    } catch (error) {
      _addLog('Không lấy được dataset: $error',
          level: ActivityLogLevel.warning);
    }
  }

  void toggleLiveStream(bool enabled) {
    liveEnabled.value = enabled;
    if (enabled) {
      _startLiveStream();
    } else {
      _liveTimer?.cancel();
      _analysisTimer?.cancel();
    }
  }

  Future<void> refreshLiveFrame() async {
    await _pullLiveFrame();
    await _pullLiveAnalysis();
  }

  void _startLiveStream() {
    _liveTimer?.cancel();
    _analysisTimer?.cancel();
    if (!liveEnabled.value) return;
    // Polling với interval 100ms (~10 FPS) để mượt hơn
    _liveTimer = Timer.periodic(const Duration(milliseconds: 100), (_) async {
      await _pullLiveFrame();
    });
    _analysisTimer = Timer.periodic(const Duration(milliseconds: 600), (_) async {
      await _pullLiveAnalysis();
    });
  }

  Future<void> _pullLiveFrame() async {
    try {
      final frame = await apiService.fetchLiveFrame();
      if (frame != null) {
        liveFrame.value = frame;
        _liveWarningShown = false;
      } else {
        if (!_liveWarningShown) {
          _addLog('Không nhận được frame từ stream',
              level: ActivityLogLevel.warning);
          _liveWarningShown = true;
        }
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
        _addLog('Live analysis lỗi: $error', level: ActivityLogLevel.warning);
        _liveAnalysisWarningShown = true;
      }
    }
  }

  Future<void> addSamples() async {
    final pickResult = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.image,
      withData: false,
    );
    if (pickResult == null) return;

    isUploading.value = true;
    final label = activeLabel.value;

    try {
      for (final file in pickResult.files) {
        final path = file.path;
        if (path == null) continue;
        final sample = DatasetSample(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          name: file.name,
          label: label,
          sizeBytes: file.size,
          createdAt: DateTime.now(),
          localPath: path,
        );
        dataset.add(sample);
        final uploaded = await apiService.uploadSample(
          file: File(path),
          label: label,
        );
        if (uploaded != null) {
          dataset.remove(sample);
          dataset.add(uploaded);
        }
      }
      _addLog('Upload ${pickResult.count} ảnh nhãn "$label"',
          level: ActivityLogLevel.success);
    } catch (error) {
      _addLog('Upload lỗi: $error', level: ActivityLogLevel.error);
      rethrow;
    } finally {
      isUploading.value = false;
    }
  }

  void changeLabel(String label) => activeLabel.value = label;

  void updateEpochs(num value) => epochs.value = value.toInt().clamp(1, 500);

  void updateTestSplit(double value) => testSplit.value = value;

  Future<void> startTraining() async {
    if (dataset.isEmpty) {
      _notify('Thiếu dữ liệu', 'Hãy upload vài ảnh trước nhé');
      return;
    }
    final name = boardName.value.trim();
    if (name.isEmpty) {
      _notify('Thiếu tên PCB', 'Vui lòng nhập tên mạch PCB trước khi train');
      return;
    }
    isTraining.value = true;
    trainingStatus.value = TrainingJobStatus(
      state: TrainingState.running,
      progress: 0,
      message: 'Đang train...'
    );
    try {
      final jobId = await apiService.startTraining(
        epochs: epochs.value,
        testSplit: testSplit.value,
        boardName: name,
      );
      if (jobId == null) {
        _addLog('Backend offline? Không tạo được job train',
            level: ActivityLogLevel.warning);
        trainingStatus.value = TrainingJobStatus.idle();
        return;
      }
      currentJobId.value = jobId;
      _addLog('Bắt đầu train job $jobId', level: ActivityLogLevel.info);
      _startPolling(jobId);
    } catch (error) {
      _addLog('Train lỗi: $error', level: ActivityLogLevel.error);
      trainingStatus.value = TrainingJobStatus(
        state: TrainingState.failed,
        message: '$error',
      );
    } finally {
      isTraining.value = false;
    }
  }

  void _startPolling(String jobId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      try {
        final status = await apiService.fetchTrainingStatus(jobId);
        trainingStatus.value = status;
        if (status.state == TrainingState.succeeded) {
          _addLog('Train job $jobId hoàn tất',
              level: ActivityLogLevel.success);
          dataset.clear();
          await fetchDataset();
          boardNameController.clear();
          _pollTimer?.cancel();
        } else if (status.state == TrainingState.failed) {
          _addLog('Train job $jobId bị lỗi', level: ActivityLogLevel.error);
          _pollTimer?.cancel();
        }
      } catch (error) {
        _addLog('Không đọc được trạng thái train: $error',
            level: ActivityLogLevel.warning);
      }
    });
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
      final verdict = result.isDefective ? 'LỖI' : 'OK';
      _addLog('Kết quả inference: $verdict (conf ${result.confidence.toStringAsFixed(2)})',
          level: ActivityLogLevel.info);
    } catch (error) {
      final errorMsg = error.toString();
      _addLog('Inference lỗi: $errorMsg', level: ActivityLogLevel.error);
      
      // Hiển thị thông báo rõ ràng nếu là lỗi model chưa train
      if (errorMsg.contains('model') || errorMsg.contains('train')) {
        _notify(
          'Model chưa được train', 
          'Vui lòng upload ảnh chuẩn và train template trước khi inference (tối thiểu 3 ảnh).'
        );
      } else {
        _notify('Inference lỗi', errorMsg);
      }
    } finally {
      isInferencing.value = false;
    }
  }

  void _addLog(String message, {ActivityLogLevel level = ActivityLogLevel.info}) {
    logs.insert(0, ActivityLogEntry(level: level, message: message, timestamp: DateTime.now()));
    if (logs.length > 50) {
      logs.removeRange(50, logs.length);
    }
  }

  void _notify(String title, String message) {
    Get.snackbar(title, message, snackPosition: SnackPosition.BOTTOM);
  }
}
