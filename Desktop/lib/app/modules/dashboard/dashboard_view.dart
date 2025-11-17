import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../models/training_job.dart';
import 'dashboard_controller.dart';
import 'widgets/activity_log_panel.dart';
import 'widgets/dataset_panel.dart';
import 'widgets/training_panel.dart';
import 'widgets/video_stream_panel.dart';

class DashboardView extends GetView<DashboardController> {
  const DashboardView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PCB Missing Component Inspector'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Đồng bộ dataset',
            onPressed: controller.fetchDataset,
          ),
        ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final isCompact = constraints.maxWidth < 1200;
          final padding = EdgeInsets.symmetric(
            horizontal: isCompact ? 16 : 24,
            vertical: 16,
          );
          final content = isCompact
              ? SingleChildScrollView(
                  padding: padding,
                  child: Column(
                    children: [
                      DatasetPanel(controller: controller),
                      const SizedBox(height: 16),
                      TrainingPanel(controller: controller),
                      const SizedBox(height: 16),
                      VideoStreamPanel(controller: controller),
                      const SizedBox(height: 16),
                      ActivityLogPanel(controller: controller),
                    ],
                  ),
                )
              : Padding(
                  padding: padding,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        flex: 3,
                        child: SingleChildScrollView(
                          child: Column(
                            children: [
                              DatasetPanel(controller: controller),
                              const SizedBox(height: 16),
                              TrainingPanel(controller: controller),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 24),
                      Expanded(
                        flex: 2,
                        child: SingleChildScrollView(
                          child: Column(
                            children: [
                              VideoStreamPanel(controller: controller),
                              const SizedBox(height: 16),
                              ActivityLogPanel(controller: controller),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                );
          return Container(color: const Color(0xfff7f9fc), child: content);
        },
      ),
      floatingActionButton: Obx(() {
        if (controller.trainingStatus.value.state == TrainingState.running) {
          return FloatingActionButton.extended(
            onPressed: null,
            backgroundColor: Colors.orange,
            label: Row(
              children: [
                const SizedBox(
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                ),
                const SizedBox(width: 12),
                const Text('Đang train...'),
              ],
            ),
          );
        }
        return FloatingActionButton.extended(
          onPressed: controller.startTraining,
          icon: const Icon(Icons.play_arrow_rounded),
          label: const Text('Train model'),
        );
      }),
    );
  }
}
