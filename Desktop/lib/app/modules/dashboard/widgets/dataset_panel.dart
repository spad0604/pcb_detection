import 'package:collection/collection.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../models/dataset_sample.dart';
import '../dashboard_controller.dart';
import 'stat_card.dart';

class DatasetPanel extends StatelessWidget {
  const DatasetPanel({super.key, required this.controller});

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
            LayoutBuilder(builder: (context, constraints) {
              final stacked = constraints.maxWidth < 700;
              final labelSelector = Obx(() => Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: ['ok', 'missing'].map((label) {
                      return ChoiceChip(
                        label: Text(
                            label == 'ok' ? 'Đủ linh kiện' : 'Thiếu linh kiện'),
                        selected: controller.activeLabel.value == label,
                        onSelected: (_) => controller.changeLabel(label),
                      );
                    }).toList(),
                  ));
              final uploadButton = Obx(() => ElevatedButton.icon(
                    onPressed: controller.isUploading.value
                        ? null
                        : controller.addSamples,
                    icon: controller.isUploading.value
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.upload_file),
                    label: const Text('Thêm ảnh'),
                  ));

              if (stacked) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Dataset',
                      style:
                          TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 12),
                    labelSelector,
                    const SizedBox(height: 12),
                    Align(alignment: Alignment.centerLeft, child: uploadButton),
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const Text(
                    'Dataset',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(width: 24),
                  Expanded(
                    child: Align(
                      alignment: Alignment.centerRight,
                      child: labelSelector,
                    ),
                  ),
                  const SizedBox(width: 12),
                  uploadButton,
                ],
              );
            }),
            const SizedBox(height: 16),
            Obx(() {
              final total = controller.dataset.length;
              final missing =
                  controller.dataset.where((s) => s.label == 'missing').length;
              final ok = total - missing;
              return LayoutBuilder(builder: (context, constraints) {
                final vertical = constraints.maxWidth < 600;
                final cards = [
                  StatCard(
                    icon: Icons.storage_rounded,
                    title: 'Tổng mẫu',
                    value: total.toString(),
                    subtitle: 'Ảnh đang theo dõi',
                  ),
                  StatCard(
                    icon: Icons.check_circle_outline,
                    title: 'OK',
                    value: ok.toString(),
                    color: Colors.green,
                  ),
                  StatCard(
                    icon: Icons.error_outline,
                    title: 'Thiếu linh kiện',
                    value: missing.toString(),
                    color: Colors.red,
                  ),
                ];
                return Flex(
                  direction: vertical ? Axis.vertical : Axis.horizontal,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: cards
                      .map((c) => Expanded(
                            child: Padding(
                              padding: EdgeInsets.only(
                                right: vertical ? 0 : 12,
                                bottom: vertical ? 12 : 0,
                              ),
                              child: c,
                            ),
                          ))
                      .toList(),
                );
              });
            }),
            const SizedBox(height: 24),
            const Text('Mẫu gần nhất',
                style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),
            Obx(() {
              if (controller.dataset.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 32),
                  child: Center(child: Text('Chưa có dữ liệu nào.')),
                );
              }
                final rows = controller.dataset
                  .toList()
                  .sortedBy((sample) => sample.createdAt)
                  .reversed
                  .take(6)
                  .toList();
              return ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Table(
                  columnWidths: const {
                    0: FlexColumnWidth(3),
                    1: FlexColumnWidth(2),
                    2: FlexColumnWidth(1.5),
                    3: FlexColumnWidth(1.5),
                  },
                  defaultVerticalAlignment: TableCellVerticalAlignment.middle,
                  children: [
                    const TableRow(
                      decoration: BoxDecoration(color: Color(0xfff2f4f8)),
                      children: [
                        Padding(
                          padding: EdgeInsets.all(12),
                          child: Text('Tên file',
                              style: TextStyle(fontWeight: FontWeight.w600)),
                        ),
                        Padding(
                          padding: EdgeInsets.all(12),
                          child: Text('Label',
                              style: TextStyle(fontWeight: FontWeight.w600)),
                        ),
                        Padding(
                          padding: EdgeInsets.all(12),
                          child: Text('Kích thước',
                              style: TextStyle(fontWeight: FontWeight.w600)),
                        ),
                        Padding(
                          padding: EdgeInsets.all(12),
                          child: Text('Thời gian',
                              style: TextStyle(fontWeight: FontWeight.w600)),
                        ),
                      ],
                    ),
                    ...rows.map(_datasetRow),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}

TableRow _datasetRow(DatasetSample sample) {
  final labelColor = sample.label == 'missing' ? Colors.deepOrange : Colors.teal;
  return TableRow(
    decoration: const BoxDecoration(color: Colors.white),
    children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: Text(sample.name, overflow: TextOverflow.ellipsis),
      ),
      Padding(
        padding: const EdgeInsets.all(12),
        child: Chip(
          backgroundColor: labelColor.withOpacity(0.12),
          label: Text(
            sample.label,
            style: TextStyle(color: labelColor, fontWeight: FontWeight.w600),
          ),
        ),
      ),
      Padding(
        padding: const EdgeInsets.all(12),
        child: Text(sample.formattedSize),
      ),
      Padding(
        padding: const EdgeInsets.all(12),
        child: Text(sample.formattedDate),
      ),
    ],
  );
}
