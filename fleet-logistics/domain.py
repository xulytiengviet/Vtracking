"""Vtracking Fleet + Logistics pilot domain. SPDX-License-Identifier: Apache-2.0"""
import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


class Problem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def field(data, key, required=True, maximum=500):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value) > maximum:
        raise Problem(400, f'Trường {key} không hợp lệ (tối đa {maximum} ký tự).')
    value = value.strip()
    if required and not value:
        raise Problem(400, f'Cần nhập {key}.')
    return value


def positive_id(value):
    if type(value) is not int or value <= 0:
        raise Problem(400, 'ID phải là số nguyên dương.')
    return value


class Store:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS trips (
                  id TEXT PRIMARY KEY, owner INTEGER NOT NULL, code TEXT NOT NULL,
                  device_id INTEGER NOT NULL, driver TEXT NOT NULL,
                  origin TEXT NOT NULL, destination TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'planned', created_at TEXT NOT NULL,
                  UNIQUE(owner, code));
                CREATE TABLE IF NOT EXISTS shipments (
                  id TEXT PRIMARY KEY, owner INTEGER NOT NULL, code TEXT NOT NULL,
                  description TEXT NOT NULL, origin TEXT NOT NULL, destination TEXT NOT NULL,
                  source TEXT NOT NULL, lot TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'created', trip_id TEXT REFERENCES trips(id),
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(owner, code));
                CREATE TABLE IF NOT EXISTS events (
                  id TEXT PRIMARY KEY, owner INTEGER NOT NULL,
                  shipment_id TEXT NOT NULL REFERENCES shipments(id), kind TEXT NOT NULL,
                  at TEXT NOT NULL, actor TEXT NOT NULL, location TEXT NOT NULL,
                  note TEXT NOT NULL, proof TEXT NOT NULL, trip_id TEXT REFERENCES trips(id),
                  request_id TEXT NOT NULL, digest TEXT NOT NULL,
                  UNIQUE(owner, request_id));
                CREATE INDEX IF NOT EXISTS event_shipment ON events(shipment_id, at);
                CREATE INDEX IF NOT EXISTS shipment_owner ON shipments(owner);
                CREATE INDEX IF NOT EXISTS trip_owner ON trips(owner);
                CREATE TRIGGER IF NOT EXISTS immutable_event_update BEFORE UPDATE ON events
                  BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS immutable_event_delete BEFORE DELETE ON events
                  BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
                PRAGMA user_version=1;
            ''')
            columns = {row[1] for row in db.execute('PRAGMA table_info(shipments)')}
            if 'carrier' not in columns:
                db.execute("ALTER TABLE shipments ADD COLUMN carrier TEXT NOT NULL DEFAULT 'local'")
            if 'tracking_code' not in columns:
                db.execute("ALTER TABLE shipments ADD COLUMN tracking_code TEXT NOT NULL DEFAULT ''")
            db.execute('PRAGMA user_version=2')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def owned(db, table, identifier, owner):
        row = db.execute(f'SELECT * FROM {table} WHERE id=? AND owner=?', (identifier, owner)).fetchone()
        if row is None:
            raise Problem(404, 'Không tìm thấy dữ liệu trong tài khoản này.')
        return dict(row)

    def list(self, table, owner):
        if table not in ('shipments', 'trips'):
            raise Problem(404, 'Không tìm thấy.')
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                f'SELECT * FROM {table} WHERE owner=? ORDER BY created_at DESC', (owner,))]

    def shipment(self, owner, identifier):
        with self.connect() as db:
            result = self.owned(db, 'shipments', identifier, owner)
            result['events'] = [dict(r) for r in db.execute(
                'SELECT * FROM events WHERE shipment_id=? AND owner=? ORDER BY rowid', (identifier, owner))]
            return result

    def create_shipment(self, user, data):
        values = {k: field(data, k, k in ('code', 'description', 'origin', 'destination'))
                  for k in ('code', 'description', 'origin', 'destination', 'source', 'lot')}
        carrier = field(data, 'carrier', False, 40) or 'local'
        if carrier not in ('local', 'ghn', 'jt', 'spx', 'vnpost', 'futa', 'lex'):
            raise Problem(400, 'Nhà vận chuyển không hợp lệ.')
        tracking_code = field(data, 'tracking_code', False, 100)
        identifier, timestamp = str(uuid.uuid4()), now()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                db.execute('''INSERT INTO shipments
                    (id,owner,code,description,origin,destination,source,lot,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)''',
                    (identifier, user['id'], *values.values(), timestamp, timestamp))
            except sqlite3.IntegrityError:
                raise Problem(409, 'Mã kiện đã tồn tại.') from None
            db.execute('UPDATE shipments SET carrier=?, tracking_code=? WHERE id=?',
                       (carrier, tracking_code, identifier))
            db.execute('''INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                       (str(uuid.uuid4()), user['id'], identifier, 'created', timestamp,
                        str(user['name']), values['origin'], 'Khởi tạo kiện hàng', '', None,
                        str(uuid.uuid4()), ''))
        return self.shipment(user['id'], identifier)

    def create_trip(self, user, data, device_ids):
        device = positive_id(data.get('device_id'))
        if device not in device_ids:
            raise Problem(403, 'Không có quyền sử dụng thiết bị GPS này.')
        values = [field(data, k) for k in ('code', 'driver', 'origin', 'destination')]
        identifier = str(uuid.uuid4())
        with self.connect() as db:
            try:
                db.execute('''INSERT INTO trips
                  (id,owner,code,driver,origin,destination,device_id,created_at) VALUES (?,?,?,?,?,?,?,?)''',
                           (identifier, user['id'], *values, device, now()))
            except sqlite3.IntegrityError:
                raise Problem(409, 'Mã chuyến đã tồn tại.') from None
            return self.owned(db, 'trips', identifier, user['id'])

    def trip_status(self, owner, identifier, data, device_ids):
        status = field(data, 'status')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            trip = self.owned(db, 'trips', identifier, owner)
            if trip['device_id'] not in device_ids:
                raise Problem(403, 'Quyền thiết bị đã bị thu hồi.')
            allowed = {'planned': {'active', 'cancelled'}, 'active': {'completed'},
                       'completed': set(), 'cancelled': set()}
            if status not in allowed[trip['status']]:
                raise Problem(409, 'Chuyển trạng thái chuyến không hợp lệ.')
            if status == 'completed' and db.execute(
                    'SELECT 1 FROM shipments WHERE trip_id=?', (identifier,)).fetchone():
                raise Problem(409, 'Cần dỡ hoặc giao hết kiện trước khi kết thúc chuyến.')
            db.execute('UPDATE trips SET status=? WHERE id=?', (status, identifier))
            return self.owned(db, 'trips', identifier, owner)

    def event(self, user, identifier, data, device_ids):
        kind = field(data, 'kind')
        request_id = field(data, 'request_id', maximum=80)
        if not re.fullmatch(r'[a-zA-Z0-9_-]{8,80}', request_id):
            raise Problem(400, 'request_id cần 8–80 ký tự chữ, số, gạch ngang hoặc gạch dưới.')
        location = field(data, 'location')
        note = field(data, 'note', False, 2000)
        proof = field(data, 'proof', False, 1000)
        digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        transitions = {
            'created': {'received'}, 'received': {'loaded', 'returned'},
            'loaded': {'unloaded', 'out_for_delivery'},
            'unloaded': {'loaded', 'returned'},
            'out_for_delivery': {'delivered', 'delivery_failed', 'unloaded'},
            'delivery_failed': {'out_for_delivery', 'unloaded'},
            'delivered': set(), 'returned': set(),
        }
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            shipment = self.owned(db, 'shipments', identifier, user['id'])
            old = db.execute('SELECT * FROM events WHERE owner=? AND request_id=?',
                             (user['id'], request_id)).fetchone()
            if old:
                if old['shipment_id'] != identifier or old['digest'] != digest:
                    raise Problem(409, 'request_id đã dùng cho thao tác khác.')
                return dict(old)
            if kind not in transitions[shipment['status']]:
                raise Problem(409, 'Trạng thái kiện không cho phép thao tác này.')
            trip_id = shipment['trip_id']
            if kind == 'loaded':
                trip_id = field(data, 'trip_id')
            if trip_id:
                trip = self.owned(db, 'trips', trip_id, user['id'])
                if trip['device_id'] not in device_ids:
                    raise Problem(403, 'Không có quyền thiết bị của chuyến.')
                if trip['status'] != 'active':
                    raise Problem(409, 'Chuyến phải đang vận chuyển.')
            if kind == 'delivered' and not proof:
                raise Problem(400, 'Cần mã biên nhận hoặc tham chiếu bằng chứng giao hàng.')
            if kind in ('delivery_failed', 'returned') and not note:
                raise Problem(400, 'Cần ghi lý do.')
            timestamp, event_id = now(), str(uuid.uuid4())
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       (event_id, user['id'], identifier, kind, timestamp, str(user['name']),
                        location, note, proof, trip_id, request_id, digest))
            binding = None if kind in ('unloaded', 'delivered', 'returned') else trip_id
            db.execute('UPDATE shipments SET status=?,trip_id=?,updated_at=? WHERE id=?',
                       (kind, binding, timestamp, identifier))
            return dict(db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone())
