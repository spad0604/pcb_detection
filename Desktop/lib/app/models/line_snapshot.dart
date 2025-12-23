import 'inference_result.dart';

class LineSnapshot {
  const LineSnapshot({
    this.capturedAt,
    this.annotatedImageUrl,
    this.inference,
  });

  final DateTime? capturedAt;
  final String? annotatedImageUrl;
  final InferenceResult? inference;

  factory LineSnapshot.fromJson(Map<String, dynamic> json) {
    final captured = json['capturedAt'] as String?;
    return LineSnapshot(
      capturedAt: captured == null ? null : DateTime.tryParse(captured),
      annotatedImageUrl: json['annotatedImageUrl'] as String?,
      inference: json['inference'] == null
          ? null
          : InferenceResult.fromJson(
              json['inference'] as Map<String, dynamic>,
            ),
    );
  }
}
