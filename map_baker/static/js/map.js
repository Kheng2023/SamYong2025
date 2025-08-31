// Map utilities skeleton for migration
export function initMap(elId) {
  const map = L.map(elId).setView([-30, 135], 4);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  return map;
}

export function colorFromName(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  const hue = Math.abs(h) % 360;
  return `hsl(${hue} 70% 50%)`;
}

export function gradient(value) {
  const v = Math.max(0, Math.min(1, value || 0));
  const stops = [
    { v: 0, c: [0,0,255] },
    { v: 0.5, c: [0,255,0] },
    { v: 1, c: [255,0,0] }
  ];
  let a=stops[0], b=stops[stops.length-1];
  for (let i=0;i<stops.length-1;i++){
    if (v>=stops[i].v && v<=stops[i+1].v){ a=stops[i]; b=stops[i+1]; break; }
  }
  const t = (v - a.v) / (b.v - a.v || 1);
  const r = Math.round(a.c[0] + t*(b.c[0]-a.c[0]));
  const g = Math.round(a.c[1] + t*(b.c[1]-a.c[1]));
  const bch = Math.round(a.c[2] + t*(b.c[2]-a.c[2]));
  const toHex = (n)=>('#'+[r,g,bch].map(x=>{const h=x.toString(16); return h.length===1?'0'+h:h;}).join(''));
  return toHex();
}

export function addGeoJsonLayer(map, name, data) {
  // Treat any layer as heatmap by default
  const feats = data.features || [];
  const maxValue = Math.max(1, ...feats.map(f => (f.properties && (f.properties.value || 0)) || 0));

  const layer = L.geoJSON(data, {
    style: f => {
      const v = (f.properties && (f.properties.value || 0)) || 0;
      const t = maxValue ? v / maxValue : 0;
      return { color:'#000', weight:1, opacity:1, fillOpacity: Math.max(0.3, t*0.7+0.3), fillColor: gradient(t) };
    },
    pointToLayer: (f, latlng) => {
      const v = (f.properties && (f.properties.value || 0)) || 0;
      const t = maxValue ? v / maxValue : 0;
      const r = Math.max(3, t*15);
      return L.circleMarker(latlng, { radius:r, fillColor:gradient(t), color:'#000', weight:1, opacity:1, fillOpacity:0.8 });
    }
  });
  return layer;
}
