# Vtracking Fleet + Logistics 0.2 — TrackVN + Map + GPS

Bản pilot có backend và giao diện tiếng Việt, bổ sung cho lõi GPS Traccar.
Long Ngo phát triển · Apache-2.0, giữ nguyên bản quyền Traccar trong repository.

## TrackVN, Map và GPS đồng bộ

Trang `/` và `/board` mở bảng theo dõi sau đăng nhập: danh sách đơn bên trái, bản đồ ở giữa,
chi tiết và các mốc bàn giao bên phải. Trên điện thoại, bản đồ và danh sách xếp dọc.

- Giao diện sáng/tối, tra cứu nhiều mã, lọc trạng thái và hãng, logo từ bộ TrackVN đính kèm.
- Lưu nhãn hãng `local/ghn/jt/spx/vnpost/futa/lex` và mã vận đơn ngoài trên mỗi kiện.
- Tra cứu một hoặc nhiều mã đã đăng ký trong tài khoản; không báo là có dữ liệu hãng khi chưa kết nối.
- Bản đồ Leaflet đóng gói trong repository, ô bản đồ lấy từ OpenStreetMap qua Internet.
- Marker nhóm theo xe; nhiều kiện chung xe không bị hiểu thành nhiều thiết bị GPS.
- Bấm đơn để xem vị trí và tuyến GPS chặng hiện tại (tối đa 24 giờ, bắt đầu không sớm hơn lúc xếp hàng).
- Vị trí cũ/không hợp lệ có màu và nhãn riêng; đơn không có tọa độ không được đặt điểm giả.
- Nhật ký và dữ liệu logistics lưu trên backend; localStorage chỉ lưu lựa chọn sáng/tối.
- Toàn bộ bộ HTML/assets gốc được giữ tại `../reference/trackvn/` để đối chiếu,
  không chạy script extension/analytics/service worker từ bản xuất trình duyệt.

**Bộ đính kèm không có backend tra cứu hãng.** Bản này chưa tự lấy trạng thái từ GHN/J&T/SPX/VNPost/Futa/LEX.
Chỉ nhập nhãn hãng/mã vận đơn không tạo ra GPS của bưu phẩm. GPS có thật phải đến từ Traccar,
liên kết chuyến và sự kiện xếp hàng; backend hãng cần tích hợp riêng bằng quyền truy cập phù hợp.
Không tái sử dụng hoặc vô hiệu hóa xác minh Turnstile của website nguồn.

API bổ sung:

| Phương thức | Endpoint | Nội dung |
|---|---|---|
| GET | /api/board | Kiện, chuyến, thiết bị, GPS và thời gian đồng bộ theo quyền |
| POST | /api/lookup | codes: mảng 1–100 mã; carrier: auto hoặc mã hãng |
| POST | /api/route | device_id; thêm shipment_id để giới hạn tuyến vào chặng của kiện |

Không có API public tracking không xác thực. Dữ liệu vẫn cách ly theo tài khoản.

## Đã thực hiện

- Đăng nhập bằng tài khoản Traccar, hỗ trợ nhập mã TOTP nếu tài khoản yêu cầu.
- Danh sách thiết bị theo quyền Traccar, vị trí gần nhất, đổi knot sang km/h.
- Bản đồ vị trí OpenStreetMap theo thao tác người dùng; sơ đồ hành trình 24 giờ.
- Tạo chuyến với thiết bị, tên tài xế, nơi đi/đến; khởi hành, hoàn tất, hủy kế hoạch.
- Tạo kiện có mã duy nhất trong tài khoản, mô tả, tuyến, nguồn gốc khai báo, mã lô.
- Chuỗi tiếp nhận → xếp xe → dỡ/trung chuyển → đang giao → giao thành công/thất bại/hoàn.
- Nhật ký sự kiện thêm mới, không có API sửa/xóa; trigger SQLite chặn UPDATE/DELETE sự kiện.
- Ghi người thao tác từ phiên đã xác thực, thời gian UTC do máy chủ tạo, địa điểm và ghi chú.
- Chống gửi trùng bằng request_id; cập nhật trạng thái và ghi sự kiện trong cùng transaction.
- Ngắt liên kết kiện–xe khi dỡ, giao thành công hoặc hoàn. Không kết thúc chuyến khi còn kiện.
- Không gán GPS có thời gian trước lúc xếp hàng làm vị trí hiện tại của kiện.
- Phân biệt vị trí suy ra từ xe, GPS cũ (>2 phút), GPS không hợp lệ và chưa có vị trí.
- Dữ liệu SQLite bền vững, không lưu nghiệp vụ bằng localStorage.

