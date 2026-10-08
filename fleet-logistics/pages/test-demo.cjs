const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const context = {window:{}};
vm.runInNewContext(fs.readFileSync(__dirname+'/demo.js','utf8'),context);
const api = context.window.VtrackingPages.request;
(async()=>{
 assert.equal((await api('/api/me')).readonly,true);
 const board=await api('/api/board');
 assert.equal(board.shipments.length,100);
 assert.equal(board.devices.length,100);
 assert.equal(board.carrier_api_connected,false);
 assert.equal(new Set(board.shipments.map(s=>s.code)).size,100);
 assert.equal(new Set(board.positions.map(p=>p.latitude+','+p.longitude)).size,100);
 assert.ok(board.shipments.every(s=>s.position&&s.device_id));
 for(const d of board.devices){const points=await api('/api/route',{device_id:d.id});assert.equal(points.length,61);assert.ok(points.every(p=>Math.abs(p.latitude)<=90&&Math.abs(p.longitude)<=180));}
 context.window.VtrackingPages.control({paused:true});
 const stopped=JSON.stringify((await api('/api/board')).positions.map(p=>[p.latitude,p.longitude]));
 assert.equal(JSON.stringify((await api('/api/board')).positions.map(p=>[p.latitude,p.longitude])),stopped);
 assert.equal((await api('/api/lookup',{codes:board.shipments.map(s=>s.code)})).results.filter(r=>r.shipments.length===1).length,100);
 assert.ok(board.devices.every(d=>d.name.includes('mẫu')));
 assert.equal((await api('/api/lookup',{codes:['REAL-UNKNOWN'],carrier:'auto'})).results[0].shipments.length,0);
 assert.equal((await api('/api/lookup',{codes:['VT-DEMO-001'],carrier:'auto'})).results[0].shipments.length,1);
 assert.ok((await api('/api/shipments/demo-shipment-0')).events.length>0);
 await assert.rejects(()=>api('/api/shipments',{code:'write'}));
 await assert.rejects(()=>api('/api/login',{email:'private',password:'secret'}));
 console.log('PASS: read-only synthetic data, lookup, timeline, no login or writes.');
})().catch(e=>{console.error(e);process.exitCode=1;});
