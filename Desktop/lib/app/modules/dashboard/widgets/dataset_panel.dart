import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../dashboard_controller.dart';

class DatasetPanel extends StatelessWidget {
  const DatasetPanel({super.key, required this.controller});

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
            const Text(
              'Trạng thái mô hình',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            Obx(() {
              final inference = controller.lastInference.value;
              if (inference == null) {
                return _InfoBanner(
                  icon: Icons.info_outline,
                  color: Colors.blueGrey,
                  title: 'Chưa có kết quả inference',
                  body:
                      'Upload một ảnh PCB bất kỳ để kiểm tra mô hình YOLO đã huấn luyện sẵn.',
                );
              }

              final verdict = inference.isDefective ? 'PCB THIẾU LINH KIỆN' : 'PCB OK';
              final verdictColor = inference.isDefective ? Colors.red : Colors.green;
              final missing = inference.missingAreas.length;

              return Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: verdictColor.withOpacity(0.1),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      verdict,
                      style: TextStyle(
                        color: verdictColor,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text('Confidence ${(inference.confidence * 100).toStringAsFixed(1)}%'),
                    const SizedBox(height: 4),
                    Text('Số vùng cảnh báo: $missing'),
                    if (controller.lastInferenceImagePath.value != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(
                            'Ảnh cuối: ${controller.lastInferenceImagePath.value!.split('/').last}'),
                      ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 24),
            const Text(
              'Quy trình vận hành',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            _StepItem(
              index: 1,
              title: 'Bật camera',
              body:
                  'Dùng switch "Live conveyor feed" để bật/tắt stream. Khi stream bật, ứng dụng sẽ tự động theo dõi và phân tích.',
            ),
            _StepItem(
              index: 2,
              title: 'Theo dõi realtime',
              body:
                  'Phần Live feed hiển thị bounding box và trạng thái phân tích hiện tại (từ YOLO).',
            ),
            _StepItem(
              index: 3,
              title: 'Kiểm tra thủ công',
              body:
                  'Sử dụng nút "Upload & Kiểm tra" để tải ảnh PCB bất kỳ và nhận kết quả ngay lập tức.',
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoBanner extends StatelessWidget {
  const _InfoBanner({
    required this.icon,
    required this.color,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: color.withOpacity(0.12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style:
                        TextStyle(color: color, fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(body),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StepItem extends StatelessWidget {
  const _StepItem({
    required this.index,
    required this.title,
    required this.body,
  });

  final int index;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 14,
            backgroundColor: Theme.of(context).colorScheme.primary,
            child: Text('$index',
                style: const TextStyle(color: Colors.white, fontSize: 12)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(body, style: const TextStyle(color: Colors.black54)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
