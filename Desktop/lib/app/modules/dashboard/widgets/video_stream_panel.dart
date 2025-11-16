import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:get/get.dart';

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
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: AspectRatio(
                aspectRatio: 16 / 9,
                child: Obx(() {
                  final Uint8List? bytes = controller.liveFrame.value;
                  if (!controller.liveEnabled.value) {
                    return _buildOverlay(context, 'Stream tạm dừng');
                  }
                  if (bytes == null) {
                    return _buildOverlay(context, 'Đang chờ camera...');
                  }
                  return Image.memory(
                    bytes,
                    gaplessPlayback: true,
                    fit: BoxFit.cover,
                  );
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