## Chạy với Traccar hiện có

Yêu cầu Python 3.12+ và máy chủ Traccar có tài khoản/thiết bị đã thiết lập.
Không cần cài thư viện Python bên ngoài.

```bash
cd fleet-logistics
python server.py
```

Mở http://localhost:8090, đăng nhập tài khoản tại Traccar http://127.0.0.1:8082.
Nếu máy chủ ở nơi khác, đặt TRACCAR_URL. Ví dụ trên Linux/macOS:

```bash
TRACCAR_URL=https://gps.example.org PUBLIC_ORIGIN=http://localhost:8090 python server.py
```

Windows PowerShell:

```powershell
cd fleet-logistics
$env:TRACCAR_URL = "https://gps.example.org"
$env:PUBLIC_ORIGIN = "http://localhost:8090"
python server.py
```

Không thêm `/api` vào TRACCAR_URL. Không nhập mật khẩu vào URL hoặc file cấu hình.
Tạo tài khoản, thiết bị và quyền trong giao diện Traccar trước. Đây không phải server GPS thay thế.

### Docker

```bash
cd fleet-logistics
cp .env.example .env
# Chỉnh TRACCAR_URL và PUBLIC_ORIGIN
# Traccar phải truy cập được từ container, không chỉ bind loopback của host.
docker compose up -d --build
```

Compose chỉ khởi động dịch vụ logistics, kết nối với Traccar đang có; không tự dựng Traccar.
Dữ liệu ở volume `logistics-data`. Không chạy `docker compose down -v` nếu muốn giữ dữ liệu.
Máy chủ Docker chỉ xuất port 8090 trên loopback. Khi vận hành từ xa, đặt reverse proxy HTTPS trước dịch vụ.
Ví dụ Caddy (cần tên miền/DNS và cấu hình TLS phù hợp):

```caddy
tracking.example.org {
    request_body {
        max_size 16KB
    }
    reverse_proxy 127.0.0.1:8090
}
```

Đặt PUBLIC_ORIGIN=https://tracking.example.org rồi khởi động lại dịch vụ.
Traccar qua mạng công cộng cũng phải dùng HTTPS; HTTP chỉ dành cho loopback/mạng riêng tin cậy.
GitHub Pages không chạy Python, SQLite hay nhận GPS; không thể triển khai toàn bộ ứng dụng trên Pages.

## Quy trình thử nghiệm đầu tiên

1. Cho Traccar nhận dữ liệu điện thoại/thiết bị thật, cấp quyền thiết bị cho tài khoản thử nghiệm.
2. Vào **Đội xe GPS**, kiểm tra tên xe, thời gian GPS, vị trí và hành trình.
3. Vào **Chuyến vận chuyển**, tạo chuyến với xe này rồi bấm **Khởi hành**.
4. Vào **Kiện hàng**, tạo kiện, mở **Xem / Bàn giao**, ghi **Đã tiếp nhận**.
5. Ghi **Đã xếp lên xe**, chọn chuyến đang chạy và địa điểm xác nhận.
6. Ghi **Đang giao**, sau đó **Đã giao** kèm mã biên nhận/tham chiếu bằng chứng.
7. Kiểm tra dòng thời gian, liên kết xe đã ngắt; kết thúc chuyến.
8. Với trung chuyển: **Đã dỡ hàng**, sau đó **Đã xếp lên xe** với chuyến mới.

