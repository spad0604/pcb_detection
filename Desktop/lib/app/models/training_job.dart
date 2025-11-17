enum TrainingState { idle, running, succeeded, failed }

class TrainingJobStatus {
  TrainingJobStatus({
    required this.state,
    this.progress = 0,
    this.message,
    this.boardName,
    this.metrics,
  });

  final TrainingState state;
  final double progress;
  final String? message;
  final String? boardName;
  final Map<String, dynamic>? metrics;

  factory TrainingJobStatus.fromJson(Map<String, dynamic> json) =>
      TrainingJobStatus(
        state: _stateFrom(apiValue: json['status'] as String?),
        progress: (json['progress'] as num?)?.toDouble() ?? 0,
        message: json['message'] as String?,
        boardName: json['boardName'] as String?,
        metrics: json['metrics'] as Map<String, dynamic>?,
      );

  TrainingJobStatus copyWith({
    TrainingState? state,
    double? progress,
    String? message,
    String? boardName,
    Map<String, dynamic>? metrics,
  }) =>
      TrainingJobStatus(
        state: state ?? this.state,
        progress: progress ?? this.progress,
        message: message ?? this.message,
        boardName: boardName ?? this.boardName,
        metrics: metrics ?? this.metrics,
      );

  static TrainingState _stateFrom({String? apiValue}) {
    switch (apiValue) {
      case 'running':
        return TrainingState.running;
      case 'succeeded':
      case 'done':
        return TrainingState.succeeded;
      case 'failed':
      case 'error':
        return TrainingState.failed;
      default:
        return TrainingState.idle;
    }
  }

  static TrainingJobStatus idle() =>
      TrainingJobStatus(state: TrainingState.idle, progress: 0);
}
