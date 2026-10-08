"""Small single-instance pilot server; deploy behind an HTTPS reverse proxy.
SPDX-License-Identifier: Apache-2.0
"""
import http.cookiejar
import json
import logging
import mimetypes
import os
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from domain import Problem, Store, positive_id

ROOT = Path(__file__).parent


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Traccar:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.opener = urllib.request.build_opener(
            NoRedirect(), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, path, form=None, method=None):
        payload = urllib.parse.urlencode(form).encode() if form is not None else None
        req = urllib.request.Request(self.base + path, data=payload, method=method,
                                     headers={'Accept': 'application/json'})
        try:
            with self.opener.open(req, timeout=15) as response:
                raw = response.read(8_000_001)
                if len(raw) > 8_000_000:
                    raise Problem(502, 'Dữ liệu GPS quá lớn; hãy thu hẹp phạm vi.')
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            if error.code in (401, 403, 404):
                raise Problem(401, 'Phiên Traccar hết hạn hoặc thông tin đăng nhập không hợp lệ.') from None
            raise Problem(502, 'Traccar từ chối yêu cầu. Kiểm tra cấu hình máy chủ.') from None
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise Problem(502, 'Không kết nối được Traccar hoặc phản hồi không hợp lệ.') from None


class Application:
    def __init__(self, store, origin, traccar_url, factory=Traccar):
        self.store, self.origin, self.traccar_url = store, origin.rstrip('/'), traccar_url
        self.factory = factory
        self.sessions, self.attempts = {}, {}
        self.lock = threading.Lock()

    def login(self, data, ip):
        stamp = time.monotonic()
        with self.lock:
            self.attempts = {k: v for k, v in self.attempts.items() if stamp - v[-1] < 60}
            attempts = [v for v in self.attempts.get(ip, []) if stamp - v < 60]
            if len(attempts) >= 10:
                raise Problem(429, 'Thử đăng nhập quá nhiều. Vui lòng chờ một phút.')
            self.attempts[ip] = attempts + [stamp]
        if not all(isinstance(data.get(k), str) and 0 < len(data[k]) <= 500 for k in ('email', 'password')):
            raise Problem(400, 'Cần email và mật khẩu hợp lệ.')
        upstream = self.factory(self.traccar_url)
        form = {k: data[k] for k in ('email', 'password')}
        if data.get('code'):
            if not isinstance(data['code'], str) or not data['code'].isdigit() or len(data['code']) != 6:
                raise Problem(400, 'Mã xác thực phải gồm 6 chữ số.')
            form['code'] = data['code']
        user = upstream.request('/api/session', form)
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.sessions = {k: v for k, v in self.sessions.items() if v['expires'] > stamp}
            self.sessions[token] = {'upstream': upstream, 'expires': stamp + 8 * 3600,
                                    'lock': threading.Lock()}
        return token, self.public_user(user)

    @staticmethod
    def public_user(user):
        return {k: user.get(k) for k in ('id', 'name', 'email', 'readonly')}

    def session(self, cookie):
        parsed = SimpleCookie()
        try:
            parsed.load(cookie or '')
            token = parsed['vt_session'].value
        except (KeyError, ValueError, CookieError):
            raise Problem(401, 'Vui lòng đăng nhập.') from None
        with self.lock:
            session = self.sessions.get(token)
            if not session or session['expires'] < time.monotonic():
                self.sessions.pop(token, None)
                raise Problem(401, 'Phiên đăng nhập đã hết hạn.')
        return token, session

    def dispatch(self, method, path, data, session):
        upstream = session['upstream']
        # /devices passes Traccar's security filter on every request (revocation/expiry).
        devices = upstream.request('/api/devices')
        user = upstream.request('/api/session')
        if user.get('disabled'):
            raise Problem(403, 'Tài khoản bị vô hiệu hóa.')
        if method != 'GET' and path not in ('/api/route', '/api/lookup') and user.get('readonly'):
            raise Problem(403, 'Tài khoản chỉ có quyền xem.')
        owner, device_ids = user['id'], {d['id'] for d in devices}
        if path == '/api/me' and method == 'GET':
            return self.public_user(user)
        if path == '/api/fleet' and method == 'GET':
            positions = upstream.request('/api/positions')
            return {'devices': devices, 'positions': [p for p in positions if p['deviceId'] in device_ids]}
        if path == '/api/board' and method == 'GET':
            return self.board(owner, devices, upstream)
        if path == '/api/lookup' and method == 'POST':
            codes = data.get('codes')
            if not isinstance(codes, list) or not 1 <= len(codes) <= 100 or any(
                    not isinstance(c, str) or not 1 <= len(c.strip()) <= 100 for c in codes):
                raise Problem(400, 'Nhập từ 1 đến 100 mã, tối đa 100 ký tự mỗi mã.')
            carrier = data.get('carrier', 'auto')
            shipments = self.store.list('shipments', owner)
            return {'source': 'vtracking', 'carrier_api_connected': False, 'results': [
                {'code': code, 'shipments': [s for s in shipments
                    if code.strip().casefold() in (s['code'].casefold(), s['tracking_code'].casefold())
                    and carrier in ('auto', s['carrier'])]} for code in codes]}
        if path == '/api/route' and method == 'POST':
            device_id = positive_id(data.get('device_id'))
            if device_id not in device_ids:
                raise Problem(403, 'Không có quyền xem hành trình xe.')
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=24)
            if data.get('shipment_id'):
                shipment = self.store.shipment(owner, data['shipment_id'])
                if not shipment['trip_id']:
                    raise Problem(409, 'Kiện không còn gắn với chuyến đang chạy.')
                with self.store.connect() as db:
                    trip = self.store.owned(db, 'trips', shipment['trip_id'], owner)
                if trip['device_id'] != device_id:
                    raise Problem(403, 'Thiết bị không thuộc chuyến của kiện.')
                loaded = next(e for e in reversed(shipment['events']) if e['kind'] == 'loaded')
                start = max(start, datetime.fromisoformat(loaded['at']))
            query = urllib.parse.urlencode({'deviceId': device_id, 'from': start.isoformat(),
                                            'to': end.isoformat()})
            return upstream.request('/api/reports/route?' + query)
        for table in ('shipments', 'trips'):
            if path == '/api/' + table:
                if method == 'GET':
                    return self.store.list(table, owner)
                if method == 'POST':
                    if table == 'shipments':
                        return self.store.create_shipment(user, data)
                    return self.store.create_trip(user, data, device_ids)
        parts = path.strip('/').split('/')
        if len(parts) == 3 and parts[:2] == ['api', 'shipments'] and method == 'GET':
            shipment = self.store.shipment(owner, parts[2])
            shipment['position'] = None
            if shipment['trip_id']:
                with self.store.connect() as db:
                    trip = self.store.owned(db, 'trips', shipment['trip_id'], owner)
                if trip['device_id'] in device_ids:
                    positions = upstream.request('/api/positions')
                    position = next((p for p in positions if p['deviceId'] == trip['device_id']), None)
                    loaded = next((e for e in reversed(shipment['events']) if e['kind'] == 'loaded'), None)
                    try:
                        fresh_binding = loaded and position and datetime.fromisoformat(
                            position['fixTime'].replace('Z', '+00:00')) >= datetime.fromisoformat(loaded['at'])
                    except (ValueError, KeyError, TypeError):
                        fresh_binding = False
                    if fresh_binding:
                        shipment['position'] = {k: position.get(k) for k in
                                                ('latitude', 'longitude', 'fixTime', 'valid', 'accuracy')}
                        shipment['position']['source'] = 'vehicle_inferred'
            return shipment
        if len(parts) == 4 and method == 'POST':
            if parts[:2] == ['api', 'shipments'] and parts[3] == 'events':
                return self.store.event(user, parts[2], data, device_ids)
            if parts[:2] == ['api', 'trips'] and parts[3] == 'status':
                return self.store.trip_status(owner, parts[2], data, device_ids)
        raise Problem(404, 'Không tìm thấy API.')

    def board(self, owner, devices, upstream):
        devices_by_id = {d['id']: d for d in devices}
        positions = [p for p in upstream.request('/api/positions') if p['deviceId'] in devices_by_id]
        by_device = {p['deviceId']: p for p in positions}
        shipments = self.store.list('shipments', owner)
        trips = self.store.list('trips', owner)
        by_trip = {t['id']: t for t in trips}
        with self.store.connect() as db:
            loaded = {r['shipment_id']: r['at'] for r in db.execute(
                "SELECT shipment_id, at FROM events WHERE owner=? AND kind='loaded' ORDER BY rowid", (owner,))}
        for shipment in shipments:
            shipment['position'] = None
            trip = by_trip.get(shipment['trip_id'])
            shipment['device_id'] = trip['device_id'] if trip and trip['device_id'] in devices_by_id else None
            position = by_device.get(shipment['device_id'])
            try:
                fresh_binding = position and datetime.fromisoformat(position['fixTime'].replace('Z', '+00:00')) >= datetime.fromisoformat(loaded[shipment['id']])
            except (ValueError, KeyError, TypeError):
                fresh_binding = False
            if fresh_binding:
                shipment['position'] = {k: position.get(k) for k in (
                    'latitude', 'longitude', 'fixTime', 'valid', 'accuracy', 'speed', 'course')}
                shipment['position']['source'] = 'vehicle_inferred'
        return {'shipments': shipments, 'trips': trips, 'devices': devices, 'positions': positions,
                'updated_at': datetime.now(timezone.utc).isoformat(), 'carrier_api_connected': False}


