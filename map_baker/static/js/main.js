// Minimal bootstrap to gradually migrate inline script
import * as Utils from './utils.js';
import * as Api from './api.js';
import * as MapMod from './map.js';
import { renderFilesPanel } from './ui/filesPanel.js';
import { renderLayersPanel } from './ui/layersPanel.js';

// Expose some parts globally to aid gradual migration without breaking inline script
window.AppModules = { Utils, Api, MapMod, UI: { renderFilesPanel, renderLayersPanel } };
console.debug('Main module loaded. Modules available as window.AppModules');