import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../models/activity_log_entry.dart';
import '../dashboard_controller.dart';

class ActivityLogPanel extends StatelessWidget {
  const ActivityLogPanel({super.key, required this.controller});

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
            const Text('Activity log',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),
            Obx(() {
              final entries = controller.logs;
              if (entries.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: Text('Chưa có sự kiện nào.'),
                );
              }
              return SizedBox(
                height: 240,
                child: ListView.separated(
                  itemCount: entries.length,
                  separatorBuilder: (_, __) => const Divider(height: 16),
                  itemBuilder: (context, index) {
                    final entry = entries[index];
                    return _LogTile(entry: entry);
                  },
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _LogTile extends StatelessWidget {
  const _LogTile({required this.entry});

  final ActivityLogEntry entry;

  @override
  Widget build(BuildContext context) {
    final color = _colorFor(entry.level);
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(entry.message,
                  style: const TextStyle(fontWeight: FontWeight.w500)),
              Text(entry.formattedTime,
                  style: const TextStyle(fontSize: 12, color: Colors.black45)),
            ],
          ),
        ),
      ],
    );
  }
}

Color _colorFor(ActivityLogLevel level) {
  switch (level) {
    case ActivityLogLevel.success:
      return Colors.green;
    case ActivityLogLevel.warning:
      return Colors.orange;
    case ActivityLogLevel.error:
      return Colors.red;
    default:
      return Colors.blueGrey;
  }
}
