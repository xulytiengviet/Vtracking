"""Generate root Pages entry from the shared production interface (no private data)."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
html = (root / 'fleet-logistics/static/index.html').read_text()
html = html.replace('<html lang="vi">', '<html lang="vi" class="pages">')
html = re.sub(r'(src|href)="/([^"\s]*)"', lambda m: f'{m[1]}="./fleet-logistics/static/{m[2]}"' if m[2] else 'href="./"', html)
html = html.replace('<script src="./fleet-logistics/static/app.js"', '<script src="./fleet-logistics/pages/demo.js" defer></script><script src="./fleet-logistics/static/app.js"')
html = html.replace('</head>', '<link rel="stylesheet" href="./fleet-logistics/pages/pages.css"><script src="./fleet-logistics/pages/pages.js" defer></script><meta name="description" content="Vtracking: giao diện theo dõi vận đơn, bản đồ và GPS. Bản trình diễn công khai."></head>')
html = html.replace('</header>', '''</header><div class="preview-banner"><strong>DỮ LIỆU MINH HỌA</strong><span>100 vận đơn và 100 xe giả định. Tuyến nội suy để mô phỏng, không phải chỉ đường hoặc dữ liệu vận chuyển thật.</span><button id="open-live">Mở hệ thống thật ↗</button></div>''')
html = html.replace('<section id="tracking-board">', '<section id="tracking-board"><div class="demo-controls"><strong>Mô phỏng 100 vận đơn</strong><button id="demo-all">Hiện đủ 100 mã</button><button id="demo-pause">Ⅱ Tạm dừng</button><label>Tốc độ <select id="demo-speed"><option value="1">1×</option><option value="3">3×</option><option value="10">10×</option></select></label><label><input id="demo-routes" type="checkbox" checked> Hiện tuyến</label><button id="demo-codes">Tải 100 mã CSV</button></div><div class="personal-controls"><button id="personal-gps">◎ Vị trí của tôi</button><p id="personal-status">Chỉ định vị khi bạn cho phép. Tọa độ dùng trong tab này để hiển thị bản đồ, không gửi vào hệ thống logistics.</p></div>')
html = html.replace('</body>', '''<dialog id="live-dialog"><div class="dialog-head"><h2>Mở máy chủ Vtracking</h2><button id="live-close" aria-label="Đóng">×</button></div><p>Nhập địa chỉ máy chủ Fleet + Logistics đã triển khai để đăng nhập và sử dụng dữ liệu thật. GitHub Pages chỉ phục vụ bản giao diện minh họa.</p><form id="live-form"><label>Địa chỉ HTTPS<input id="live-url" type="url" placeholder="https://tracking.example.org" required></label><button class="primary">Mở hệ thống</button></form></dialog></body>''')
html = html.replace('Dữ liệu từ hệ thống Vtracking của bạn. Nhãn hãng không có nghĩa đã kết nối API của hãng.', 'Thử mã VT-DEMO-001, GHN-DEMO-002 hoặc JT-DEMO-003. Tất cả là dữ liệu minh họa.')
html = re.sub(r'((?:src|href)="\./fleet-logistics/[^"?]+\.(?:css|js))(?:\?[^"]*)?"', r'\1?v=0.3.0"', html)
(root / 'index.html').write_text(html)
(root / '.nojekyll').touch()
print('Generated index.html for /Vtracking/ with relative asset paths.')
