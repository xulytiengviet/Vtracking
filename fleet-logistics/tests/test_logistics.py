"""Domain and HTTP tests using a fake Traccar boundary, not a live GPS server."""
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer
from domain import Problem, Store
from server import Application, handler_class

USER={'id':1,'name':'Điều phối','email':'test@example.com'}

class DomainTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(str(Path(self.tmp.name)/'db'))
        self.s=self.store.create_shipment(USER,{'code':'K1','description':'Nông sản','origin':'A','destination':'B'})
        self.t=self.store.create_trip(USER,{'code':'T1','device_id':10,'driver':'Tài xế','origin':'A','destination':'B'},{10})
        self.n=0
    def tearDown(self):self.tmp.cleanup()
    def event(self,kind,**extra):
        self.n+=1
        return self.store.event(USER,self.s['id'],{'kind':kind,'location':'Kho','request_id':f'request-{self.n}',**extra},{10})
    def problem(self,status,fn):
        with self.assertRaises(Problem) as ctx:fn()
        self.assertEqual(status,ctx.exception.status)
    def activate(self):self.store.trip_status(1,self.t['id'],{'status':'active'},{10})
    def test_delivery_binding_and_proof(self):
        self.event('received');self.activate();self.event('loaded',trip_id=self.t['id'])
        self.problem(409,lambda:self.store.trip_status(1,self.t['id'],{'status':'completed'},{10}))
        self.event('out_for_delivery');self.problem(400,lambda:self.event('delivered'))
        self.event('delivered',proof='BIEN-NHAN-001')
        s=self.store.shipment(1,self.s['id'])
        self.assertEqual('delivered',s['status']);self.assertIsNone(s['trip_id'])
        self.assertEqual(5,len(s['events']));self.assertEqual(USER['name'],s['events'][-1]['actor'])
        self.store.trip_status(1,self.t['id'],{'status':'completed'},{10})
        self.problem(409,lambda:self.event('loaded',trip_id=self.t['id']))
    def test_transfer_failure_return(self):
        self.event('received');self.activate();self.event('loaded',trip_id=self.t['id']);self.event('unloaded')
        self.assertIsNone(self.store.shipment(1,self.s['id'])['trip_id'])
        self.event('loaded',trip_id=self.t['id']);self.event('out_for_delivery')
        self.problem(400,lambda:self.event('delivery_failed'))
        self.event('delivery_failed',note='Vắng người nhận');self.event('unloaded');self.event('returned',note='Trả hàng')
        self.assertIsNone(self.store.shipment(1,self.s['id'])['trip_id'])
    def test_cross_account(self):
        self.assertEqual([],self.store.list('shipments',2))
        self.problem(404,lambda:self.store.shipment(2,self.s['id']))
        self.problem(404,lambda:self.store.event({'id':2,'name':'Other'},self.s['id'],{'kind':'received','location':'Kho','request_id':'other-account'},{10}))
        self.problem(404,lambda:self.store.trip_status(2,self.t['id'],{'status':'active'},{10}))
    def test_device_permissions_and_trip_state(self):
        self.event('received')
        self.problem(409,lambda:self.event('loaded',trip_id=self.t['id']))
        self.problem(403,lambda:self.store.trip_status(1,self.t['id'],{'status':'active'},set()))
        self.activate()
        self.problem(403,lambda:self.store.event(USER,self.s['id'],{'kind':'loaded','trip_id':self.t['id'],'location':'Kho','request_id':'revoked-device'},set()))
    def test_idempotency(self):
        data={'kind':'received','location':'Kho','request_id':'same-request'}
        a=self.store.event(USER,self.s['id'],data,{10});b=self.store.event(USER,self.s['id'],data,{10})
        self.assertEqual(a['id'],b['id']);self.assertEqual(2,len(self.store.shipment(1,self.s['id'])['events']))
        self.problem(409,lambda:self.store.event(USER,self.s['id'],{**data,'location':'Different'},{10}))
    def test_concurrent_retry(self):
        results=[]
        def send():results.append(self.store.event(USER,self.s['id'],{'kind':'received','location':'Kho','request_id':'parallel-request'},{10})['id'])
        threads=[threading.Thread(target=send) for _ in range(6)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(6,len(results));self.assertEqual(1,len(set(results)))
        self.assertEqual(2,len(self.store.shipment(1,self.s['id'])['events']))
    def test_persistence_immutability(self):
        with self.store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM events')
        self.assertEqual('K1',Store(self.store.path).shipment(1,self.s['id'])['code'])
    def test_v1_migration_keeps_shipments(self):
        with self.store.connect() as db:
            db.execute('ALTER TABLE shipments DROP COLUMN carrier')
            db.execute('ALTER TABLE shipments DROP COLUMN tracking_code')
            db.execute('PRAGMA user_version=1')
        upgraded=Store(self.store.path)
        shipment=upgraded.shipment(1,self.s['id'])
        self.assertEqual('local',shipment['carrier'])
        self.assertEqual('',shipment['tracking_code'])
        self.assertEqual('K1',shipment['code'])
        self.assertEqual(1,len(shipment['events']))

    def test_duplicate_and_invalid_transition(self):
        self.problem(409,lambda:self.store.create_shipment(USER,self.s))
        self.problem(409,lambda:self.event('delivered',proof='X'))
        self.assertEqual(1,len(self.store.shipment(1,self.s['id'])['events']))

class FakeTraccar:
    revoked=False
    readonly=False
    def __init__(self,base):pass
    def request(self,path,form=None,method=None):
        if self.revoked:raise Problem(401,'Revoked')
        if path=='/api/session':
            if form and form.get('password')!='test':raise Problem(401,'Bad credentials')
            return {**USER,'readonly':self.readonly}
        if path=='/api/devices':return [{'id':10,'name':'Xe 10'}]
        if path=='/api/positions':return [{'deviceId':10,'latitude':10,'longitude':106,'valid':True,'fixTime':'2020-01-01T00:00:00Z'},{'deviceId':99}]
        if path.startswith('/api/reports/route?'):return []
        raise AssertionError(path)

class HttpTests(unittest.TestCase):
    def setUp(self):
        FakeTraccar.revoked=False;FakeTraccar.readonly=False
        self.tmp=tempfile.TemporaryDirectory()
        self.app=Application(Store(str(Path(self.tmp.name)/'db')),'https://tracking.test','http://traccar',FakeTraccar)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler_class(self.app))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.cookie=''
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,data=None,origin='https://tracking.test',custom=True):
        headers={'Cookie':self.cookie,'Origin':origin}
        if data is not None:headers['Content-Type']='application/json'
        if custom:headers['X-Vtracking']='1'
        req=urllib.request.Request(f'http://127.0.0.1:{self.server.server_port}'+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try:response=urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:response=e
        with response:
            if response.headers.get('Set-Cookie'):self.cookie=response.headers['Set-Cookie'].split(';')[0]
            return response.status,response.read(),response.headers
    def login(self):
        status,_,headers=self.request('/api/login',{'email':'test@example.com','password':'test'})
        self.assertEqual(200,status);self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('Secure',headers['Set-Cookie'])
    def test_auth_csrf_revocation_logout(self):
        self.assertEqual(401,self.request('/api/shipments')[0])
        self.assertEqual(403,self.request('/api/login',{},origin='https://evil.test')[0])
        self.assertEqual(403,self.request('/api/login',{},custom=False)[0]);self.login()
        self.assertEqual(200,self.request('/api/shipments')[0]);FakeTraccar.revoked=True
        self.assertEqual(401,self.request('/api/shipments')[0]);self.assertEqual(200,self.request('/api/logout',{})[0])
        self.assertEqual(401,self.request('/api/shipments')[0])
    def test_readonly_and_fleet_scope(self):
        self.login();fleet=json.loads(self.request('/api/fleet')[1])
        self.assertEqual([10],[p['deviceId'] for p in fleet['positions']])
        self.assertEqual(403,self.request('/api/route',{'device_id':99})[0]);FakeTraccar.readonly=True
        self.assertEqual(403,self.request('/api/shipments',{})[0]);self.assertEqual(200,self.request('/api/route',{'device_id':10})[0])
    def test_lifecycle_and_old_gps(self):
        self.login()
        status,body,_=self.request('/api/shipments',{'code':'K','description':'Hàng','origin':'A','destination':'B'})
        self.assertEqual(200,status);sid=json.loads(body)['id']
        status,body,_=self.request('/api/trips',{'code':'T','device_id':10,'driver':'D','origin':'A','destination':'B'})
        self.assertEqual(200,status);tid=json.loads(body)['id']
        self.assertEqual(200,self.request(f'/api/trips/{tid}/status',{'status':'active'})[0])
        for kind in ('received','loaded'):
            self.assertEqual(200,self.request(f'/api/shipments/{sid}/events',{'kind':kind,'trip_id':tid,'location':'Kho','request_id':'event-'+kind})[0])
        detail=json.loads(self.request('/api/shipments/'+sid)[1]);self.assertIsNone(detail['position']);self.assertEqual(3,len(detail['events']))
    def test_board_lookup_scope_and_carrier(self):
        self.login()
        data={'code':'LOCAL-1','description':'Hàng','origin':'A','destination':'B','carrier':'ghn','tracking_code':'GHN-123'}
        sid=json.loads(self.request('/api/shipments',data)[1])['id']
        self.app.store.create_shipment({'id':2,'name':'Other'},{**data,'code':'PRIVATE'})
        result=json.loads(self.request('/api/lookup',{'codes':['GHN-123','PRIVATE'],'carrier':'auto'})[1])
        self.assertEqual([sid],[s['id'] for s in result['results'][0]['shipments']])
        self.assertEqual([],result['results'][1]['shipments'])
        self.assertFalse(result['carrier_api_connected'])
        wrong=json.loads(self.request('/api/lookup',{'codes':['GHN-123'],'carrier':'vnpost'})[1])
        self.assertEqual([],wrong['results'][0]['shipments'])
        board=json.loads(self.request('/api/board')[1])
        self.assertEqual([sid],[s['id'] for s in board['shipments']])
        self.assertEqual([10],[p['deviceId'] for p in board['positions']])
        self.assertEqual(400,self.request('/api/lookup',{'codes':[]})[0])

    def test_live_board_binding_and_unload(self):
        from datetime import datetime,timezone,timedelta
        self.login()
        sid=json.loads(self.request('/api/shipments',{'code':'LIVE','description':'Hàng','origin':'A','destination':'B'})[1])['id']
        tid=json.loads(self.request('/api/trips',{'code':'TRIP','device_id':10,'driver':'D','origin':'A','destination':'B'})[1])['id']
        self.request(f'/api/trips/{tid}/status',{'status':'active'})
        for kind in ('received','loaded'):
            self.request(f'/api/shipments/{sid}/events',{'kind':kind,'trip_id':tid,'location':'Kho','request_id':'live-'+kind})
        session=next(iter(self.app.sessions.values()))
        original=session['upstream'].request
        queries=[]
        def live(path,form=None,method=None):
            if path=='/api/positions':return [{'deviceId':10,'latitude':10.2,'longitude':105.9,'valid':True,'fixTime':(datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat()}]
            queries.append(path)
            return original(path,form,method)
        session['upstream'].request=live
        board=json.loads(self.request('/api/board')[1])
        self.assertEqual('vehicle_inferred',board['shipments'][0]['position']['source'])
        self.assertEqual(200,self.request('/api/route',{'device_id':10,'shipment_id':sid})[0])
        self.assertTrue(any('/api/reports/route?' in q for q in queries))
        self.request(f'/api/shipments/{sid}/events',{'kind':'unloaded','location':'Kho B','request_id':'unload-live'})
        board=json.loads(self.request('/api/board')[1])
        self.assertIsNone(board['shipments'][0]['position'])
        self.assertIsNone(board['shipments'][0]['device_id'])
        self.assertEqual(409,self.request('/api/route',{'device_id':10,'shipment_id':sid})[0])

    def test_map_assets_and_reference_isolation(self):
        for path in ('/board','/board.js','/board.css','/vendor/leaflet/leaflet.js','/logos/ghn.jpg'):
            self.assertEqual(200,self.request(path)[0],path)
        self.assertEqual(404,self.request('/reference/trackvn/saved-page.html')[0])
        self.assertEqual(404,self.request('/%2e%2e/server.py')[0])

    def test_static_and_validation(self):
        status,body,headers=self.request('/')
        self.assertEqual(200,status);self.assertIn('Vtracking',body.decode());self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.login();self.assertEqual(400,self.request('/api/shipments',[])[0]);self.assertNotEqual(200,self.request('/../server.py')[0])

if __name__=='__main__':unittest.main()
