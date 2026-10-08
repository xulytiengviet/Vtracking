/* Vtracking TrackVN integration. SPDX-License-Identifier: Apache-2.0 */
'use strict';
const carriers={local:'Vtracking nội bộ',ghn:'GHN',jt:'J&T Express',spx:'Shopee Express',vnpost:'VNPost',futa:'Futa',lex:'LEX VN'};
let boardMap=null, markerLayer=null, routeLayer=null, selectedShipment=null, lookupIds=null, fitted=false, selectionSequence=0;
function carrierFields(){return `<label>Nhà vận chuyển<select name="carrier">${Object.entries(carriers).map(([key,name])=>`<option value="${key}">${esc(name)}</option>`).join('')}</select></label>${input('tracking_code','Mã vận đơn của hãng (nếu có)',false)}`;}
function setBoardVisibility(){const board=state.tab==='board';$('#tracking-board').hidden=!board;$('#management-intro').hidden=board;$('#management-list').hidden=board;if(board&&boardMap)setTimeout(()=>boardMap.invalidateSize(),0);}
function clearBoard(){selectedShipment=null;lookupIds=null;selectionSequence++;markerLayer?.clearLayers();routeLayer?.clearLayers();$('#parcel-list').replaceChildren();$('#tracking-detail').replaceChildren();$('#lookup-codes').value='';$('#lookup-carrier').value='auto';$('#lookup-result').textContent='Dữ liệu từ hệ thống Vtracking của bạn.';fitted=false;}
function validPoint(p){return p&&Number.isFinite(p.latitude)&&Number.isFinite(p.longitude)&&Math.abs(p.latitude)<=90&&Math.abs(p.longitude)<=180;}
function recent(p){const age=Date.now()-Date.parse(p.fixTime);return p.valid&&Number.isFinite(age)&&age>=-60000&&age<=120000;}
function initMap(){if(boardMap)return true;if(!window.TrackingMap){$('#map-health').textContent='Không tải được thư viện bản đồ. Danh sách và lịch sử vẫn dùng được.';return false;}
 const useVietflex=!!window.Vietflex;
 boardMap=useVietflex?Vietflex.vietflexMap('live-map',{useLegacyGoogleTiles:true,googleMapType:'roadmap',zoomControl:false,attributionControl:false}):L.map('live-map',{center:[15.8,107.6],zoom:5,zoomControl:true});
 if(useVietflex){new Vietflex.ZoomControl({position:'topleft'}).addTo(boardMap);new Vietflex.AttributionControl({position:'bottomright'}).addTo(boardMap);}

 const tileSources={osm:['https://tile.openstreetmap.org/{z}/{x}/{y}.png','&copy; OpenStreetMap contributors'],hot:['https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png','&copy; OpenStreetMap contributors Tiles &copy; HOT / OpenStreetMap France (CC BY-SA)']};
 let base=boardMap.baseLayer||null,failures=0,switched=false,tileTimer;
 const toolbar=document.querySelector('.map-toolbar');
 const chooser=document.createElement('select');chooser.id='map-source';chooser.setAttribute('aria-label','Nền bản đồ');chooser.innerHTML=(useVietflex?'<option value="google">Vietflex · Đường phố</option><option value="satellite">Vietflex · Vệ tinh</option>':'')+'<option value="osm">OpenStreetMap</option><option value="hot">OSM Humanitaire</option><option value="none">Chỉ điểm / tuyến</option>';toolbar.appendChild(chooser);
 const health=document.createElement('p');health.id='tile-health';health.setAttribute('role','status');document.querySelector('#live-map').after(health);
 function switchBase(key,automatic=false){clearTimeout(tileTimer);if(base)boardMap.removeLayer(base);base=null;failures=0;chooser.value=key;
  if(key==='none'){health.textContent='Đang xem điểm / tuyến không có nền đường phố.';return;}
  health.textContent='Đang tải nền '+({google:'Vietflex · Đường phố',satellite:'Vietflex · Vệ tinh',osm:'OpenStreetMap',hot:'OSM Humanitaire'}[key])+'…';
  const layer=['google','satellite'].includes(key)?Vietflex.legacyGoogleTiles({mapType:key==='google'?'roadmap':'hybrid'}):TrackingMap.tileLayer(tileSources[key][0],{maxZoom:19,attribution:tileSources[key][1]});base=layer;
  const fallback=()=>{if(base!==layer)return;if(['google','satellite'].includes(key)){switchBase('osm',true);}else if(key==='osm'&&!switched){switched=true;switchBase('hot',true);}else health.textContent='Chưa tải được nền bản đồ qua mạng. Bạn vẫn xem được điểm, tuyến; thử đổi nguồn nền.';};
  layer.on('tileload',()=>{if(base!==layer)return;clearTimeout(tileTimer);health.textContent=(automatic?'Đã chuyển nền dự phòng · ':'')+({google:'Vietflex · Đường phố',satellite:'Vietflex · Vệ tinh',osm:'OpenStreetMap',hot:'OSM Humanitaire'}[key]);});
  layer.on('tileerror',()=>{if(base===layer&&++failures>=3)fallback();});layer.addTo(boardMap);tileTimer=setTimeout(fallback,10000);
 }
 chooser.onchange=()=>{switched=false;switchBase(chooser.value);};switchBase(useVietflex?'google':'osm');
 markerLayer=TrackingMap.featureGroup().addTo(boardMap);routeLayer=TrackingMap.featureGroup().addTo(boardMap);return true;
}
function visibleShipments(){const status=$('#board-status').value;return state.shipments.filter(s=>(lookupIds===null||lookupIds.has(s.id))&&(status==='all'||(status==='moving'?['loaded','out_for_delivery','delivery_failed'].includes(s.status):s.status===status)));}
function renderBoard(){setBoardVisibility();const shipments=visibleShipments();$('#board-count').textContent=shipments.length;$('#board-updated').textContent=`Đồng bộ: ${date(state.updated_at)} · ${window.VtrackingPages?'Mô phỏng cập nhật 2 giây':'Tự cập nhật 15 giây'}`;
 $('#parcel-list').innerHTML=shipments.length?shipments.map(s=>`<button class="parcel ${s.id===selectedShipment?'active':''}" data-shipment="${s.id}"><strong>${esc(s.code)}</strong>${pill(s.status)}<p>${esc(s.description)}</p><p>${esc(carriers[s.carrier]||s.carrier)}${s.tracking_code?' · '+esc(s.tracking_code):''}</p><small>${esc(s.origin)} → ${esc(s.destination)}</small><small>${s.position?esc(positionStatus(s.position))+' · suy ra từ xe':'Chưa có GPS gắn với kiện'}</small></button>`).join(''):'<div class="empty">Không có đơn phù hợp.<br>Vào mục Kiện hàng để tạo và gắn với chuyến.</div>';
 if(selectedShipment&&!shipments.some(s=>s.id===selectedShipment)){selectedShipment=null;selectionSequence++;routeLayer?.clearLayers();$('#tracking-detail').innerHTML='<div class="empty">Chọn đơn hàng để xem chi tiết.</div>';}
 if(!initMap())return;markerLayer.clearLayers();const groups=new Map();for(const s of shipments){if(validPoint(s.position)){const key=s.device_id;const group=groups.get(key)||{p:s.position,shipments:[]};group.shipments.push(s);groups.set(key,group);}}
 let displayed=0;const fleet=$('#show-fleet').checked;
 for(const device of state.fleet.devices){const group=groups.get(device.id);const p=group?.p||(fleet?state.fleet.positions.find(p=>p.deviceId===device.id):null);if(!validPoint(p))continue;displayed++;
 const selected=group?.shipments.some(s=>s.id===selectedShipment);const color=recent(p)?'#148b7f':'#af7c35';
 const marker=TrackingMap.circleMarker([p.latitude,p.longitude],{radius:selected?12:8,color:selected?'#1d405f':'#fff',weight:selected?3:2,fillColor:color,fillOpacity:.95}).addTo(markerLayer);
 marker.bindPopup(`<div class="map-popup"><strong>${esc(device.name)}</strong>${esc(positionStatus(p))}<br>${esc(date(p.fixTime))}<br>${group?group.shipments.map(s=>esc(s.code)).join(', ')+'<br>Vị trí kiện suy ra từ xe':'GPS phương tiện'}</div>`);
 marker.on('click',()=>{if(group?.shipments.length)selectShipment(group.shipments[0].id,true).catch(e=>notify(e.message));});
 }
 if(window.VtrackingPages?.renderMap)window.VtrackingPages.renderMap(shipments);
 $('#map-health').textContent=`${displayed} phương tiện có tọa độ · ${shipments.filter(s=>validPoint(s.position)).length}/${shipments.length} đơn có GPS suy ra · ${fleet?'Đang hiện cả đội xe':'Chỉ hiện xe gắn với đơn đã lọc'}`;
 if(!fitted&&displayed){fitMap();fitted=true;}setTimeout(()=>boardMap.invalidateSize(),0);
 if(selectedShipment)selectShipment(selectedShipment,false).catch(e=>notify(e.message));
}
function fitMap(){if(markerLayer?.getLayers().length)boardMap.fitBounds(markerLayer.getBounds().pad(.2),{maxZoom:14});else boardMap?.setView([15.8,107.6],5);}
async function selectShipment(id,focus=true){selectedShipment=id;const sequence=++selectionSequence;document.querySelectorAll('[data-shipment]').forEach(e=>e.classList.toggle('active',e.dataset.shipment===id));
 const s=await api('/api/shipments/'+id);if(sequence!==selectionSequence||!state.user)return;const row=state.shipments.find(x=>x.id===id);const p=s.position;routeLayer?.clearLayers();
 $('#tracking-detail').innerHTML=`<p class="eyebrow">HÀNH TRÌNH ĐƠN HÀNG</p><h3>${esc(s.code)}</h3>${pill(s.status)}<p>${esc(s.description)}</p><p>${esc(carriers[s.carrier]||s.carrier)}<br>${esc(s.tracking_code||'Chưa gắn mã vận đơn hãng')}</p><p>${p?`GPS suy ra từ xe<br>${esc(positionStatus(p))}<br>${esc(date(p.fixTime))}<br>${esc(p.latitude)}, ${esc(p.longitude)}`:'Chưa có GPS của kiện. Địa điểm dưới đây là thông tin bàn giao đã ghi nhận.'}</p><button id="board-manage" class="primary">Chi tiết / Bàn giao</button><ol class="timeline">${s.events.map(e=>`<li><strong>${esc(labels[e.kind]||e.kind)}</strong><p>${date(e.at)}</p><p>${esc(e.location)}</p><p>${esc(e.note)}${e.proof?' · '+esc(e.proof):''}</p></li>`).join('')}</ol><p id="board-route-note">${row?.device_id?'Đang lấy hành trình GPS của chặng hiện tại…':'Không có chặng GPS đang hoạt động.'}</p>`;
 $('#board-manage').onclick=()=>detail(id).catch(e=>notify(e.message));
 if(focus&&validPoint(p)&&boardMap)boardMap.setView([p.latitude,p.longitude],14);
 if(!row?.device_id||!boardMap)return;
 try{const route=await api('/api/route',{device_id:row.device_id,shipment_id:id});if(sequence!==selectionSequence||!state.user)return;let segment=[],previous=null,count=0;
 const draw=()=>{if(segment.length>1)TrackingMap.polyline(segment,{color:'#0067d9',weight:5,opacity:1}).addTo(routeLayer);segment=[];};
 for(const point of route){if(!point.valid||!validPoint(point)){draw();previous=null;continue;}const ts=Date.parse(point.fixTime);if(!Number.isFinite(ts)){draw();previous=null;continue;}if(previous!==null&&(ts<previous||ts-previous>300000))draw();segment.push([point.latitude,point.longitude]);previous=ts;count++;}draw();
 if(focus&&routeLayer.getLayers().length)boardMap.fitBounds(routeLayer.getBounds().pad(.15),{maxZoom:13});
 $('#board-route-note').textContent=`${count} điểm GPS của chặng gắn kiện, tối đa 24 giờ. Khoảng mất tín hiệu trên 5 phút được ngắt đoạn.`;
 }catch(error){if(sequence===selectionSequence&&$('#board-route-note'))$('#board-route-note').textContent=error.message;}
}
$('#parcel-list').onclick=e=>{const b=e.target.closest('[data-shipment]');if(b)selectShipment(b.dataset.shipment).catch(e=>notify(e.message));};
$('#lookup-form').onsubmit=async e=>{e.preventDefault();const codes=$('#lookup-codes').value.split(/[\n,;]+/).map(s=>s.trim()).filter(Boolean);if(!codes.length){lookupIds=null;renderBoard();return;}const button=e.target.querySelector('button');button.disabled=true;try{const result=await api('/api/lookup',{codes,carrier:$('#lookup-carrier').value});lookupIds=new Set(result.results.flatMap(r=>r.shipments.map(s=>s.id)));const missing=result.results.filter(r=>!r.shipments.length).map(r=>r.code);$('#lookup-result').textContent=`Tìm thấy ${lookupIds.size} kiện trong Vtracking.${missing.length?' Chưa có dữ liệu: '+missing.join(', ')+'.':''} Chưa kết nối API tra cứu trực tiếp của hãng.`;renderBoard();}catch(error){notify(error.message);}finally{button.disabled=false;}};
$('#lookup-reset').onclick=()=>{lookupIds=null;$('#lookup-codes').value='';$('#lookup-carrier').value='auto';$('#board-status').value='all';$('#lookup-result').textContent='Đang hiển thị toàn bộ kiện thuộc tài khoản hiện tại.';renderBoard();};
$('#board-status').onchange=()=>renderBoard();$('#show-fleet').onchange=()=>renderBoard();$('#map-fit').onclick=fitMap;$('#board-refresh').onclick=()=>refresh().catch(e=>notify(e.message));
$('#theme').onclick=()=>{document.documentElement.classList.toggle('dark');try{localStorage.setItem('vtracking-theme',document.documentElement.classList.contains('dark')?'dark':'light');}catch{}setTimeout(()=>boardMap?.invalidateSize(),0);};
try{if(localStorage.getItem('vtracking-theme')==='dark')document.documentElement.classList.add('dark');}catch{}

setInterval(()=>{if(state.user&&!document.hidden)refresh().catch(e=>notify(e.message));},15000);
api('/api/me').then(async u=>{showWorkspace(u);await refresh();}).catch(()=>showLogin());

function setBoardView(view){document.querySelector('.tracking-grid').dataset.view=view;document.querySelectorAll('[data-view]').forEach(b=>{if(b.tagName==='BUTTON')b.setAttribute('aria-pressed',String(b.dataset.view===view));});setTimeout(()=>boardMap?.invalidateSize(),0);}
document.querySelector('.board-views').onclick=e=>{if(e.target.dataset.view)setBoardView(e.target.dataset.view);};
$('#map-expand').onclick=()=>{const expanded=document.querySelector('.tracking-grid').classList.toggle('map-expanded');$('#map-expand').setAttribute('aria-pressed',String(expanded));$('#map-expand').textContent=expanded?'⛶ Thu gọn':'⛶ Mở rộng';boardMap?.invalidateSize();};
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.querySelector('.map-expanded'))$('#map-expand').click();});
window.addEventListener('resize',()=>boardMap?.invalidateSize());
