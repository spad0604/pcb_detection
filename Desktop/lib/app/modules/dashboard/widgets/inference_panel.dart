import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

import '../../../models/inference_result.dart';
import '../../../utils/component_labels.dart';
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
                const Icon(Icons.analytics_rounded, size: 24),
                const SizedBox(width: 8),
                const Text('Kiểm tra PCB (Upload ảnh)',
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
                          : const Icon(Icons.upload_file),
                      label: const Text('Upload & Kiểm tra'),
                    )),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Upload ảnh PCB để kiểm tra xem có thiếu linh kiện không',
              style: TextStyle(color: Colors.black54, fontSize: 13),
            ),
            const SizedBox(height: 16),
            Obx(() {
              final result = controller.lastInference.value;
              final imagePath = controller.lastInferenceImagePath.value;
              
              if (result == null) {
                return const _EmptyState();
              }
              
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Prefer Cloudinary URL when available
                  if (result.annotatedImageUrl != null &&
                      result.annotatedImageUrl!.isNotEmpty) ...[
                    _AnnotatedImage(imageUrl: result.annotatedImageUrl!),
                    const SizedBox(height: 16),
                  ] else if (result.hasAnnotatedImage == true) ...[
                    _AnnotatedImageFromEndpoint(
                      timestamp: result.timestamp.millisecondsSinceEpoch,
                    ),
                    const SizedBox(height: 16),
                  ] else if (imagePath != null) ...[
                    _ImageWithBoundingBoxes(
                      imagePath: imagePath,
                      result: result,
                    ),
                    const SizedBox(height: 16),
                  ],
                  _InferenceSummary(result: result),
                ],
              );
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
      padding: const EdgeInsets.symmetric(vertical: 40),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: const Color(0xfff2f4f8),
        border: Border.all(color: Colors.black12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: const [
          Icon(Icons.cloud_upload_rounded, size: 56, color: Colors.black38),
          SizedBox(height: 16),
          Text('Chưa có kết quả kiểm tra',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          SizedBox(height: 8),
          Text('Bấm "Upload & Kiểm tra" để chọn ảnh PCB',
              style: TextStyle(color: Colors.black54)),
          SizedBox(height: 4),
          Text('Hệ thống sẽ phân tích và báo cáo kết quả',
              style: TextStyle(color: Colors.black54, fontSize: 12)),
        ],
      ),
    );
  }
}

class _ImageWithBoundingBoxes extends StatelessWidget {
  const _ImageWithBoundingBoxes({
    required this.imagePath,
    required this.result,
  });

