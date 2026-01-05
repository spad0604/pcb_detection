import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../utils/component_labels.dart';
import '../dashboard_controller.dart';

class ComponentListPanel extends StatelessWidget {
  const ComponentListPanel({super.key, required this.controller});

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
                Icon(Icons.list_alt, size: 24),
                SizedBox(width: 8),
                Text(
                  'Danh sách Linh kiện',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Obx(() {
              final analysis = controller.liveAnalysis.value;
              
              // Lấy danh sách tất cả linh kiện
              final allComponents = ComponentLabels.getAllOriginalLabels();
              final missingComponents = analysis?.missingComponentLabels ?? [];
              
              // Xác định linh kiện nào đủ, linh kiện nào thiếu
              final componentStatus = <String, bool>{};
              for (final component in allComponents) {
                componentStatus[component] = !missingComponents.contains(component);
              }
              
              return Column(
                children: allComponents.map((componentKey) {
                  final isPresent = componentStatus[componentKey] ?? false;
                  final componentName = ComponentLabels.toVietnamese(componentKey);
                  
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Row(
                      children: [
                        Icon(
                          isPresent ? Icons.check_circle : Icons.cancel,
                          color: isPresent ? Colors.green : Colors.red,
                          size: 28,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            componentName,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              );
            }),
          ],
        ),
      ),
    );
  }
}

