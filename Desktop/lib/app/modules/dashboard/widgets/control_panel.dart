import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../dashboard_controller.dart';

class ControlPanel extends GetView<DashboardController> {
  const ControlPanel({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.settings, color: Colors.blue),
                const SizedBox(width: 8),
                Text(
                  'Cấu hình & Test',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const Divider(height: 24),
            
            // Test Detection Button
            const Text(
              'Test Detection',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
            ),
            const SizedBox(height: 8),
            Obx(() => SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: controller.isTestingDetection.value
                    ? null
                    : controller.triggerTestDetection,
                icon: controller.isTestingDetection.value
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.play_arrow),
                label: Text(controller.isTestingDetection.value
                    ? 'Đang detect...'
                    : 'Chạy Detection Test'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            )),
            const SizedBox(height: 16),
            
            // Serial Port Selector
            const Text(
              'Serial Port (Arduino)',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
            ),
            const SizedBox(height: 8),
            Obx(() {
              final ports = controller.availablePorts;
              final currentPort = controller.selectedPort.value;
              
              if (ports.isEmpty) {
                return Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.orange.shade200),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.warning, color: Colors.orange, size: 20),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Không tìm thấy port. Kết nối Arduino và nhấn Refresh.',
                          style: TextStyle(fontSize: 12),
                        ),
                      ),
                    ],
                  ),
                );
              }
              
              return DropdownButtonFormField<String>(
                value: ports.contains(currentPort) ? currentPort : null,
                decoration: InputDecoration(
                  border: const OutlineInputBorder(),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.refresh, size: 20),
                    onPressed: controller.refreshAvailablePorts,
                    tooltip: 'Refresh ports',
                  ),
                ),
                items: ports.map((port) {
                  return DropdownMenuItem(
                    value: port,
                    child: Text(port, style: const TextStyle(fontSize: 14)),
                  );
                }).toList(),
                onChanged: (value) {
                  if (value != null) {
                    controller.selectPort(value);
                  }
                },
              );
            }),
            const SizedBox(height: 16),
            
            // Camera Selector
            const Text(
              'Camera Index',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
            ),
            const SizedBox(height: 8),
            Obx(() => Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<int>(
                    value: controller.selectedCameraIndex.value,
                    decoration: const InputDecoration(
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    items: [0, 1, 2, 4].map((index) {
                      return DropdownMenuItem(
                        value: index,
                        child: Text('Camera $index', style: const TextStyle(fontSize: 14)),
                      );
                    }).toList(),
                    onChanged: (value) {
                      if (value != null) {
                        controller.switchCamera(value);
                      }
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Obx(() => Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: controller.isCameraOpened.value
                        ? Colors.green.shade50
                        : Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: controller.isCameraOpened.value
                          ? Colors.green
                          : Colors.red,
                    ),
                  ),
                  child: Icon(
                    controller.isCameraOpened.value
                        ? Icons.videocam
                        : Icons.videocam_off,
                    color: controller.isCameraOpened.value
                        ? Colors.green
                        : Colors.red,
                    size: 20,
                  ),
                )),
              ],
            )),
            
            const SizedBox(height: 16),
            
            // Status info
            Obx(() {
              final status = controller.lineStatus.value;
              if (status == null) return const SizedBox.shrink();
              
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          status['connected'] == true
                              ? Icons.check_circle
                              : Icons.cancel,
                          color: status['connected'] == true
                              ? Colors.green
                              : Colors.red,
                          size: 16,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          status['connected'] == true
                              ? 'Serial: Connected'
                              : 'Serial: Disconnected',
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'OK: ${status['okCount'] ?? 0} | NG: ${status['ngCount'] ?? 0}',
                      style: const TextStyle(fontSize: 12),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}
