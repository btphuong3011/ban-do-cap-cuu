# Bản Đồ Cấp Cứu

Công cụ lập kế hoạch cấp cứu sản khoa cho vùng miền núi, thử nghiệm tại Điện Biên. Công cụ trả lời bốn câu hỏi: khu dân cư nào ở ngoài 2 giờ tới nơi mổ cấp cứu (ngưỡng của Ủy ban Phẫu thuật Toàn cầu, Lancet 2015), nên duy trì kíp mổ 24/7 ở đâu trước, đoạn đường nào xung yếu khi sạt lở mùa mưa, và mỗi khu cần chuẩn bị gì. Với câu hỏi cuối, công cụ in **phiếu kế hoạch sinh** cho trạm y tế xã và cô đỡ thôn bản.

**Xem bản đồ:** https://btphuong3011.github.io/ban-do-cap-cuu/

Đây là công cụ dùng **trước** khi có ca cấp cứu, không dùng để chỉ đường lúc đang cấp cứu. Khi có cấp cứu, hãy gọi 115 và làm theo phiếu kế hoạch sinh đã lập sẵn.

## Bốn bước trên trang

1. **Ai ở quá xa:** mỗi chấm tròn là một khu dân cư, to nhỏ theo số dân, tô màu theo thời gian tới nơi mổ lấy thai gần nhất (dưới 1 giờ, 1–2 giờ, trên 2 giờ).
2. **Kíp mổ ở đâu:** bật, tắt kíp mổ 24/7 ở từng trung tâm y tế; danh sách xếp theo số người được đưa vào ngưỡng 2 giờ.
3. **Mùa mưa:** chọn một trong 3 đoạn đường xung yếu nhất để xem khu nào bị cô lập thêm.
4. **Kế hoạch sinh:** danh sách khu dân cư ngoài 2 giờ, xếp theo số ca sinh ước tính mỗi năm; bấm một khu để xem và in phiếu (khổ A4).

## Phiếu kế hoạch sinh

Mỗi phiếu ghi:
- nơi mổ cấp cứu gần nhất trong phương án đang chọn;
- thời gian đi mùa khô, và mùa mưa khi đoạn đường xung yếu bị sạt lở;
- nơi dự phòng;
- sơ đồ tuyến đường;
- khuyến nghị lên nhà chờ sinh nếu khu dân cư ở ngoài 2 giờ;
- phần để cán bộ y tế điền cùng gia đình: ngày dự sinh, người đi cùng, phương tiện, người có thể hiến máu, giấy tờ;
- các dấu hiệu nguy hiểm cần đi ngay.

Thông tin cá nhân chỉ ghi tay trên giấy, không nhập vào công cụ. Danh sách dấu hiệu nguy hiểm dựa trên hướng dẫn chăm sóc thai sản của Tổ chức Y tế Thế giới và cần chuyên gia sản khoa thẩm định trước khi dùng thật.

## Cách tính

- **Đường:** đồ thị đường bộ Điện Biên lấy từ OpenStreetMap (bản xuất của HOT trên HDX). Tốc độ giả định theo loại đường:

  | Loại đường | Tốc độ |
  |---|---|
  | Quốc lộ | 40–45 km/h |
  | Đường tỉnh | 35 km/h |
  | Đường huyện cũ | 28 km/h |
  | Đường xã | 22 km/h |
  | Đường trong bản | 15–18 km/h |
  | Đường đất | 12 km/h |

- **Dân số:** Kontur Population 2023, chia ô lục giác khoảng 400 m, tổng khoảng 702.000 người. Từ mỗi ô đi bộ ra đường gần nhất với tốc độ 4 km/h.
- **Thời gian:** dùng thuật toán đường đi ngắn nhất (Dijkstra) để tính thời gian tới cơ sở gần nhất đang có năng lực mổ.
- **Khu dân cư:** gom các ô dân số thành 240 cụm (k-means), đặt tên theo địa danh gần nhất trên OpenStreetMap. Khi thí điểm, sẽ thay bằng danh sách bản của trạm y tế xã. Thời gian của mỗi khu là trung vị theo dân số. Tuyến đường trên phiếu tính từ ô đông dân nhất của khu.
- **Ca sinh:** số dân × tỷ suất sinh thô của Điện Biên 18,72‰ (Tổng cục Thống kê, Điều tra dân số giữa kỳ 2024).
- **Đoạn đường xung yếu:** thử cắt lần lượt 150 đoạn quốc lộ, đường tỉnh, đường huyện có nhiều người đi qua nhất trên đường ngắn nhất, rồi đo số dân bị đẩy ra ngoài 2 giờ.
- **Năng lực mổ:** năng lực mổ cấp cứu của từng cơ sở là **giả định** để so sánh phương án.

Mã nguồn mô hình nằm trong thư mục [`model`](model/) (Python: numpy, scipy, scikit-learn):
- `extract_roads_gpkg.py`: lấy đường từ bản xuất OpenStreetMap của HOT;
- `extract_pop.py`: lấy dân số Kontur;
- `build_model.py`: dựng đồ thị, tính thời gian và tìm đoạn đường xung yếu;
- `extract_places_hot.py` và `build_areas.py`: tạo khu dân cư và tuyến đường cho phiếu kế hoạch sinh.

Dữ liệu bản đồ © những người đóng góp OpenStreetMap (ODbL); dân số © Kontur (CC BY 4.0). Mọi con số là kết quả mô phỏng.
