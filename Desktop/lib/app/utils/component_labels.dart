/// Mapping các label linh kiện từ backend sang tiếng Việt
class ComponentLabels {
  static const Map<String, String> _labelMap = {
    'CAP_INPUT': 'Tụ hóa đầu vào',
    'CAP_OUTPUT': 'Tụ hóa đầu ra',
    'LM2596_CHIP': 'Chip LM2596',
    'TRIMPOT': 'Biến trở xanh',
    'INDUCTOR_470': 'Cuộn cảm 470µH',

    // New YOLO canonical labels
    'Cuon cam': 'Cuộn cảm',
    'Tu ra': 'Tụ đầu ra',
    'Bien tro': 'Biến trở',
    'Diode': 'Diode',
    'LM2596': 'LM2596',
  };

  /// Chuyển đổi label từ backend sang tiếng Việt
  /// Trả về label gốc nếu không tìm thấy trong map
  static String toVietnamese(String label) {
    return _labelMap[label] ?? label;
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
