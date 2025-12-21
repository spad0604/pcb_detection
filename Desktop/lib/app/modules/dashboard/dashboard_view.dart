import 'package:flutter/material.dart';
import 'package:get/get.dart';

import 'dashboard_controller.dart';
import 'widgets/activity_log_panel.dart';
import 'widgets/inference_panel.dart';
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
            tooltip: 'Làm mới camera',
            onPressed: controller.refreshLiveFrame,
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
                      VideoStreamPanel(controller: controller),
                      const SizedBox(height: 16),
                      InferencePanel(controller: controller),
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
                              VideoStreamPanel(controller: controller),
                              const SizedBox(height: 16),
                              InferencePanel(controller: controller),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 24),
                      Expanded(
                        flex: 2,
                        child: SingleChildScrollView(
                          child: ActivityLogPanel(controller: controller),
                        ),
                      ),
                    ],
                  ),
                );
          return Container(color: const Color(0xfff7f9fc), child: content);
        },
      ),
    );
  }
}
