import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../dashboard_controller.dart';

class TrainingPanel extends StatelessWidget {
  const TrainingPanel({super.key, required this.controller});

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
              'Giám sát dây chuyền',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            Obx(() {
              return SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('Live conveyor feed'),
                subtitle: const Text(
                    'Bật công tắc để nhận hình ảnh và kết quả từ camera theo thời gian thực.'),
                value: controller.liveEnabled.value,
                onChanged: controller.toggleLiveStream,
              );
            }),
            const Divider(height: 32),
            Obx(() {
              final liveResult = controller.liveAnalysis.value;
              final bool hasData = liveResult != null;
              final bool defective = liveResult?.isDefective ?? false;
              final color = !hasData
                  ? Colors.blueGrey
                  : defective
                      ? Colors.red
                      : Colors.green;
              final title = !hasData
                  ? 'Đang chờ khung hình...'
                  : defective
                      ? 'Phát hiện lỗi trên line'
                      : 'Line ổn định';
              final subtitle = !hasData
                  ? 'Chưa nhận được bounding box từ backend. Kiểm tra camera hoặc backend.'
                  : 'Confidence ${(liveResult!.confidence * 100).toStringAsFixed(1)}% với ${liveResult.missingAreas.length} vùng cảnh báo.';

              return Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: color.withOpacity(0.12),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      hasData
                          ? (defective ? Icons.warning_amber : Icons.check_circle)
                          : Icons.wifi_tethering,
                      color: color,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(title,
                              style: TextStyle(
                                  color: color, fontWeight: FontWeight.w600)),
                          const SizedBox(height: 4),
                          Text(subtitle),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: 'Refresh ngay',
                      onPressed: controller.refreshLiveFrame,
                      icon: const Icon(Icons.refresh),
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 20),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Kiểm tra thủ công'),
              subtitle: Obx(() {
                if (controller.isInferencing.value) {
                  return const Text('Đang chạy inference cho ảnh vừa tải lên...');
                }
                return const Text(
                    'Tải ảnh PCB từ thư mục để xác thực kết quả khi cần.');
              }),
              trailing: Obx(() => ElevatedButton.icon(
                    onPressed: controller.isInferencing.value
                        ? null
                        : controller.runInference,
                    icon: controller.isInferencing.value
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.upload_file),
                    label: Text(controller.isInferencing.value
                        ? 'Đang xử lý'
                        : 'Upload & Kiểm tra'),
                  )),
            ),
            const SizedBox(height: 12),
            const Text(
              'Ghi chú vận hành',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            const _TipItem(
              icon: Icons.hub_outlined,
              text:
                  'Mô hình YOLO đã được đóng băng với checkpoint mới nhất, không cần training lại trong ứng dụng.',
            ),
            const _TipItem(
              icon: Icons.security_outlined,
              text:
                  'Nếu live feed mất tín hiệu > 5 giây, kiểm tra lại backend hoặc camera và nhấn "Refresh".',
            ),
            const _TipItem(
              icon: Icons.science_outlined,
              text:
                  'Ưu tiên inference thủ công khi cần xác minh nhanh với ảnh ngoại lệ.',
            ),
          ],
        ),
      ),
    );
  }
}

class _TipItem extends StatelessWidget {
  const _TipItem({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: Colors.blueGrey.shade600),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(color: Colors.black87),
            ),
          ),
        ],
      ),
    );
  }
}
