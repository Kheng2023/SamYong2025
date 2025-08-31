import { el, formatFileSize } from '../utils.js';

/**
 * Render the files panel into container.
 * @param {HTMLElement} container
 * @param {Array} files - list from /api/files
 * @param {(file:object)=>void} onFileSelect - callback when a file is clicked
 */
export function renderFilesPanel(container, files, onFileSelect) {
  if (!container) return;
  if (!files || files.length === 0) {
    container.textContent = 'No GeoJSON files found.';
    return;
  }
  // Group by directory
  const byDir = new Map();
  files.forEach(f => {
    if (!byDir.has(f.directory)) byDir.set(f.directory, []);
    byDir.get(f.directory).push(f);
  });

  const frag = document.createDocumentFragment();
  for (const [dir, list] of byDir.entries()) {
    frag.appendChild(el('h3', {}, dir));
    const ul = el('ul', { className: 'files__list', 'data-dir': dir });
    list.forEach(file => {
      const btn = el('button', {
        className: 'file-item',
        'data-path': file.path,
        'data-name': file.name,
        'data-dir': file.directory,
        type: 'button',
        title: `${file.name} (${file.directory})`
      }, `${file.name} (${formatFileSize(file.size)})`);
      ul.append(el('li', {}, btn));
    });
    frag.appendChild(ul);
  }
  container.innerHTML = '';
  container.appendChild(frag);

  // Delegated click
  container.addEventListener('click', (e) => {
    const btn = e.target.closest('.file-item');
    if (!btn || !container.contains(btn)) return;
    const file = {
      path: btn.dataset.path,
      name: btn.dataset.name,
      directory: btn.dataset.dir
    };
    onFileSelect && onFileSelect(file);
  });
}