  final String imagePath;
  final InferenceResult result;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Container(
        constraints: const BoxConstraints(maxHeight: 400), // Giới hạn chiều cao
        child: FutureBuilder<ImageInfo>(
          future: _getImageInfo(),
          builder: (context, snapshot) {
            if (!snapshot.hasData) {
              return Container(
                height: 200,
                color: Colors.black12,
                child: const Center(child: CircularProgressIndicator()),
              );
            }

            final imageInfo = snapshot.data!;
            final imageWidth = imageInfo.image.width.toDouble();
            final imageHeight = imageInfo.image.height.toDouble();
            final aspectRatio = imageWidth / imageHeight;

            return AspectRatio(
              aspectRatio: aspectRatio,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  // Ảnh gốc
                  Image.file(
                    File(imagePath),
                    fit: BoxFit.contain,
                  ),
                  // Vẽ bounding boxes
                  CustomPaint(
                    painter: _BoundingBoxPainter(
                      missingAreas: result.missingAreas,
                      imageWidth: imageWidth,
                      imageHeight: imageHeight,
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Future<ImageInfo> _getImageInfo() async {
    final image = FileImage(File(imagePath));
    final completer = Completer<ImageInfo>();
    final stream = image.resolve(const ImageConfiguration());
    stream.addListener(ImageStreamListener((info, _) {
      completer.complete(info);
    }));
    return completer.future;
  }
}

class _BoundingBoxPainter extends CustomPainter {
  _BoundingBoxPainter({
    required this.missingAreas,
    required this.imageWidth,
    required this.imageHeight,
  });

  final List<MissingArea> missingAreas;
  final double imageWidth;
  final double imageHeight;

  @override
  void paint(Canvas canvas, Size size) {
    if (missingAreas.isEmpty) return;

    // Tính toán scale và offset để match với BoxFit.contain
    final imageAspect = imageWidth / imageHeight;
    final canvasAspect = size.width / size.height;
    
    double scale;
    double offsetX = 0;
    double offsetY = 0;
    
    if (canvasAspect > imageAspect) {
      // Canvas rộng hơn -> ảnh fit theo chiều cao
      scale = size.height / imageHeight;
      offsetX = (size.width - imageWidth * scale) / 2;
    } else {
      // Canvas cao hơn -> ảnh fit theo chiều rộng
      scale = size.width / imageWidth;
      offsetY = (size.height - imageHeight * scale) / 2;
    }
    
    for (var area in missingAreas) {
      if (area.bbox == null) continue;

      final bbox = area.bbox!;

      // Chuyển bbox chuẩn hoá (0-1) về toạ độ ảnh gốc, sau đó nhân scale
      final left = (bbox.x * imageWidth) * scale + offsetX;
      final top = (bbox.y * imageHeight) * scale + offsetY;
      final right = ((bbox.x + bbox.width) * imageWidth) * scale + offsetX;
      final bottom = ((bbox.y + bbox.height) * imageHeight) * scale + offsetY;
      
      final rect = Rect.fromLTRB(left, top, right, bottom);
      
      // Vẽ background mờ màu đỏ
      final bgPaint = Paint()
        ..color = Colors.red.withOpacity(0.25)
        ..style = PaintingStyle.fill;
      canvas.drawRect(rect, bgPaint);

      // Vẽ border màu đỏ đậm
      final borderPaint = Paint()
        ..color = Colors.red
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.0;
      canvas.drawRect(rect, borderPaint);

      // Vẽ label
      final textSpan = TextSpan(
        text: '${ComponentLabels.toVietnamese(area.description)} (${(area.confidence * 100).toStringAsFixed(0)}%)',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.bold,
          backgroundColor: Colors.red,
        ),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: ui.TextDirection.ltr,
      );
      textPainter.layout();
      
      // Vẽ background cho text
      final labelRect = Rect.fromLTWH(
        rect.left,
        rect.top - 20,
        textPainter.width + 8,
        20,
      );
      canvas.drawRect(labelRect, Paint()..color = Colors.red);
      
      textPainter.paint(
        canvas,
        Offset(rect.left + 4, rect.top - 18),
      );
    }
  }

  @override
  bool shouldRepaint(_BoundingBoxPainter oldDelegate) => true;
}

class _InferenceSummary extends StatelessWidget {
  const _InferenceSummary({required this.result});

  final InferenceResult result;

  @override
  Widget build(BuildContext context) {
    final verdictColor = result.isDefective ? Colors.red : Colors.green;
    final missingLabels = result.missingComponentLabels;
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
        if (result.isDefective && missingLabels.isNotEmpty) ...[
          const Text('Linh kiện đang thiếu:',
              style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: missingLabels
                .map((label) => Chip(
                      label: Text(ComponentLabels.toVietnamese(label)),
                      backgroundColor: Colors.red.shade50,
                    ))
                .toList(),
          ),
          const SizedBox(height: 12),
        ],
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
                          '${ComponentLabels.toVietnamese(area.description)} (${(area.confidence * 100).toStringAsFixed(0)}%)'),
                      backgroundColor: Colors.orange.shade50,
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
class _AnnotatedImageFromEndpoint extends GetView<DashboardController> {
  const _AnnotatedImageFromEndpoint({required this.timestamp});

  final int timestamp;

  @override
  Widget build(BuildContext context) {
    final baseUrl = controller.apiService.baseUrl;
    // Dùng timestamp từ result thay vì DateTime.now() để tránh nháy
    final imageUrl = '$baseUrl/api/stream/annotated?t=$timestamp';
    
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Container(
        constraints: const BoxConstraints(maxHeight: 600),
        color: Colors.black12,
        child: Image.network(
          imageUrl,
          key: ValueKey(timestamp), // Key để Flutter biết khi nào cần rebuild
          fit: BoxFit.contain,
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return const Center(child: CircularProgressIndicator());
          },
          errorBuilder: (context, error, stackTrace) {
            return Container(
              height: 200,
              color: Colors.red.shade100,
              child: Center(
                child: Text('Lỗi hiển thị ảnh: $error'),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _AnnotatedImage extends StatelessWidget {
  const _AnnotatedImage({required this.imageUrl});

  final String imageUrl;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Container(
        constraints: const BoxConstraints(maxHeight: 600),
        color: Colors.black12,
        child: Image.network(
          imageUrl,
          fit: BoxFit.contain,
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return Center(
              child: CircularProgressIndicator(
                value: loadingProgress.expectedTotalBytes != null
                    ? loadingProgress.cumulativeBytesLoaded /
                        loadingProgress.expectedTotalBytes!
                    : null,
              ),
            );
          },
          errorBuilder: (context, error, stackTrace) {
            return Container(
              height: 200,
              color: Colors.red.shade100,
              child: Center(
                child: Text('Lỗi hiển thị ảnh: $error'),
              ),
            );
          },
        ),
      ),
    );
  }
}