Địa điểm bàn giao và nguồn gốc là nội dung nhân viên khai báo, chưa được xác minh bằng quét mã/cảm biến.
Bản đồ OSM tải từ dịch vụ ngoài khi người dùng mở vị trí; cần mạng Internet.
Sơ đồ tuyến là phép chiếu tương đối các tọa độ, không thay thế bản đồ dẫn đường.

## Phạm vi và giới hạn rõ ràng

Đây là MVP/pilot cho một máy chủ, chưa phải nền tảng logistics nhiều doanh nghiệp quy mô lớn.

- **Phân quyền logistics theo tài khoản:** mỗi tài khoản chỉ thấy dữ liệu mình tạo, kể cả admin Traccar.
  Chưa có tổ chức/team, chia sẻ kiện giữa nhân viên hay RBAC điều phối/tài xế. Không dùng chung mật khẩu
  để thay thế chức năng phân quyền nhóm; cần bổ sung mô hình tổ chức trước khi triển khai đội ngũ thực tế.
- **Fleet chỉ đọc GPS:** quản lý thiết bị, geofence, cảnh báo, bảo dưỡng tiếp tục ở Traccar.
  Tên tài xế trong chuyến là trường văn bản, chưa liên kết Driver/nhân sự Traccar.
- Một bản ghi shipment tương ứng một kiện. Chưa có đơn hàng cha chứa nhiều kiện, pallet/container.
- Bằng chứng giao hàng là mã/tham chiếu do nhân viên nhập, chưa có upload ảnh, chữ ký, OTP xác minh.
- Chưa có QR/RFID, ứng dụng tài xế, ghi bàn giao offline, public tracking link, ETA/tối ưu tuyến, EPCIS.
- Bảng theo dõi tải toàn bộ bản ghi của tài khoản; cần phân trang server-side khi triển khai dữ liệu lớn.
- GPS polling 15 giây khi trang đang mở; chưa dùng WebSocket. Bảng theo dõi cập nhật marker và chi tiết kiện đang chọn.
- SQLite phù hợp pilot một instance. Không chạy nhiều replica dùng chung file SQLite qua network filesystem.
- Phiên lưu trong RAM, hết hạn sau 8 giờ, mất khi khởi động lại. Mật khẩu không lưu.
- HTTP server chuẩn Python phục vụ pilot nội bộ sau reverse proxy; chưa kiểm thử tải, HA hay penetration test.
  Reverse proxy cần giới hạn kết nối, tốc độ và timeout trước khi mở Internet.
- Nhật ký append-only ở mức ứng dụng/DB trigger, không phải chữ ký số hay bằng chứng chống quản trị viên sửa DB.
- Chưa có quy trình sửa sai nghiệp vụ; không xóa log thủ công. Cần sự kiện hiệu chỉnh ở phiên bản tiếp theo.
- Schema v2 tự bổ sung carrier/tracking_code cho DB v1, giữ nguyên dữ liệu. Sao lưu trước khi nâng cấp.

## API

Tất cả endpoint nghiệp vụ yêu cầu cookie `vt_session` nhận từ đăng nhập.
POST dùng `Content-Type: application/json`, `X-Vtracking: 1` và Origin đúng PUBLIC_ORIGIN nếu có Origin.
Không bật CORS. Cookie HttpOnly, SameSite=Strict, Secure khi origin là HTTPS.

