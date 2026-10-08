/* Public preview controls; browser location stays in this tab. */
'use strict';
let personalMarker=null,personalAccuracy=null,personalWatch=null;
const personalButton=document.querySelector('#personal-gps');
personalButton.onclick=()=>{
 if(personalWatch!==null){navigator.geolocation.clearWatch(personalWatch);personalWatch=null;if(personalMarker)boardMap.removeLayer(personalMarker);if(personalAccuracy)boardMap.removeLayer(personalAccuracy);personalMarker=null;personalAccuracy=null;personalButton.textContent='◎ Vị trí của tôi';document.querySelector('#personal-status').textContent='Đã dừng định vị thiết bị.';return;}
 if(!navigator.geolocation){notify('Trình duyệt không hỗ trợ định vị.');return;}
 if(!initMap())return;
 personalButton.disabled=true;
 personalWatch=navigator.geolocation.watchPosition(pos=>{personalButton.disabled=false;const latlng=[pos.coords.latitude,pos.coords.longitude];if(!personalMarker){personalMarker=L.circleMarker(latlng,{radius:10,color:'#fff',weight:3,fillColor:'#366ae2',fillOpacity:1}).addTo(boardMap).bindPopup('Vị trí thiết bị của bạn — không gắn với đơn hàng mẫu');personalAccuracy=L.circle(latlng,{radius:pos.coords.accuracy,color:'#366ae2',weight:1,fillOpacity:.08}).addTo(boardMap);boardMap.setView(latlng,15);}else{personalMarker.setLatLng(latlng);personalAccuracy.setLatLng(latlng).setRadius(pos.coords.accuracy);}personalButton.textContent='■ Dừng định vị';document.querySelector('#personal-status').textContent=`Vị trí thiết bị thật · Sai số khoảng ${Math.round(pos.coords.accuracy)} m · ${new Date(pos.timestamp).toLocaleTimeString('vi-VN')}`;},error=>{personalButton.disabled=false;if(personalWatch!==null)navigator.geolocation.clearWatch(personalWatch);personalWatch=null;notify(error.code===1?'Bạn chưa cấp quyền vị trí. Có thể bật lại trong cài đặt trình duyệt.':'Chưa lấy được vị trí: '+error.message);},{enableHighAccuracy:true,timeout:20000,maximumAge:10000});
};
window.addEventListener('pagehide',()=>{if(personalWatch!==null)navigator.geolocation.clearWatch(personalWatch);});
document.querySelector('#open-live').onclick=()=>document.querySelector('#live-dialog').showModal();
document.querySelector('#live-close').onclick=()=>document.querySelector('#live-dialog').close();
document.querySelector('#live-form').onsubmit=e=>{e.preventDefault();try{const url=new URL(document.querySelector('#live-url').value);if(url.protocol!=='https:'||url.username||url.password)throw Error('Hãy nhập địa chỉ HTTPS của máy chủ Vtracking, không chứa tài khoản/mật khẩu.');window.open(url.href,'_blank','noopener,noreferrer');document.querySelector('#live-dialog').close();}catch(error){notify(error.message);}};
