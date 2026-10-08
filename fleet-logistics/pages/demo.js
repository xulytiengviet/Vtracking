/* Public Pages preview. All shipment and vehicle data below is synthetic. */
'use strict';
(()=>{
 const paths=[[[10.2548,105.9722],[10.267,106.004],[10.282,106.04],[10.306,106.089],[10.334,106.137],[10.353,106.187],[10.383,106.239]],[[10.0342,105.7883],[10.075,105.818],[10.123,105.848],[10.165,105.894],[10.204,105.931],[10.2548,105.9722]],[[10.7769,106.7009],[10.748,106.675],[10.716,106.641],[10.68,106.605],[10.644,106.56]]];
 const names=['Xe mẫu · Vĩnh Long → TP.HCM','Xe mẫu · Cần Thơ → Vĩnh Long','Xe mẫu · TP.HCM → Long An'];
 const statuses=['out_for_delivery','loaded','loaded','received','delivered','delivery_failed'];
 const carrierNames=['local','ghn','jt','vnpost','spx','lex'];
 const codes=['VT-DEMO-001','GHN-DEMO-002','JT-DEMO-003','VNPOST-DEMO-004','SPX-DEMO-005','LEX-DEMO-006'];
 let selectedTime=Date.now();
 function snapshot(){const now=Date.now();selectedTime=now;const iso=t=>new Date(t).toISOString();const tick=Math.floor(now/15000);
 const positions=paths.map((route,i)=>{const index=tick%route.length,p=route[index];return {id:i+1,deviceId:i+1,latitude:p[0],longitude:p[1],valid:true,fixTime:iso(now-(i===2?600000:0)),speed:18+i*3,accuracy:15,source:'demo'};});
 const devices=names.map((name,i)=>({id:i+1,name,status:i===2?'offline':'online'}));
 const trips=names.map((name,i)=>({id:'demo-trip-'+i,code:'DEMO-CHUYEN-00'+(i+1),device_id:i+1,driver:'Tài xế minh họa '+(i+1),origin:['Vĩnh Long','Cần Thơ','TP.HCM'][i],destination:['TP.HCM','Vĩnh Long','Long An'][i],status:'active',created_at:iso(now-3600000)}));
 const shipments=codes.map((code,i)=>{const moving=[0,1,2,5].includes(i),j=i%3;return {id:'demo-shipment-'+i,code,description:['Nông sản đóng thùng','Hàng tiêu dùng','Thiết bị điện tử','Hồ sơ chuyển phát','Đơn đã giao mẫu','Đơn giao lại mẫu'][i],carrier:carrierNames[i],tracking_code:code,origin:trips[j].origin,destination:trips[j].destination,status:statuses[i],trip_id:moving?trips[j].id:null,device_id:moving?j+1:null,position:moving?{...positions[j],source:'vehicle_inferred'}:null,source:'Dữ liệu minh họa, không phải đơn thực',lot:'DEMO',created_at:iso(now-7200000),updated_at:iso(now-60000)};});
 return {shipments,trips,devices,positions,updated_at:iso(now),carrier_api_connected:false};}
 function detail(id){const b=snapshot(),s=b.shipments.find(s=>s.id===id);if(!s)throw Error('Không tìm thấy mã minh họa.');const kinds=['created','received'];if(s.status!=='received')kinds.push('loaded');if(['out_for_delivery','delivered','delivery_failed'].includes(s.status))kinds.push('out_for_delivery');if(['delivered','delivery_failed'].includes(s.status))kinds.push(s.status);s.events=kinds.map((kind,i)=>({id:'demo-event-'+i,kind,at:new Date(selectedTime-(kinds.length-i)*600000).toISOString(),actor:'Nhân viên mẫu',location:i<2?s.origin:s.destination,note:'Sự kiện minh họa',proof:kind==='delivered'?'DEMO-POD-001':'',trip_id:s.trip_id}));return s;}
 window.VtrackingPages={async request(path,data){
  if(path==='/api/me')return {id:-1,name:'Chế độ minh họa',email:'',readonly:true};
  if(path==='/api/board')return snapshot();
  if(path==='/api/fleet'){const b=snapshot();return {devices:b.devices,positions:b.positions};}
  if(path==='/api/shipments'&&data===undefined)return snapshot().shipments;
  if(path==='/api/trips'&&data===undefined)return snapshot().trips;
  if(/^\/api\/shipments\/demo-shipment-\d+$/.test(path)&&data===undefined)return detail(path.split('/').at(-1));
  if(path==='/api/lookup'){if(!Array.isArray(data.codes)||!data.codes.length||data.codes.length>100)throw Error('Nhập từ 1 đến 100 mã minh họa.');const b=snapshot();return {source:'demo',carrier_api_connected:false,results:data.codes.map(code=>({code,shipments:b.shipments.filter(s=>s.code.toLowerCase()===code.trim().toLowerCase()&&['auto',s.carrier].includes(data.carrier||'auto'))}))};}
  if(path==='/api/route'){const index=Number(data.device_id)-1;if(!paths[index])throw Error('Không có xe mẫu này.');return paths[index].map((p,i)=>({latitude:p[0],longitude:p[1],valid:true,fixTime:new Date(Date.now()-(paths[index].length-i)*60000).toISOString()}));}
  throw Error('Bản GitHub Pages chỉ minh họa. Mở máy chủ Vtracking để đăng nhập và ghi dữ liệu thật.');
 }};
})();
