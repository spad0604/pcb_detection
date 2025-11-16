import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
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
  final Rxn<Uint8List> liveFrame = Rxn<Uint8List>();
  final liveEnabled = true.obs;

  Timer? _pollTimer;
  Timer? _liveTimer;
  bool _liveWarningShown = false;

  @override
  void onInit() {
    super.onInit();
    fetchDataset();
    _startLiveStream();
  }

  @override
  void onClose() {
    _pollTimer?.cancel();
    _liveTimer?.cancel();
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
    }
  }

  Future<void> refreshLiveFrame() async {
    await _pullLiveFrame();
  }

  void _startLiveStream() {
    _liveTimer?.cancel();
    if (!liveEnabled.value) return;
    _liveTimer = Timer.periodic(const Duration(milliseconds: 800), (_) async {
      await _pullLiveFrame();
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
        return;
      }
      lastInference.value = result;
      final verdict = result.isDefective ? 'LỖI' : 'OK';
      _addLog('Kết quả inference: $verdict (conf ${result.confidence.toStringAsFixed(2)})',
          level: ActivityLogLevel.info);
    } catch (error) {
      _addLog('Inference lỗi: $error', level: ActivityLogLevel.error);
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
