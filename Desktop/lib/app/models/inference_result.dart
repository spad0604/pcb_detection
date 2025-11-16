class MissingArea {
  MissingArea({
    required this.id,
    required this.description,
    required this.confidence,
  });

  final String id;
  final String description;
  final double confidence;

  factory MissingArea.fromJson(Map<String, dynamic> json) => MissingArea(
        id: json['id'] as String? ?? 'unknown',
        description: json['description'] as String? ?? 'Unknown region',
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      );
}

class InferenceResult {
  InferenceResult({
    required this.isDefective,
    required this.confidence,
    required this.timestamp,
    this.missingAreas = const [],
    this.notes,
  });

  final bool isDefective;
  final double confidence;
  final DateTime timestamp;
  final List<MissingArea> missingAreas;
  final String? notes;

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
      );
}
