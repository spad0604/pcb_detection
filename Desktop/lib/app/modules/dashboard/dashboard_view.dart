import 'package:flutter/material.dart';
import 'package:get/get.dart';

import 'dashboard_controller.dart';
import 'widgets/component_list_panel.dart';
import 'widgets/result_panel.dart';
import 'widgets/university_header.dart';
import 'widgets/video_stream_panel.dart';

class DashboardView extends GetView<DashboardController> {
  const DashboardView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          const UniversityHeader(),
          Expanded(
            child: LayoutBuilder(
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
                            ComponentListPanel(controller: controller),
                            const SizedBox(height: 16),
                            ResultPanel(controller: controller),
                          ],
                        ),
                      )
                    : Padding(
                        padding: padding,
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 2,
                              child: SingleChildScrollView(
                                child: Column(
                                  children: [
                                    VideoStreamPanel(controller: controller),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 24),
                            Expanded(
                              flex: 1,
                              child: SingleChildScrollView(
                                child: Column(
                                  children: [
                                    ComponentListPanel(controller: controller),
                                    const SizedBox(height: 16),
                                    ResultPanel(controller: controller),
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
          ),
        ],
      ),
    );
  }
}
