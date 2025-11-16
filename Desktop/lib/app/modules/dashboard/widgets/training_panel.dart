import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../models/training_job.dart';
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
        child: Obx(() {
          final status = controller.trainingStatus.value;
          final isRunning = status.state == TrainingState.running;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('Training',
                      style:
                          TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
                  const Spacer(),
                  FilledButton.icon(
                    onPressed: controller.startTraining,
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text('Train ngay'),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Số epoch'),
                        const SizedBox(height: 6),
                        _EpochSelector(controller: controller),
                      ],
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Tỉ lệ test set'),
                        const SizedBox(height: 6),
                        _SplitSlider(controller: controller),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Text(
                'Trạng thái: ${_statusLabel(status.state)}',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: isRunning ? status.progress.clamp(0, 1) : null,
                  minHeight: 10,
                ),
              ),
              if (status.message != null) ...[
                const SizedBox(height: 8),
                Text(status.message!, style: const TextStyle(color: Colors.black54)),
              ],
              if (status.metrics != null) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  children: status.metrics!.entries
                      .map((metric) => Chip(
                            label: Text('${metric.key}: ${metric.value}'),
                          ))
                      .toList(),
                ),
              ],
            ],
          );
        }),
      ),
    );
  }
}

class _EpochSelector extends StatelessWidget {
  const _EpochSelector({required this.controller});

  final DashboardController controller;

  @override
  Widget build(BuildContext context) {
    return Obx(() => Row(
          children: [
            IconButton(
              onPressed: () =>
                  controller.updateEpochs(controller.epochs.value - 1),
              icon: const Icon(Icons.remove_circle_outline),
            ),
            Expanded(
              child: Text(
                controller.epochs.value.toString(),
                textAlign: TextAlign.center,
                style:
                    const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ),
            IconButton(
              onPressed: () =>
                  controller.updateEpochs(controller.epochs.value + 1),
              icon: const Icon(Icons.add_circle_outline),
            ),
          ],
        ));
  }
}

class _SplitSlider extends StatelessWidget {
  const _SplitSlider({required this.controller});

  final DashboardController controller;

  @override
  Widget build(BuildContext context) {
    return Obx(() => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Slider(
              value: controller.testSplit.value,
              onChanged: controller.updateTestSplit,
              divisions: 8,
              min: 0.1,
              max: 0.4,
            ),
            Text('Test ${(controller.testSplit.value * 100).round()}%'),
          ],
        ));
  }
}

String _statusLabel(TrainingState state) {
  switch (state) {
    case TrainingState.running:
      return 'Đang train';
    case TrainingState.succeeded:
      return 'Hoàn tất';
    case TrainingState.failed:
      return 'Thất bại';
    default:
      return 'Chưa chạy';
  }
}