def handler_class(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Avoid logging paths/identifiers, cookies or credentials.
            logging.info('HTTP request completed')

        def send(self, status, body, content_type='application/json; charset=utf-8', cookie=None):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                             "img-src 'self' data: https://tile.openstreetmap.org; frame-src https://www.openstreetmap.org; "
                             "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.end_headers()
            self.wfile.write(body)

        def cookie(self, token='', expire=False):
            value = f'vt_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={0 if expire else 28800}'
            return value + ('; Secure' if app.origin.startswith('https://') else '')

        def handle_request(self):
            try:
                path = urllib.parse.urlsplit(self.path).path
                if self.command == 'GET' and not path.startswith('/api/'):
                    static_root = (ROOT / 'static').resolve()
                    filename = 'index.html' if path in ('/', '/board') else urllib.parse.unquote(path).lstrip('/')
                    target = (static_root / filename).resolve()
                    if not target.is_relative_to(static_root) or not target.is_file():
                        raise Problem(404, 'Không tìm thấy tài nguyên.')
                    mime = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
                    return self.send(200, target.read_bytes(), mime)
                data = {}
                if self.command == 'POST':
                    if self.headers.get('Origin') not in (None, app.origin) or self.headers.get('X-Vtracking') != '1':
                        raise Problem(403, 'Yêu cầu không cùng nguồn hoặc thiếu X-Vtracking.')
                    if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                        raise Problem(415, 'Chỉ chấp nhận JSON.')
                    try:
                        size = int(self.headers.get('Content-Length', '0'))
                        if size <= 0 or size > 16384:
                            raise Problem(413, 'Nội dung phải từ 1 đến 16384 byte.')
                        data = json.loads(self.rfile.read(size))
                    except (ValueError, UnicodeError):
                        raise Problem(400, 'JSON không hợp lệ.') from None
                    if not isinstance(data, dict):
                        raise Problem(400, 'Nội dung phải là một đối tượng JSON.')
                if path == '/api/login' and self.command == 'POST':
                    token, user = app.login(data, self.client_address[0])
                    return self.send(200, user, cookie=self.cookie(token))
                token, session = app.session(self.headers.get('Cookie'))
                with session['lock']:
                    if path == '/api/logout' and self.command == 'POST':
                        with app.lock:
                            app.sessions.pop(token, None)
                        try:
                            session['upstream'].request('/api/session', method='DELETE')
                        except Problem:
                            pass
                        return self.send(200, {'ok': True}, cookie=self.cookie(expire=True))
                    result = app.dispatch(self.command, path, data, session)
                self.send(200, result)
            except Problem as error:
                self.send(error.status, {'error': error.message})
            except sqlite3.Error:
                logging.exception('Database error')
                self.send(503, {'error': 'Cơ sở dữ liệu bận hoặc không khả dụng.'})
            except Exception:
                logging.exception('Request error')
                self.send(500, {'error': 'Lỗi nội bộ; kiểm tra nhật ký máy chủ.'})

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()
    return Handler


def main():
    logging.basicConfig(level=logging.INFO)
    origin = os.environ.get('PUBLIC_ORIGIN', 'http://localhost:8090').rstrip('/')
    traccar = os.environ.get('TRACCAR_URL', 'http://127.0.0.1:8082')
    for value in (origin, traccar):
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
            raise SystemExit('PUBLIC_ORIGIN và TRACCAR_URL phải là URL HTTP(S) hợp lệ, không chứa thông tin đăng nhập.')
    database = Path(os.environ.get('DATABASE_PATH', str(ROOT / 'data' / 'logistics.sqlite3')))
    database.parent.mkdir(parents=True, exist_ok=True)
    app = Application(Store(database), origin, traccar)
    server = ThreadingHTTPServer((os.environ.get('BIND', '127.0.0.1'), int(os.environ.get('PORT', '8090'))), handler_class(app))
    logging.info('Fleet + Logistics pilot listening on port %s', server.server_port)
    server.serve_forever()


if __name__ == '__main__':
    main()
