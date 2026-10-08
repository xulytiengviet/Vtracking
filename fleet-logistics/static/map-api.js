/* One mapping engine per map: Vietflex constructors or vendored Leaflet fallback. */
'use strict';
window.TrackingMap=window.Vietflex?{
 featureGroup:(...a)=>new Vietflex.FeatureGroup(...a),layerGroup:(...a)=>new Vietflex.LayerGroup(...a),
 circleMarker:(...a)=>new Vietflex.CircleMarker(...a),circle:(...a)=>new Vietflex.Circle(...a),
 marker:(...a)=>new Vietflex.Marker(...a),polyline:(...a)=>new Vietflex.Polyline(...a),
 divIcon:(...a)=>new Vietflex.DivIcon(...a),tileLayer:(...a)=>new Vietflex.TileLayer(...a)
}:window.L;
