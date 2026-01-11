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
              
              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  childAspectRatio: 3.5,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                ),
                itemCount: allComponents.length,
                itemBuilder: (context, index) {
                  final componentKey = allComponents[index];
                  final isPresent = componentStatus[componentKey] ?? false;
                  final componentName = ComponentLabels.toVietnamese(componentKey);
                  final componentIcon = ComponentLabels.getIcon(componentKey);
                  final componentColor = ComponentLabels.getColor(componentKey);
                  final imagePath = ComponentLabels.getImagePath(componentKey);
                  final hasImage = ComponentLabels.hasImage(componentKey);
                  
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade50,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: Colors.grey.shade200,
                        width: 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        // Ảnh hoặc Icon linh kiện
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: hasImage ? Colors.white : componentColor.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: componentColor.withOpacity(0.3),
                              width: 1,
                            ),
                          ),
                          child: hasImage
                              ? ClipRRect(
                                  borderRadius: BorderRadius.circular(5),
                                  child: Image.asset(
                                    imagePath!,
                                    fit: BoxFit.cover,
                                    errorBuilder: (context, error, stackTrace) {
                                      return Icon(
                                        componentIcon,
                                        color: componentColor,
                                        size: 20,
                                      );
                                    },
                                  ),
                                )
                              : Icon(
                                  componentIcon,
                                  color: componentColor,
                                  size: 20,
                                ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            componentName,
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 4),
                        // Trạng thái đủ/thiếu
                        Icon(
                          isPresent ? Icons.check_circle : Icons.cancel,
                          color: isPresent ? Colors.green : Colors.red,
                          size: 22,
                        ),
                      ],
                    ),
                  );
                },
              );
            }),
          ],
        ),
      ),
    );
  }
}

