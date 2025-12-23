import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../models/inference_result.dart';
import '../dashboard_controller.dart';

class VideoStreamPanel extends StatelessWidget {
  const VideoStreamPanel({super.key, required this.controller});

  final DashboardController controller;

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.videocam_rounded),
                const SizedBox(width: 8),
                const Text(
                  'Live conveyor feed',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                Obx(() {
                  return Switch.adaptive(
                    value: controller.liveEnabled.value,
                    activeColor: Theme.of(context).colorScheme.primary,
                    onChanged: controller.toggleLiveStream,
                  );
                }),
                IconButton(
                  tooltip: 'Refresh frame',
                  onPressed: () => controller.refreshLiveFrame(),
                  icon: const Icon(Icons.refresh_rounded),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Obx(() {
              final analysis = controller.liveAnalysis.value;
                final statusText = analysis == null
                  ? 'Đang chờ camera...'
                  : analysis.isDefective
                    ? 'Phát hiện sai lệch'
                    : 'PCB ổn định';
              final badgeColor =
                  analysis == null ? Colors.grey : analysis.isDefective ? Colors.red : Colors.green;
              final note = analysis?.notes;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: badgeColor.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          analysis?.isDefective == true
                              ? Icons.error_rounded
                              : Icons.check_circle_rounded,
                          color: badgeColor,
                          size: 18,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          statusText,
                          style: TextStyle(
                            color: badgeColor,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (note != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      note,
                      style: const TextStyle(color: Colors.black54),
                    ),
                  ],
                ],
              );
            }),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: AspectRatio(
                aspectRatio: 16 / 9,
                child: Obx(() {
                  final Uint8List? bytes = controller.liveFrame.value;
                  if (!controller.liveEnabled.value) {
                    return _buildOverlay(context, 'Stream tạm dừng');
                  }
                  final analysis = controller.liveAnalysis.value;
                  if (bytes == null) {
                    return _buildOverlay(context, 'Đang chờ camera...');
                  }
                  return _VideoCanvas(frame: bytes, analysis: analysis);
                }),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOverlay(BuildContext context, String message) {
    return Container(
      color: Colors.black12,
      alignment: Alignment.center,
      child: Text(
        message,
        style: Theme.of(context)
            .textTheme
            .titleMedium
            ?.copyWith(color: Colors.black54),
      ),
    );
  }
}

class _VideoCanvas extends StatelessWidget {
  const _VideoCanvas({required this.frame, this.analysis});

  final Uint8List frame;
  final InferenceResult? analysis;

  @override
  Widget build(BuildContext context) {
    // Camera stream luôn hiển thị raw frame; boxes nằm ở panel kết quả riêng
    return Image.memory(
      frame,
      gaplessPlayback: true,
      fit: BoxFit.cover,
    );
  }
}
