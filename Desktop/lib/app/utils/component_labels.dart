import 'package:flutter/material.dart';

/// Mapping các label linh kiện từ backend sang tiếng Việt
class ComponentLabels {
  static const Map<String, String> _labelMap = {
    'Tu vao': 'Tụ đầu vào',
    'Cuon cam': 'Cuộn cảm',
    'Tu ra': 'Tụ đầu ra',
    'Bien tro': 'Biến trở',
    'Diode': 'Diode',
    'LM2596': 'LM2596',
  };

  /// Icon cho từng loại linh kiện
  static const Map<String, IconData> _iconMap = {
    'Tu vao': Icons.battery_charging_full,
    'Cuon cam': Icons.all_inclusive,
    'Tu ra': Icons.battery_full,
    'Bien tro': Icons.tune,
    'Diode': Icons.arrow_forward,
    'LM2596': Icons.memory,
  };

  /// Màu cho từng loại linh kiện
  static const Map<String, Color> _colorMap = {
    'Tu vao': Color(0xFF2196F3),      // Xanh dương
    'Cuon cam': Color(0xFFFF9800),    // Cam
    'Tu ra': Color(0xFF4CAF50),       // Xanh lá
    'Bien tro': Color(0xFF9C27B0),    // Tím
    'Diode': Color(0xFFF44336),       // Đỏ
    'LM2596': Color(0xFF607D8B),      // Xám xanh
  };

  /// Đường dẫn ảnh cho từng loại linh kiện
  static const Map<String, String> _imageMap = {
    'Tu vao': 'assets/images/tu_vao.jpg',
    'Cuon cam': 'assets/images/cuon_cam.jpg',
    'Tu ra': 'assets/images/tu_ra.jpg',
    'Bien tro': 'assets/images/bien_tro.jpg',
    'LM2596': 'assets/images/lm2596.jpg',
    'Diode': 'assets/images/diode.png',
    // Diode chưa có ảnh, sẽ dùng icon fallback
  };

  /// Chuyển đổi label từ backend sang tiếng Việt
  /// Trả về label gốc nếu không tìm thấy trong map
  static String toVietnamese(String label) {
    return _labelMap[label] ?? label;
  }

  /// Lấy icon cho linh kiện
  static IconData getIcon(String label) {
    return _iconMap[label] ?? Icons.developer_board;
  }

  /// Lấy màu cho linh kiện
  static Color getColor(String label) {
    return _colorMap[label] ?? Colors.grey;
  }

  /// Lấy đường dẫn ảnh cho linh kiện (null nếu không có)
  static String? getImagePath(String label) {
    return _imageMap[label];
  }

  /// Kiểm tra xem linh kiện có ảnh không
  static bool hasImage(String label) {
    return _imageMap.containsKey(label);
  }

  /// Lấy tất cả labels tiếng Việt
  static List<String> getAllVietnameseLabels() {
    return _labelMap.values.toList();
  }

  /// Lấy tất cả labels gốc
  static List<String> getAllOriginalLabels() {
    return _labelMap.keys.toList();
  }
}
