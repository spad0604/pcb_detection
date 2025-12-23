class BoundingBox {
  BoundingBox({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
  });

  final double x;
  final double y;
  final double width;
  final double height;

  factory BoundingBox.fromJson(Map<String, dynamic> json) => BoundingBox(
        x: (json['x'] as num?)?.toDouble() ?? 0,
        y: (json['y'] as num?)?.toDouble() ?? 0,
        width: (json['width'] as num?)?.toDouble() ?? 0,
        height: (json['height'] as num?)?.toDouble() ?? 0,
      );
}

class MissingArea {
  MissingArea({
    required this.id,
    required this.description,
    required this.confidence,
    this.bbox,
  });

  final String id;
  final String description;
  final double confidence;
  final BoundingBox? bbox;

  factory MissingArea.fromJson(Map<String, dynamic> json) => MissingArea(
        id: json['id'] as String? ?? 'unknown',
        description: json['description'] as String? ?? 'Unknown region',
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
        bbox: json['bbox'] == null
            ? null
            : BoundingBox.fromJson(json['bbox'] as Map<String, dynamic>),
      );
}

class InferenceResult {
  InferenceResult({
    required this.isDefective,
    required this.confidence,
    required this.timestamp,
    this.missingAreas = const [],
    this.notes,
    this.annotatedImageUrl,
  });

  final bool isDefective;
  final double confidence;
  final DateTime timestamp;
  final List<MissingArea> missingAreas;
  final String? notes;
  final String? annotatedImageUrl;

  factory InferenceResult.fromJson(Map<String, dynamic> json) =>
      InferenceResult(
        isDefective: json['isDefective'] as bool? ?? false,
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
        timestamp:
            DateTime.tryParse(json['timestamp'] as String? ?? '') ?? DateTime.now(),
        missingAreas: (json['missingAreas'] as List<dynamic>? ?? [])
            .map((e) => MissingArea.fromJson(e as Map<String, dynamic>))
            .toList(),
        notes: json['notes'] as String?,
        annotatedImageUrl: json['annotatedImageUrl'] as String?,
      );
}
