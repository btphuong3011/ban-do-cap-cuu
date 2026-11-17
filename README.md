# Bản Đồ Cấp Cứu

Mô hình minh họa: bao nhiêu người dân Điện Biên tới được nơi mổ cấp cứu (mổ lấy thai) trong 2 giờ, theo ngưỡng của Ủy ban Phẫu thuật Toàn cầu (Lancet, 2015); đoạn đường nào xung yếu khi sạt lở mùa mưa; và nên ưu tiên giữ kíp mổ 24/7 ở đâu.

**Xem bản đồ:** https://btphuong3011.github.io/ban-do-cap-cuu/

## Cách tính

- **Đường:** đồ thị đường bộ Điện Biên từ OpenStreetMap (bản xuất của HOT trên HDX), tốc độ giả định theo loại đường: quốc lộ 40–45 km/h, tỉnh lộ 35, đường huyện cũ 28, đường xã 22, đường trong bản 15–18, đường đất 12 km/h.
- **Dân số:** Kontur Population 2023, ô lục giác khoảng 400 m (khoảng 702.000 người). Từ mỗi ô đi bộ ra đường gần nhất 4 km/h.
- **Thời gian:** thuật toán đường đi ngắn nhất (Dijkstra) tới cơ sở gần nhất đang bật năng lực mổ.
- **Ca sinh:** số người ngoài 2 giờ × tỷ suất sinh thô của Điện Biên 18,72‰ (Tổng cục Thống kê, Điều tra dân số giữa kỳ 2024).
- **Đoạn đường xung yếu:** thử cắt lần lượt 150 đoạn quốc lộ, tỉnh lộ, đường huyện có nhiều người đi qua nhất trên đường ngắn nhất, đo số dân bị đẩy ra ngoài 2 giờ.
- Năng lực mổ cấp cứu của từng cơ sở là **giả định** để minh họa; bấm vào cơ sở trên bản đồ để bật hoặc tắt.

Mã nguồn mô hình nằm trong thư mục `mo-hinh` của hồ sơ (Python: numpy, scipy).

Đây là công cụ hỗ trợ lập kế hoạch cho cơ quan y tế, không dùng để chỉ đường cấp cứu. Khi có cấp cứu, hãy gọi 115.

Dữ liệu bản đồ © những người đóng góp OpenStreetMap (ODbL); dân số © Kontur (CC BY 4.0).
