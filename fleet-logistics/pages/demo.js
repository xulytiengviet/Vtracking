/* Public Pages preview. All shipment and vehicle data below is synthetic. */
'use strict';
(()=>{
 const hubs=[['Vĩnh Long',10.2548,105.9722],['Cần Thơ',10.0342,105.7883],['TP.HCM',10.7769,106.7009],['Mỹ Tho',10.3600,106.3600],['Bến Tre',10.2434,106.3756],['Trà Vinh',9.9347,106.3453],['Sa Đéc',10.2908,105.7565],['Cao Lãnh',10.4550,105.6340],['Long Xuyên',10.3864,105.4352],['Sóc Trăng',9.6025,105.9739]];
 const palette=['#087f8c','#de7043','#6764c2','#239361','#bb4585','#977022'];
 const carrierNames=['local','ghn','jt','vnpost','spx','lex'];
 const prefixes=['VT','GHN','JT','VNPOST','SPX','LEX'];
 const codes=Array.from({length:100},(_,i)=>prefixes[i%6]+'-DEMO-'+String(i+1).padStart(3,'0'));
 const paths=codes.map((_,i)=>{const a=hubs[i%10],b=hubs[(i%10+1+Math.floor(i/10)%9)%10];return Array.from({length:61},(_,k)=>{const t=k/60,bend=Math.sin(Math.PI*t)*((i%5)-2)*.012;return [a[1]+(b[1]-a[1])*t+bend,a[2]+(b[2]-a[2])*t-bend];});});
 let selectedTime=Date.now(),elapsed=0,lastTick=Date.now(),paused=false,speed=1;
 function clock(){const now=Date.now();if(!paused)elapsed+=(now-lastTick)*speed;lastTick=now;return elapsed;}
 function snapshot(){const now=Date.now();selectedTime=now;const iso=t=>new Date(t).toISOString();const tick=clock()/1800;
 const positions=paths.map((route,i)=>{const progress=(tick+i*.59)%60,index=Math.floor(progress),t=progress-index,p=route[index],q=route[index+1];return {id:i+1,deviceId:i+1,latitude:p[0]+(q[0]-p[0])*t,longitude:p[1]+(q[1]-p[1])*t,valid:true,fixTime:iso(now),speed:paused?0:18+i%20,accuracy:15,source:'demo'};});
 const devices=codes.map((_,i)=>({id:i+1,name:'Xe mẫu '+String(i+1).padStart(3,'0'),status:'online'}));
 const trips=codes.map((_,i)=>({id:'demo-trip-'+i,code:'DEMO-CHUYEN-'+String(i+1).padStart(3,'0'),device_id:i+1,driver:'Tài xế minh họa '+(i+1),origin:hubs[i%10][0],destination:hubs[(i%10+1+Math.floor(i/10)%9)%10][0],status:'active',created_at:iso(now-3600000)}));
 const shipments=codes.map((code,i)=>({id:'demo-shipment-'+i,code,description:['Nông sản đóng thùng','Hàng tiêu dùng','Thiết bị điện tử','Hồ sơ chuyển phát'][i%4],carrier:carrierNames[i%6],tracking_code:code,origin:trips[i].origin,destination:trips[i].destination,status:i%2?'loaded':'out_for_delivery',trip_id:trips[i].id,device_id:i+1,position:{...positions[i],source:'vehicle_inferred'},source:'Dữ liệu minh họa, không phải đơn thực',lot:'DEMO',created_at:iso(now-7200000),updated_at:iso(now)}));
 return {shipments,trips,devices,positions,updated_at:iso(now),carrier_api_connected:false};}
 function detail(id){const b=snapshot(),s=b.shipments.find(s=>s.id===id);if(!s)throw Error('Không tìm thấy mã minh họa.');const kinds=['created','received'];if(s.status!=='received')kinds.push('loaded');if(['out_for_delivery','delivered','delivery_failed'].includes(s.status))kinds.push('out_for_delivery');if(['delivered','delivery_failed'].includes(s.status))kinds.push(s.status);s.events=kinds.map((kind,i)=>({id:'demo-event-'+i,kind,at:new Date(selectedTime-(kinds.length-i)*600000).toISOString(),actor:'Nhân viên mẫu',location:i<2?s.origin:s.destination,note:'Sự kiện minh họa',proof:kind==='delivered'?'DEMO-POD-001':'',trip_id:s.trip_id}));return s;}
 window.VtrackingPages={hubs,paths,palette,codes,control(options){clock();if(typeof options.paused==='boolean')paused=options.paused;if([1,3,10].includes(options.speed))speed=options.speed;return {paused,speed};},async request(path,data){
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
