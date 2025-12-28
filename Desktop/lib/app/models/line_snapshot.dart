import 'inference_result.dart';

class LineSnapshot {
  const LineSnapshot({
    this.capturedAt,
    this.hasAnnotatedImage,
    this.inference,
  });

  final DateTime? capturedAt;
  final bool? hasAnnotatedImage;
  final InferenceResult? inference;

  factory LineSnapshot.fromJson(Map<String, dynamic> json) {
    final captured = json['capturedAt'] as String?;
    return LineSnapshot(
      capturedAt: captured == null ? null : DateTime.tryParse(captured),
      hasAnnotatedImage: json['hasAnnotatedImage'] as bool?,
      inference: json['inference'] == null
          ? null
          : InferenceResult.fromJson(
              json['inference'] as Map<String, dynamic>,
            ),
    );
  }
}
