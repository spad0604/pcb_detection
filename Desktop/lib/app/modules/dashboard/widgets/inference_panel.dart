import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

import '../../../models/inference_result.dart';
import '../dashboard_controller.dart';

class InferencePanel extends StatelessWidget {
  const InferencePanel({super.key, required this.controller});

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
              children: [
                const Text('Inference',
                    style:
                        TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
                const Spacer(),
                Obx(() => FilledButton.icon(
                      onPressed: controller.isInferencing.value
                          ? null
                          : controller.runInference,
                      icon: controller.isInferencing.value
                          ? const SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.search_rounded),
                      label: const Text('Chọn ảnh kiểm tra'),
                    )),
              ],
            ),
            const SizedBox(height: 16),
            Obx(() {
              final result = controller.lastInference.value;
              if (result == null) {
                return const _EmptyState();
              }
              return _InferenceSummary(result: result);
            }),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 32),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: const Color(0xfff2f4f8),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: const [
          Icon(Icons.image_search, size: 48, color: Colors.black38),
          SizedBox(height: 12),
          Text('Chưa có kết quả nào'),
          Text('Chọn ảnh PCB để kiểm tra thiếu linh kiện.'),
        ],
      ),
    );
  }
}

class _InferenceSummary extends StatelessWidget {
  const _InferenceSummary({required this.result});

  final InferenceResult result;

  @override
  Widget build(BuildContext context) {
    final verdictColor = result.isDefective ? Colors.red : Colors.green;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: verdictColor.withOpacity(0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                result.isDefective ? 'PCB THIẾU LINH KIỆN' : 'PCB OK',
                style: TextStyle(
                  color: verdictColor,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Text('Confidence ${(result.confidence * 100).toStringAsFixed(1)}%'),
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (result.missingAreas.isEmpty)
          const Text('Không phát hiện khu vực thiếu linh kiện.')
        else ...[
          const Text('Vùng nghi ngờ:',
              style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: result.missingAreas
                .map((area) => Chip(
                      label: Text(
                          '${area.description} (${(area.confidence * 100).toStringAsFixed(0)}%)'),
                    ))
                .toList(),
          ),
        ],
        const SizedBox(height: 12),
        Text("Thời gian: ${DateFormat('dd/MM HH:mm').format(result.timestamp)}"),
        if (result.notes != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(result.notes!),
          ),
      ],
    );
  }
}
