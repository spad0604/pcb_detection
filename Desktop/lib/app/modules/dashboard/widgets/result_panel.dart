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
        child: Obx(() {
          final analysis = controller.currentAnalysis;
          final shouldShow = controller.showComponentList.value && analysis != null;

          String withCacheBuster(String url, int ts) {
            final separator = url.contains('?') ? '&' : '?';
            return '$url${separator}t=$ts';
          }

          String resolveAnnotatedUrl() {
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

            final hasResult = shouldShow;
          final isDefective = analysis?.isDefective ?? false;
          final verdictText = !hasResult
              ? ''
              : (isDefective ? 'Mạch thiếu linh kiện' : 'Đầy đủ linh kiện');
          final verdictColor = !hasResult
              ? Colors.black54
              : (isDefective ? Colors.red : Colors.green);

            final timestamp = analysis?.timestamp.millisecondsSinceEpoch ??
              DateTime.now().millisecondsSinceEpoch;
            final annotatedUrl = withCacheBuster(resolveAnnotatedUrl(), timestamp);

            final missingCount = analysis?.missingComponentLabels.length ?? 0;
            final hasImage = analysis?.hasAnnotatedImage == true;

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.assessment,
                    size: 24,
                    color: hasResult ? verdictColor : null,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    verdictText.isEmpty ? 'Kết quả:' : 'Kết quả: $verdictText',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      color: verdictColor,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (!hasResult)
                Expanded(
                  child: Container(
                    width: double.infinity,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.hourglass_empty,
                            size: 42, color: Colors.grey),
                        SizedBox(height: 10),
                        Text(
                          'Đang chờ kết quả...',
                          style: TextStyle(
                            fontSize: 15,
                            color: Colors.grey,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              else ...[
                if (missingCount > 0) ...[
                  Text(
                    'Thiếu: $missingCount linh kiện',
                    style: const TextStyle(
                      fontSize: 13,
                      color: Colors.black54,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                if (hasImage)
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        width: double.infinity,
                        constraints: const BoxConstraints(maxHeight: 240),
                        color: Colors.grey.shade50,
                        child: Image.network(
                          annotatedUrl,
                          key: ValueKey(timestamp),
                          fit: BoxFit.contain,
                          gaplessPlayback: true,
                          filterQuality: FilterQuality.medium,
                          loadingBuilder: (context, child, loadingProgress) {
                            if (loadingProgress == null) return child;
                            return const Center(
                              child: CircularProgressIndicator(),
                            );
                          },
                          errorBuilder: (context, error, stackTrace) {
                            return Container(
                              color: Colors.grey.shade200,
                              alignment: Alignment.center,
                              child: const Text('Không tải được ảnh'),
                            );
                          },
                        ),
                      ),
                    ),
                  )
                else
                  Expanded(
                    child: Container(
                      width: double.infinity,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Text(
                        'Chưa có ảnh từ server',
                        style: TextStyle(color: Colors.black45),
                      ),
                    ),
                  ),
              ],
            ],
          );
        }),
      ),
    );
  }
}