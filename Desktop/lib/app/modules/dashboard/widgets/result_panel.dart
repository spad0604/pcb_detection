import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../dashboard_controller.dart';

class ResultPanel extends StatelessWidget {
  const ResultPanel({super.key, required this.controller});

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
            const Row(
              children: [
                Icon(Icons.assessment, size: 24),
                SizedBox(width: 8),
                Text(
                  'Kết quả',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Obx(() {
              final analysis = controller.liveAnalysis.value;

              String _withCacheBuster(String url, int ts) {
                final separator = url.contains('?') ? '&' : '?';
                return '$url${separator}t=$ts';
              }

              String _resolveAnnotatedUrl() {
                final baseUrl = controller.apiService.baseUrl;
                final raw = analysis?.annotatedImageUrl;
                if (raw != null && raw.trim().isNotEmpty) {
                  if (raw.startsWith('http://') || raw.startsWith('https://')) {
                    return raw;
                  }
                  final path = raw.startsWith('/') ? raw : '/$raw';
                  return '$baseUrl$path';
                }
                return '$baseUrl/api/stream/annotated';
              }

              if (analysis == null) {
                return Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 32),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Column(
                    children: [
                      Icon(Icons.hourglass_empty, size: 48, color: Colors.grey),
                      SizedBox(height: 12),
                      Text(
                        'Đang chờ kết quả...',
                        style: TextStyle(
                          fontSize: 16,
                          color: Colors.grey,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                );
              }

              final isDefective = analysis.isDefective;
              final color = isDefective ? Colors.red : Colors.green;
              final icon = isDefective ? Icons.error : Icons.check_circle;
              final text = isDefective ? 'THIẾU LINH KIỆN' : 'ĐẦY ĐỦ';
              final timestamp = analysis.timestamp.millisecondsSinceEpoch;
              final annotatedUrl = _withCacheBuster(_resolveAnnotatedUrl(), timestamp);

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (analysis.hasAnnotatedImage == true)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        constraints: const BoxConstraints(maxHeight: 400),
                        child: Image.network(
                          annotatedUrl,
                          key: ValueKey(timestamp),
                          fit: BoxFit.contain,
                          gaplessPlayback: true,
                          filterQuality: FilterQuality.medium,
                          loadingBuilder: (context, child, loadingProgress) {
                            if (loadingProgress == null) return child;
                            return SizedBox(
                              height: 200,
                              child: Center(child: CircularProgressIndicator()),
                            );
                          },
                          errorBuilder: (context, error, stackTrace) {
                            return Container(
                              height: 200,
                              color: Colors.grey.shade200,
                              child: const Center(
                                child: Text('Không tải được ảnh'),
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                ],
              ); // Correctly ends the Column
            }), // Correctly ends the Obx
          ],
        ),
      ),
    );
  }
}