| Phương thức | Endpoint | Nội dung |
|---|---|---|
| POST | /api/login | email, password, code tùy chọn |
| POST | /api/logout | {} |
| GET | /api/me | Người dùng hiện tại |
| GET | /api/fleet | Thiết bị và GPS được cấp quyền |
| POST | /api/route | device_id; tuyến 24 giờ gần nhất |
| GET/POST | /api/trips | Danh sách / tạo chuyến |
| POST | /api/trips/{id}/status | status: active, completed, cancelled |
| GET/POST | /api/shipments | Danh sách / tạo kiện |
| GET | /api/shipments/{id} | Chi tiết, sự kiện, GPS suy ra khi có |
| POST | /api/shipments/{id}/events | kind, request_id, location, trip_id/note/proof tùy nghiệp vụ |

Ví dụ nội dung sự kiện xếp hàng:

```json
{
  "kind": "loaded",
  "request_id": "scan-unique-0001",
  "location": "Kho Vĩnh Long",
  "trip_id": "UUID-chuyen-dang-chay",
  "note": "Đã đối chiếu kiện"
}
```

Gửi lại cùng request_id và cùng payload trả sự kiện đã có; dùng lại với payload khác trả 409.
Thời gian sự kiện là lúc máy chủ ghi nhận. Chưa hỗ trợ backdate/offline event ingestion.
Mỗi request xác thực lại qua Traccar; thu hồi quyền thiết bị làm mất quyền xem GPS và thao tác chuyến tương ứng.
Không xóa và tái sử dụng ID tài khoản Traccar trên một DB mới trong khi giữ nguyên DB logistics cũ;
phải có kế hoạch di chuyển tài khoản/dữ liệu đồng bộ.

## Kiểm thử và sao lưu

```bash
cd fleet-logistics
python -m unittest discover -s tests -v
node --check static/app.js
node --check static/board.js
```

Bộ kiểm thử bao gồm HTTP dùng Traccar giả lập, cách ly tài khoản, quyền xe/read-only,
CSRF, thu hồi phiên, vòng đời kiện, bàn giao, yêu cầu bằng chứng, idempotency đồng thời,
rollback, append-only, dữ liệu tồn tại sau mở lại DB và GPS có trước lúc xếp hàng.
Không thay thế kiểm thử với máy chủ Traccar/thiết bị GPS thật.

Sao lưu an toàn SQLite đang chạy bằng SQLite backup API (không chỉ sao chép file .sqlite3 vì có WAL):

```bash
python -c "import sqlite3; s=sqlite3.connect('data/logistics.sqlite3'); d=sqlite3.connect('logistics-backup.sqlite3'); s.backup(d); d.close(); s.close()"
```

Đối với Docker, đường dẫn DB bên trong container là /data/logistics.sqlite3.
Định kỳ lưu bản sao ra nơi riêng và thử khôi phục khi dịch vụ dừng.

## Giao diện công khai trên GitHub Pages

https://xulytiengviet.github.io/Vtracking/ mở giao diện chung với adapter dữ liệu mẫu chỉ đọc.
`../index.html` được sinh từ `static/index.html` bằng `python pages/build.py`; đường dẫn assets tương đối,
hoạt động dưới `/Vtracking/`. Khi sửa HTML chung, chạy lại lệnh sinh trang trước khi commit.
`.nojekyll` giúp Pages phục vụ giao diện thay vì render README.

Dữ liệu mẫu định danh DEMO và banner cố định. Không có mật khẩu, token, GPS hoặc vận đơn thật trong bản Pages.
`pages/demo.js` không gửi request đến backend và từ chối đăng nhập/các thao tác ghi.
Nút định vị dùng Geolocation sau thao tác người dùng; vị trí thiết bị không gắn với đơn mẫu,
không được lưu hoặc gửi vào Traccar. Bản đồ nền vẫn tải ô bản đồ từ OpenStreetMap.
Nút mở hệ thống thật chỉ điều hướng tới URL HTTPS do người dùng nhập; không kết nối chéo cookie/CORS.
Máy chủ Python tiếp tục phục vụ HTML gốc và API thật, không tải adapter demo.

Kiểm thử: `node pages/test-demo.cjs`, `node --check pages/pages.js`, `python pages/build.py`.
