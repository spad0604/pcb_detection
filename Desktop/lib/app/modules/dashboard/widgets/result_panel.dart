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
              
              // Debug: In ra console để kiểm tra
              if (analysis != null) {
                print('🔍 DEBUG: hasAnnotatedImage = ${analysis.hasAnnotatedImage}');
                print('🔍 DEBUG: annotatedImageUrl = ${analysis.annotatedImageUrl}');
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

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (analysis.hasAnnotatedImage == true)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        constraints: const BoxConstraints(maxHeight: 400),
                        child: Image.network(
                          '${controller.apiService.baseUrl}/api/stream/annotated',
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
                  if (analysis.hasAnnotatedImage == true) 
                    const SizedBox(height: 16),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: color, width: 2),
                    ),
                    child: Column(
                      children: [
                        Icon(icon, size: 64, color: color),
                        const SizedBox(height: 16),
                        Text(
                          text,
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: color,
                          ),
                        ),
                        if (analysis.notes != null) ...[
                          const SizedBox(height: 12),
                          Text(
                            analysis.notes!,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey.shade700,
                            ),
                          ),
                        ],
                      ],
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