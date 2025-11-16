import 'dart:math';

import 'package:intl/intl.dart';

class DatasetSample {
  DatasetSample({
    required this.id,
    required this.name,
    required this.label,
    required this.sizeBytes,
    required this.createdAt,
    this.localPath,
  });

  final String id;
  final String name;
  final String label;
  final int sizeBytes;
  final DateTime createdAt;
  final String? localPath;

  factory DatasetSample.fromJson(Map<String, dynamic> json) => DatasetSample(
        id: json['id'] as String? ?? _randomId(),
        name: json['name'] as String? ?? 'sample',
        label: json['label'] as String? ?? 'missing',
        sizeBytes: json['sizeBytes'] as int? ?? 0,
        createdAt: DateTime.tryParse(json['createdAt'] as String? ?? '') ??
            DateTime.now(),
        localPath: json['localPath'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'label': label,
        'sizeBytes': sizeBytes,
        'createdAt': createdAt.toIso8601String(),
        'localPath': localPath,
      };

  String get formattedSize {
    if (sizeBytes <= 0) return '—';
    const units = ['B', 'KB', 'MB', 'GB'];
    var size = sizeBytes.toDouble();
    var unitIdx = 0;
    while (size >= 1024 && unitIdx < units.length - 1) {
      size /= 1024;
      unitIdx++;
    }
    return '${size.toStringAsFixed(1)} ${units[unitIdx]}';
  }

  String get formattedDate => DateFormat('dd/MM HH:mm').format(createdAt);

  static String _randomId() =>
      List<int>.generate(8, (_) => Random().nextInt(36))
          .map((i) => i.toRadixString(36))
          .join();
}
