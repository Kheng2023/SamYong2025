// Centralized API access with minimal caching
const cache = {
  files: null,
  properties: new Map(), // key: filePath -> props array
  propValues: new Map(), // key: filePath::prop -> values array
  geojson: new Map(),    // key: filePath -> data
};

export async function fetchFiles() {
  if (cache.files) return cache.files;
  const res = await fetch('/api/files');
  if (!res.ok) throw new Error(`files HTTP ${res.status}`);
  const data = await res.json();
  cache.files = data.files;
  return cache.files;
}

export async function fetchGeoJSON(filePath) {
  if (cache.geojson.has(filePath)) return cache.geojson.get(filePath);
  // the endpoint requires directory/filename; when path is like "geojsons/file.geojson"
  const [dir, ...rest] = filePath.split('/');
  const filename = rest.join('/');
  const res = await fetch(`/api/files/${dir}/${filename}`);
  if (!res.ok) throw new Error(`geojson HTTP ${res.status}`);
  const data = await res.json();
  cache.geojson.set(filePath, data);
  return data;
}

export async function getProperties(filePath) {
  if (cache.properties.has(filePath)) return cache.properties.get(filePath);
  const res = await fetch(`/api/properties?file_path=${encodeURIComponent(filePath)}`);
  if (!res.ok) throw new Error(`properties HTTP ${res.status}`);
  const data = await res.json();
  cache.properties.set(filePath, data.properties || []);
  return data.properties || [];
}

export async function getPropertyValues(filePath, property) {
  const key = `${filePath}::${property}`;
  if (cache.propValues.has(key)) return cache.propValues.get(key);
  const res = await fetch(`/api/property-values?file_path=${encodeURIComponent(filePath)}&property=${encodeURIComponent(property)}`);
  if (!res.ok) throw new Error(`property-values HTTP ${res.status}`);
  const data = await res.json();
  cache.propValues.set(key, data.values || []);
  return data.values || [];
}

export async function processHeatmap(params) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return;
    qs.append(k, typeof v === 'string' ? v : String(v));
  });
  const res = await fetch(`/api/process?${qs.toString()}`);
  if (!res.ok) {
    let errMsg = `process HTTP ${res.status}`;
    try { const e = await res.json(); if (e?.detail) errMsg = e.detail; } catch {}
    throw new Error(errMsg);
  }
  return res.json();
}
