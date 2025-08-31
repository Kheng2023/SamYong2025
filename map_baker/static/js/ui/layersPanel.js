import { el } from '../utils.js';

/**
 * Render active layers list with visibility toggle and remove.
 * Expected layers is an object: { [name]: { layer: LeafletLayer, color?: string } }
 */
export function renderLayersPanel(container, layers, { onToggle, onRemove } = {}) {
  if (!container) return;
  container.innerHTML = '';
  const ul = el('ul', { className: 'layers-panel' });

  Object.entries(layers || {}).forEach(([name]) => {
    const id = `layer-${name}`;
    const displayName = name.length > 30 ? name.slice(0, 30) + '...' : name;
    const li = el('li', {},
      el('div', { className: 'layer-control' },
        el('input', { type: 'checkbox', id, checked: true }),
        el('label', { htmlFor: id, title: name }, displayName),
        el('button', { className: 'remove-layer', 'data-layer': name, type: 'button' }, '×'),
        el('input', { type: 'checkbox', className: 'aggregate-select', id: `aggregate-${name}`, 'data-layer': name }),
        el('label', { htmlFor: `aggregate-${name}`, title: 'Select for aggregation', className: 'aggregate-label' }, 'Agg')
      )
    );
    ul.append(li);
  });

  container.append(ul);

  container.addEventListener('click', (e) => {
    const btn = e.target.closest('.remove-layer');
    if (!btn || !container.contains(btn)) return;
    onRemove && onRemove(btn.dataset.layer);
  });
  container.addEventListener('change', (e) => {
    const cb = e.target.closest('input[type="checkbox"][id^="layer-"]');
    if (!cb || !container.contains(cb)) return;
    const name = cb.id.replace('layer-', '');
    onToggle && onToggle(name, cb.checked);
  });
}
