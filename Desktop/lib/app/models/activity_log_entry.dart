import 'package:intl/intl.dart';

class ActivityLogEntry {
  ActivityLogEntry({
    required this.level,
    required this.message,
    required this.timestamp,
  });

  final ActivityLogLevel level;
  final String message;
  final DateTime timestamp;

  String get formattedTime => DateFormat('HH:mm:ss').format(timestamp);
}

enum ActivityLogLevel { info, success, warning, error }
