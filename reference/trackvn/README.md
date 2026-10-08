# TrackVN — bộ giao diện người dùng cung cấp

Bảo toàn toàn bộ nội dung assets(1).zip và HTML đính kèm để đối chiếu.
Đây là bản xuất trình duyệt/build đã biên dịch, không có mã nguồn React/TypeScript gốc, backend /api/track hay backend xác minh phiên.

Các file gốc không được phục vụ bởi server Vtracking: HTML có mã chèn từ browser extension, analytics và service worker của website nguồn.
Bản tích hợp hoạt động nằm tại ../../fleet-logistics/static, sử dụng ảnh thương hiệu/logo từ bộ đính kèm và giao diện được viết lại để kết nối backend Vtracking. Không thực thi analytics, extension script hoặc cơ chế xác minh phiên của nguồn cũ.

Giữ nguyên thông báo bản quyền trong bundle. Tài sản nhập từ người dùng giữ giấy phép/quyền của chủ sở hữu gốc, không tự đổi thành Apache-2.0 của Traccar.
