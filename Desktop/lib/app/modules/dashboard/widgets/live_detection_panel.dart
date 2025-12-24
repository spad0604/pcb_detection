import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

import '../../../models/inference_result.dart';
import '../../../models/line_snapshot.dart';
import '../../../utils/component_labels.dart';
import '../dashboard_controller.dart';

class LiveDetectionPanel extends StatelessWidget {
  const LiveDetectionPanel({super.key, required this.controller});

  final DashboardController controller;

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: const [
                Icon(Icons.bolt_outlined),
                SizedBox(width: 8),
                Text('Kết quả detect từ camera',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: 12),
            const Text(
              'Mỗi lần băng tải hoặc nút "Test Detection" kích hoạt, ảnh và kết quả sẽ hiển thị ở đây.',
              style: TextStyle(color: Colors.black54, fontSize: 13),
            ),
            const SizedBox(height: 16),
            Obx(() {
              final snapshot = controller.lastLineSnapshot.value;
              if (snapshot == null) {
                return const _EmptyDetectionState();
              }
              return _SnapshotContent(snapshot: snapshot);
            }),
          ],
        ),
      ),
    );
  }
}

class _SnapshotContent extends StatelessWidget {
  const _SnapshotContent({required this.snapshot});

  final LineSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final InferenceResult? result = snapshot.inference;
    final isDefective = result?.isDefective ?? false;
    final verdictColor = isDefective ? Colors.red : Colors.green;
    final capturedAt = snapshot.capturedAt;
    final formattedTime = capturedAt == null
        ? 'Chưa xác định thời gian'
        : DateFormat('HH:mm:ss dd/MM').format(capturedAt.toLocal());
    final notes = result?.notes;
    final imageUrl = snapshot.annotatedImageUrl;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: verdictColor.withOpacity(0.12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(isDefective ? Icons.error_rounded : Icons.check_circle_rounded,
                  color: verdictColor),
              const SizedBox(width: 8),
              Text(
                result == null
                    ? 'Đang chờ kết quả'
                    : isDefective
                        ? 'Phát hiện sai lệch'
                        : 'PCB đạt yêu cầu',
                style: TextStyle(
                  color: verdictColor,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Text('Chụp lúc: $formattedTime',
            style: const TextStyle(color: Colors.black54, fontSize: 13)),
        if (notes != null) ...[
          const SizedBox(height: 4),
          Text(notes, style: const TextStyle(fontSize: 13)),
        ],
        const SizedBox(height: 16),
        if (imageUrl != null)
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: AspectRatio(
              aspectRatio: 4 / 3,
              child: Image.network(
                imageUrl,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) => Container(
                  color: Colors.red.shade50,
                  alignment: Alignment.center,
                  child: Text('Lỗi tải ảnh: $error', textAlign: TextAlign.center),
                ),
              ),
            ),
          )
        else
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 32),
            decoration: BoxDecoration(
              color: const Color(0xfff2f4f8),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.black12),
            ),
            child: const Text(
              'Backend chưa gửi ảnh annotate',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.black45),
            ),
          ),
        if (result != null) ...[
          const SizedBox(height: 16),
          _DetectionDetails(result: result),
        ],
      ],
    );
  }
}

class _DetectionDetails extends StatelessWidget {
  const _DetectionDetails({required this.result});

  final InferenceResult result;

  @override
  Widget build(BuildContext context) {
    final labels = result.missingComponentLabels;
    final missingCount = labels.length;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          result.isDefective
              ? (missingCount > 0
                  ? 'Thiếu $missingCount linh kiện quan trọng'
                  : 'Thiếu linh kiện (đang xác định)')
              : 'Không phát hiện linh kiện thiếu',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        if (result.isDefective && labels.isNotEmpty) ...[
          const Text('Danh sách linh kiện thiếu:',
              style: TextStyle(color: Colors.black87)),
          const SizedBox(height: 4),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: labels
                .map((label) => Chip(
                      label: Text(ComponentLabels.toVietnamese(label)),
                      backgroundColor: Colors.red.shade50,
                    ))
                .toList(),
          ),
          const SizedBox(height: 12),
        ],
        if (result.missingAreas.isEmpty)
          const Text('Không phát hiện vùng thiếu trong lần chụp này.',
              style: TextStyle(color: Colors.black54))
        else
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: result.missingAreas
                .map(
                  (area) => Chip(
                    label: Text(
                      '${ComponentLabels.toVietnamese(area.description)} (${(area.confidence * 100).toStringAsFixed(0)}%)',
                    ),
                    backgroundColor: Colors.orange.shade50,
                  ),
                )
                .toList(),
          ),
      ],
    );
  }
}

class _EmptyDetectionState extends StatelessWidget {
  const _EmptyDetectionState();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 40),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: const Color(0xfff2f4f8),
        border: Border.all(color: Colors.black12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: const [
          Icon(Icons.sensors_rounded, size: 48, color: Colors.black38),
          SizedBox(height: 12),
          Text('Chưa có lần detect nào',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          SizedBox(height: 6),
          Text('Nhấn "Chạy Detection Test" hoặc chờ board đi qua camera.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.black54)),
        ],
      ),
    );
  }
}
