/* Public preview controls; browser location stays in this tab. */
'use strict';
let personalMarker=null,personalAccuracy=null,personalWatch=null;
const personalButton=document.querySelector('#personal-gps');
personalButton.onclick=()=>{
 if(personalWatch!==null){navigator.geolocation.clearWatch(personalWatch);personalWatch=null;if(personalMarker)boardMap.removeLayer(personalMarker);if(personalAccuracy)boardMap.removeLayer(personalAccuracy);personalMarker=null;personalAccuracy=null;personalButton.textContent='◎ Vị trí của tôi';document.querySelector('#personal-status').textContent='Đã dừng định vị thiết bị.';return;}
 if(!navigator.geolocation){notify('Trình duyệt không hỗ trợ định vị.');return;}
 if(!initMap())return;
 personalButton.disabled=true;
 personalWatch=navigator.geolocation.watchPosition(pos=>{personalButton.disabled=false;const latlng=[pos.coords.latitude,pos.coords.longitude];if(!personalMarker){personalMarker=TrackingMap.circleMarker(latlng,{radius:10,color:'#fff',weight:3,fillColor:'#366ae2',fillOpacity:1}).addTo(boardMap).bindPopup('Vị trí thiết bị của bạn — không gắn với đơn hàng mẫu');personalAccuracy=TrackingMap.circle(latlng,{radius:pos.coords.accuracy,color:'#366ae2',weight:1,fillOpacity:.08}).addTo(boardMap);boardMap.setView(latlng,15);}else{personalMarker.setLatLng(latlng);personalAccuracy.setLatLng(latlng).setRadius(pos.coords.accuracy);}personalButton.textContent='■ Dừng định vị';document.querySelector('#personal-status').textContent=`Vị trí thiết bị thật · Sai số khoảng ${Math.round(pos.coords.accuracy)} m · ${new Date(pos.timestamp).toLocaleTimeString('vi-VN')}`;},error=>{personalButton.disabled=false;if(personalWatch!==null)navigator.geolocation.clearWatch(personalWatch);personalWatch=null;notify(error.code===1?'Bạn chưa cấp quyền vị trí. Có thể bật lại trong cài đặt trình duyệt.':'Chưa lấy được vị trí: '+error.message);},{enableHighAccuracy:true,timeout:20000,maximumAge:10000});
};
window.addEventListener('pagehide',()=>{if(personalWatch!==null)navigator.geolocation.clearWatch(personalWatch);});

// Independent overview layers remain visible when a shipment is selected.
let demoRoutes=null,demoPlaces=null;
window.VtrackingPages.renderMap=shipments=>{
 if(!demoPlaces){demoPlaces=TrackingMap.layerGroup().addTo(boardMap);window.VtrackingPages.hubs.forEach(([name,lat,lng])=>TrackingMap.marker([lat,lng],{interactive:false,icon:TrackingMap.divIcon({className:'demo-place',html:esc(name),iconSize:[100,20]})}).addTo(demoPlaces));}
 if(!demoRoutes)demoRoutes=TrackingMap.layerGroup().addTo(boardMap);demoRoutes.clearLayers();
 if(!document.querySelector('#demo-routes').checked)return;
 for(const s of shipments){const i=s.device_id-1;TrackingMap.polyline(window.VtrackingPages.paths[i],{color:window.VtrackingPages.palette[i%6],weight:2,opacity:.35}).addTo(demoRoutes).bindTooltip(esc(s.code)+' · Tuyến giả định').on('click',()=>selectShipment(s.id).catch(e=>notify(e.message)));}
};
let demoPaused=false;
document.querySelector('#demo-pause').onclick=()=>{demoPaused=!demoPaused;window.VtrackingPages.control({paused:demoPaused});document.querySelector('#demo-pause').textContent=demoPaused?'▶ Tiếp tục':'Ⅱ Tạm dừng';refresh().catch(e=>notify(e.message));};
document.querySelector('#demo-speed').onchange=e=>window.VtrackingPages.control({speed:Number(e.target.value)});
document.querySelector('#demo-routes').onchange=()=>renderBoard();
document.querySelector('#demo-all').onclick=()=>{$('#lookup-reset').click();fitMap();};
document.querySelector('#demo-codes').onclick=()=>{const blob=new Blob(['Mã vận đơn\n'+window.VtrackingPages.codes.join('\n')],{type:'text/csv;charset=utf-8'});const url=URTrackingMap.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='Vtracking_100_ma_DEMO.csv';a.click();setTimeout(()=>URTrackingMap.revokeObjectURL(url),1000);};
setInterval(()=>{if(state.user&&!document.hidden&&!demoPaused)refresh().catch(e=>notify(e.message));},2000);
