// Data Upload and Processing Interface
// This module provides user-friendly interfaces for data integration

class DataUploadInterface {
    constructor(map, layers, uploadedData) {
        this.map = map;
        this.layers = layers;
        this.uploadedData = uploadedData;
        this.governmentIntegrator = new GovernmentDataIntegrator();
        this.uploadQueue = [];
        this.isProcessing = false;
        
        this.initializeInterface();
    }

    initializeInterface() {
        // Add government data integration button
        this.addGovernmentDataButton();
        
        // Add batch upload interface
        this.addBatchUploadInterface();
        
        // Add data quality indicator
        this.addDataQualityIndicator();
        
        // Add progress tracking
        this.addProgressTracker();
    }

    addGovernmentDataButton() {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;

        // Create government data section
        const govDataSection = document.createElement('div');
        govDataSection.className = 'section';
        govDataSection.innerHTML = `
            <h3>🏛️ Government Data Integration</h3>
            <div class="gov-data-sources">
                <div class="data-source-card" data-source="aemo">
                    <div class="source-header">
                        <span class="source-icon">⚡</span>
                        <span class="source-name">AEMO</span>
                        <span class="source-status" id="aemo-status">Ready</span>
                    </div>
                    <p class="source-description">Electricity grid and power generation data</p>
                    <button class="btn btn-small" onclick="dataUploadInterface.fetchGovernmentData('aemo')">
                        📊 Fetch AEMO Data
                    </button>
                </div>

                <div class="data-source-card" data-source="abs">
                    <div class="source-header">
                        <span class="source-icon">📈</span>
                        <span class="source-name">ABS Maps</span>
                        <span class="source-status" id="abs-status">Ready</span>
                    </div>
                    <p class="source-description">Population and infrastructure statistics</p>
                    <button class="btn btn-small" onclick="dataUploadInterface.fetchGovernmentData('abs')">
                        🗺️ Fetch ABS Data
                    </button>
                </div>

                <div class="data-source-card" data-source="geoscience">
                    <div class="source-header">
                        <span class="source-icon">🏔️</span>
                        <span class="source-name">Geoscience AU</span>
                        <span class="source-status" id="geoscience-status">Ready</span>
                    </div>
                    <p class="source-description">Geological and seismic hazard data</p>
                    <button class="btn btn-small" onclick="dataUploadInterface.fetchGovernmentData('geoscience')">
                        🌍 Fetch Geology Data
                    </button>
                </div>

                <div class="data-source-card" data-source="bom">
                    <div class="source-header">
                        <span class="source-icon">🌡️</span>
                        <span class="source-name">Bureau of Meteorology</span>
                        <span class="source-status" id="bom-status">Ready</span>
                    </div>
                    <p class="source-description">Weather and climate information</p>
                    <button class="btn btn-small" onclick="dataUploadInterface.fetchGovernmentData('bom')">
                        ☁️ Fetch Climate Data
                    </button>
                </div>
            </div>

            <div class="gov-data-actions">
                <button class="btn" onclick="dataUploadInterface.integrateAllGovernmentData()">
                    🔄 Integrate All Government Data
                </button>
                <button class="btn" onclick="dataUploadInterface.searchDataCatalogue()">
                    🔍 Search Data Catalogue
                </button>
            </div>
        `;

        // Insert before the first existing section
        const firstSection = sidebar.querySelector('.section');
        if (firstSection) {
            sidebar.insertBefore(govDataSection, firstSection);
        } else {
            sidebar.appendChild(govDataSection);
        }
    }

    addBatchUploadInterface() {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;

        const batchSection = document.createElement('div');
        batchSection.className = 'section';
        batchSection.innerHTML = `
            <h3>📁 Batch Data Upload</h3>
            <div class="batch-upload-area">
                <div class="upload-drop-zone" id="batch-drop-zone">
                    <div class="drop-zone-content">
                        <span class="drop-icon">📦</span>
                        <h4>Drop multiple files here</h4>
                        <p>Supports: GeoJSON, KML, CSV, ZIP archives</p>
                        <button class="btn" onclick="document.getElementById('batch-files').click()">
                            Choose Files
                        </button>
                        <input type="file" id="batch-files" multiple accept=".geojson,.kml,.csv,.json,.zip" style="display: none;">
                    </div>
                </div>
                
                <div class="upload-queue" id="upload-queue" style="display: none;">
                    <h4>Upload Queue</h4>
                    <div class="queue-items" id="queue-items"></div>
                </div>
            </div>
        `;

        sidebar.appendChild(batchSection);
        this.setupBatchUpload();
    }

    addDataQualityIndicator() {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;

        const qualitySection = document.createElement('div');
        qualitySection.className = 'section';
        qualitySection.innerHTML = `
            <h3>📊 Data Quality Overview</h3>
            <div class="data-quality-dashboard">
                <div class="quality-metric">
                    <span class="metric-label">Data Sources Active:</span>
                    <span class="metric-value" id="active-sources">0</span>
                </div>
                <div class="quality-metric">
                    <span class="metric-label">Total Records:</span>
                    <span class="metric-value" id="total-records">0</span>
                </div>
                <div class="quality-metric">
                    <span class="metric-label">Data Freshness:</span>
                    <span class="metric-value" id="data-freshness">Unknown</span>
                </div>
                <div class="quality-metric">
                    <span class="metric-label">Coverage Score:</span>
                    <span class="metric-value" id="coverage-score">0%</span>
                </div>
            </div>
            
            <div class="data-sources-status">
                <h4>Layer Status</h4>
                <div class="layer-status-list" id="layer-status-list">
                    <!-- Dynamically populated -->
                </div>
            </div>
        `;

        sidebar.appendChild(qualitySection);
        this.updateDataQualityIndicator();
    }

    addProgressTracker() {
        // Add progress overlay to the page
        const progressOverlay = document.createElement('div');
        progressOverlay.id = 'data-progress-overlay';
        progressOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 10001;
            display: none;
            align-items: center;
            justify-content: center;
        `;

        progressOverlay.innerHTML = `
            <div class="progress-container" style="background: white; padding: 30px; border-radius: 15px; text-align: center; min-width: 400px;">
                <h3 id="progress-title">Processing Data...</h3>
                <div class="progress-bar-container" style="width: 100%; height: 20px; background: #ddd; border-radius: 10px; margin: 20px 0; overflow: hidden;">
                    <div id="progress-bar" style="height: 100%; background: linear-gradient(45deg, #3498db, #2980b9); width: 0%; transition: width 0.3s;"></div>
                </div>
                <p id="progress-status">Initializing...</p>
                <div class="progress-details" id="progress-details" style="text-align: left; margin-top: 20px; font-size: 12px; max-height: 200px; overflow-y: auto;"></div>
                <button class="btn btn-danger" onclick="dataUploadInterface.cancelProcessing()" style="margin-top: 15px;">Cancel</button>
            </div>
        `;

        document.body.appendChild(progressOverlay);
    }

    setupBatchUpload() {
        const dropZone = document.getElementById('batch-drop-zone');
        const fileInput = document.getElementById('batch-files');

        // File input change handler
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelection(Array.from(e.target.files));
        });

        // Drag and drop handlers
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            this.handleFileSelection(Array.from(e.dataTransfer.files));
        });
    }

    handleFileSelection(files) {
        console.log('Files selected:', files);
        
        files.forEach((file, index) => {
            const queueItem = {
                id: Date.now() + index,
                file: file,
                name: file.name,
                size: file.size,
                type: this.detectFileType(file.name),
                status: 'queued',
                progress: 0
            };
            
            this.uploadQueue.push(queueItem);
        });

        this.updateUploadQueue();
        this.processUploadQueue();
    }

    detectFileType(filename) {
        const extension = filename.toLowerCase().split('.').pop();
        const typeMap = {
            'geojson': 'geojson',
            'json': 'geojson',
            'kml': 'kml',
            'csv': 'csv',
            'zip': 'archive'
        };

        return typeMap[extension] || 'unknown';
    }

    updateUploadQueue() {
        const queueContainer = document.getElementById('upload-queue');
        const queueItems = document.getElementById('queue-items');
        
        if (this.uploadQueue.length === 0) {
            queueContainer.style.display = 'none';
            return;
        }

        queueContainer.style.display = 'block';
        queueItems.innerHTML = '';

        this.uploadQueue.forEach(item => {
            const queueItemElement = document.createElement('div');
            queueItemElement.className = 'queue-item';
            queueItemElement.innerHTML = `
                <div class="queue-item-header">
                    <span class="file-name">${item.name}</span>
                    <span class="file-status status-${item.status}">${item.status}</span>
                </div>
                <div class="queue-item-details">
                    <span class="file-size">${this.formatFileSize(item.size)}</span>
                    <span class="file-type">${item.type}</span>
                </div>
                <div class="queue-item-progress">
                    <div class="progress-bar" style="width: ${item.progress}%"></div>
                </div>
            `;
            
            queueItems.appendChild(queueItemElement);
        });
    }

    async processUploadQueue() {
        if (this.isProcessing || this.uploadQueue.length === 0) return;

        this.isProcessing = true;
        this.showProgress('Processing Files', 'Starting file processing...');

        let processedCount = 0;
        const totalFiles = this.uploadQueue.length;

        for (const item of this.uploadQueue) {
            if (item.status === 'queued') {
                try {
                    item.status = 'processing';
                    this.updateUploadQueue();
                    this.updateProgress(processedCount / totalFiles * 100, `Processing ${item.name}...`);

                    await this.processFile(item);
                    
                    item.status = 'completed';
                    item.progress = 100;
                    processedCount++;
                    
                } catch (error) {
                    item.status = 'error';
                    item.error = error.message;
                    console.error(`Error processing ${item.name}:`, error);
                }
                
                this.updateUploadQueue();
            }
        }

        this.updateProgress(100, 'All files processed!');
        setTimeout(() => {
            this.hideProgress();
            this.isProcessing = false;
        }, 2000);

        this.updateDataQualityIndicator();
    }

    async processFile(queueItem) {
        const { file, type } = queueItem;
        
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                try {
                    let data;
                    const content = e.target.result;
                    
                    switch (type) {
                        case 'geojson':
                            data = JSON.parse(content);
                            break;
                        case 'csv':
                            data = this.parseCSV(content);
                            break;
                        case 'kml':
                            data = this.parseKML(content);
                            break;
                        default:
                            throw new Error(`Unsupported file type: ${type}`);
                    }

                    // Determine layer type from filename or content
                    const layerType = this.determineLayerType(file.name, data);
                    
                    // Add to map
                    this.addDataToMap(data, layerType);
                    
                    resolve(data);
                    
                } catch (error) {
                    reject(error);
                }
            };
            
            reader.onerror = () => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }

    parseCSV(csvText) {
        const lines = csvText.split('\n');
        const headers = lines[0].split(',').map(h => h.trim());
        const features = [];

        for (let i = 1; i < lines.length; i++) {
            if (lines[i].trim()) {
                const values = lines[i].split(',');
                const properties = {};
                headers.forEach((header, index) => {
                    properties[header] = values[index] ? values[index].trim() : '';
                });

                // Try to create a point feature if lat/lng found
                const lat = this.findLatitude(properties);
                const lng = this.findLongitude(properties);

                if (lat && lng) {
                    features.push({
                        type: "Feature",
                        geometry: {
                            type: "Point",
                            coordinates: [parseFloat(lng), parseFloat(lat)]
                        },
                        properties: properties
                    });
                }
            }
        }

        return {
            type: "FeatureCollection",
            features: features
        };
    }

    parseKML(kmlText) {
        // Basic KML parsing - in production, use a proper KML parser
        const parser = new DOMParser();
        const kmlDoc = parser.parseFromString(kmlText, 'text/xml');
        
        // This is a simplified implementation
        return {
            type: "FeatureCollection",
            features: []
        };
    }

    findLatitude(properties) {
        const latKeys = ['lat', 'latitude', 'y', 'Latitude', 'LAT', 'Lat'];
        for (const key of latKeys) {
            if (properties[key]) return properties[key];
        }
        return null;
    }

    findLongitude(properties) {
        const lngKeys = ['lng', 'lon', 'longitude', 'x', 'Longitude', 'LON', 'Lng', 'Long'];
        for (const key of lngKeys) {
            if (properties[key]) return properties[key];
        }
        return null;
    }

    determineLayerType(filename, data) {
        const name = filename.toLowerCase();
        
        if (name.includes('power') || name.includes('electric') || name.includes('energy')) {
            return 'electricity';
        }
        if (name.includes('telecom') || name.includes('fiber') || name.includes('network')) {
            return 'telecommunications';
        }
        if (name.includes('water') || name.includes('hydro')) {
            return 'water';
        }
        if (name.includes('road') || name.includes('transport') || name.includes('highway')) {
            return 'roads';
        }
        if (name.includes('climate') || name.includes('weather') || name.includes('temperature')) {
            return 'climate';
        }
        if (name.includes('geology') || name.includes('soil') || name.includes('seismic')) {
            return 'geology';
        }

        // Try to determine from data properties
        if (data.features && data.features.length > 0) {
            const properties = data.features[0].properties;
            const keys = Object.keys(properties).join(' ').toLowerCase();
            
            if (keys.includes('capacity') || keys.includes('mw') || keys.includes('voltage')) {
                return 'electricity';
            }
            if (keys.includes('bandwidth') || keys.includes('fiber') || keys.includes('latency')) {
                return 'telecommunications';
            }
        }

        return 'roads'; // Default fallback
    }

    addDataToMap(data, layerType) {
        if (typeof addGeoJSONLayer === 'function') {
            addGeoJSONLayer(data, layerType);
            this.uploadedData[layerType] = data;
        }
    }

    // Government data integration methods
    async fetchGovernmentData(source) {
        this.updateSourceStatus(source, 'loading');
        
        try {
            let data;
            
            switch (source) {
                case 'aemo':
                    data = await this.governmentIntegrator.fetchAEMOData();
                    this.addDataToMap(data, 'electricity');
                    break;
                case 'abs':
                    data = await this.governmentIntegrator.fetchABSData();
                    this.addDataToMap(data, 'roads'); // ABS infrastructure data
                    break;
                case 'geoscience':
                    data = await this.governmentIntegrator.fetchGeoscienceData();
                    this.addDataToMap(data, 'geology');
                    break;
                case 'bom':
                    data = await this.governmentIntegrator.fetchBOMData();
                    this.addDataToMap(data, 'climate');
                    break;
            }
            
            this.updateSourceStatus(source, 'success');
            this.updateDataQualityIndicator();
            
        } catch (error) {
            this.updateSourceStatus(source, 'error');
            console.error(`Error fetching ${source} data:`, error);
            alert(`Failed to fetch ${source} data: ${error.message}`);
        }
    }

    async integrateAllGovernmentData() {
        this.showProgress('Government Data Integration', 'Connecting to government data sources...');
        
        try {
            const results = await this.governmentIntegrator.integrateAllGovernmentData();
            
            // Process successful results
            results.success.forEach(result => {
                this.addDataToMap(result.data, result.type);
            });
            
            // Show results
            this.updateProgress(100, `Integration complete! Loaded ${results.metadata.totalRecords} records`);
            
            setTimeout(() => {
                this.hideProgress();
                this.showIntegrationResults(results);
            }, 2000);
            
            this.updateDataQualityIndicator();
            
        } catch (error) {
            this.hideProgress();
            console.error('Government data integration failed:', error);
            alert(`Integration failed: ${error.message}`);
        }
    }

    async searchDataCatalogue() {
        const query = prompt('Enter search terms for Australian government datasets:');
        if (!query) return;

        this.showProgress('Searching Data Catalogue', `Searching for: ${query}`);
        
        try {
            const results = await this.governmentIntegrator.searchDataCatalogue(query);
            this.hideProgress();
            this.showSearchResults(results);
            
        } catch (error) {
            this.hideProgress();
            console.error('Data catalogue search failed:', error);
            alert(`Search failed: ${error.message}`);
        }
    }

    // UI Helper Methods
    updateSourceStatus(source, status) {
        const statusElement = document.getElementById(`${source}-status`);
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `source-status status-${status}`;
        }
    }

    updateDataQualityIndicator() {
        const activeSources = Object.keys(this.uploadedData).filter(key => this.uploadedData[key]).length;
        const totalRecords = Object.values(this.uploadedData).reduce((sum, data) => {
            return sum + (data?.features?.length || 0);
        }, 0);

        document.getElementById('active-sources').textContent = activeSources;
        document.getElementById('total-records').textContent = totalRecords.toLocaleString();
        document.getElementById('data-freshness').textContent = 'Current';
        document.getElementById('coverage-score').textContent = Math.round((activeSources / 6) * 100) + '%';

        // Update layer status
        const statusList = document.getElementById('layer-status-list');
        if (statusList) {
            statusList.innerHTML = '';
            
            const layerTypes = ['electricity', 'telecommunications', 'water', 'roads', 'climate', 'geology'];
            layerTypes.forEach(type => {
                const hasData = this.uploadedData[type];
                const recordCount = hasData ? this.uploadedData[type].features?.length || 0 : 0;
                
                const statusItem = document.createElement('div');
                statusItem.className = 'layer-status-item';
                statusItem.innerHTML = `
                    <span class="layer-name">${type}</span>
                    <span class="layer-records">${recordCount} records</span>
                    <span class="layer-indicator ${hasData ? 'active' : 'inactive'}"></span>
                `;
                statusList.appendChild(statusItem);
            });
        }
    }

    showProgress(title, status) {
        const overlay = document.getElementById('data-progress-overlay');
        const titleElement = document.getElementById('progress-title');
        const statusElement = document.getElementById('progress-status');
        
        titleElement.textContent = title;
        statusElement.textContent = status;
        overlay.style.display = 'flex';
    }

    updateProgress(percentage, status, details = '') {
        const progressBar = document.getElementById('progress-bar');
        const statusElement = document.getElementById('progress-status');
        const detailsElement = document.getElementById('progress-details');
        
        progressBar.style.width = percentage + '%';
        statusElement.textContent = status;
        
        if (details) {
            detailsElement.innerHTML += `<div>${new Date().toLocaleTimeString()}: ${details}</div>`;
            detailsElement.scrollTop = detailsElement.scrollHeight;
        }
    }

    hideProgress() {
        document.getElementById('data-progress-overlay').style.display = 'none';
    }

    showIntegrationResults(results) {
        let message = `Government Data Integration Complete!\n\n`;
        message += `Total Records: ${results.metadata.totalRecords}\n`;
        message += `Processing Time: ${results.metadata.durationMs}ms\n\n`;
        message += `Successful Sources:\n`;
        
        results.success.forEach(item => {
            message += `• ${item.source}: ${item.recordCount} records\n`;
        });
        
        if (results.errors.length > 0) {
            message += `\nErrors:\n`;
            results.errors.forEach(error => {
                message += `• ${error.source}: ${error.error}\n`;
            });
        }
        
        alert(message);
    }

    showSearchResults(results) {
        let message = `Data Catalogue Search Results\n\n`;
        message += `Found ${results.result.count} datasets:\n\n`;
        
        results.result.results.forEach((dataset, index) => {
            message += `${index + 1}. ${dataset.title}\n`;
            message += `   Organization: ${dataset.organization.title}\n`;
            message += `   Formats: ${dataset.resources.map(r => r.format).join(', ')}\n\n`;
        });
        
        alert(message);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    cancelProcessing() {
        this.isProcessing = false;
        this.hideProgress();
        this.uploadQueue = [];
        this.updateUploadQueue();
    }
}

// Add CSS styles for the data upload interface
const dataUploadStyles = document.createElement('style');
dataUploadStyles.textContent = `
    .data-source-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid #ddd;
        transition: all 0.3s ease;
    }

    .data-source-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }

    .source-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }

    .source-icon {
        font-size: 18px;
        margin-right: 8px;
    }

    .source-name {
        font-weight: bold;
        flex: 1;
    }

    .source-status {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
        text-transform: uppercase;
    }

    .status-ready { background: #e8f5e8; color: #2d5a2d; }
    .status-loading { background: #fff3cd; color: #856404; }
    .status-success { background: #d4edda; color: #155724; }
    .status-error { background: #f8d7da; color: #721c24; }

    .source-description {
        font-size: 12px;
        color: #666;
        margin-bottom: 10px;
    }

    .btn-small {
        padding: 5px 10px;
        font-size: 12px;
    }

    .gov-data-actions {
        margin-top: 15px;
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }

    .batch-upload-area {
        margin-bottom: 20px;
    }

    .upload-drop-zone {
        border: 2px dashed #3498db;
        border-radius: 10px;
        padding: 30px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
    }

    .upload-drop-zone:hover,
    .upload-drop-zone.dragover {
        border-color: #2980b9;
        background-color: rgba(52, 152, 219, 0.1);
    }

    .drop-zone-content h4 {
        margin: 10px 0;
        color: #2c3e50;
    }

    .drop-zone-content p {
        color: #7f8c8d;
        margin-bottom: 15px;
    }

    .drop-icon {
        font-size: 48px;
        color: #3498db;
        display: block;
        margin-bottom: 10px;
    }

    .upload-queue {
        margin-top: 20px;
        background: rgba(255, 255, 255, 0.8);
        border-radius: 8px;
        padding: 15px;
    }

    .queue-item {
        background: white;
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #eee;
    }

    .queue-item-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }

    .file-name {
        font-weight: bold;
        color: #2c3e50;
    }

    .file-status {
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 10px;
        text-transform: uppercase;
    }

    .status-queued { background: #f8f9fa; color: #6c757d; }
    .status-processing { background: #fff3cd; color: #856404; }
    .status-completed { background: #d4edda; color: #155724; }

    .queue-item-details {
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: #666;
        margin-bottom: 8px;
    }

    .queue-item-progress {
        height: 4px;
        background: #eee;
        border-radius: 2px;
        overflow: hidden;
    }

    .queue-item-progress .progress-bar {
        height: 100%;
        background: linear-gradient(45deg, #3498db, #2980b9);
        transition: width 0.3s ease;
    }

    .data-quality-dashboard {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }

    .quality-metric {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        padding: 5px 0;
        border-bottom: 1px solid #eee;
    }

    .quality-metric:last-child {
        border-bottom: none;
        margin-bottom: 0;
    }

    .metric-label {
        font-size: 12px;
        color: #666;
    }

    .metric-value {
        font-weight: bold;
        color: #2c3e50;
    }

    .data-sources-status {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 8px;
        padding: 15px;
    }

    .layer-status-list {
        margin-top: 10px;
    }

    .layer-status-item {
        display: flex;
        align-items: center;
        padding: 5px 0;
        border-bottom: 1px solid #eee;
    }

    .layer-status-item:last-child {
        border-bottom: none;
    }

    .layer-name {
        flex: 1;
        font-size: 12px;
        text-transform: capitalize;
    }

    .layer-records {
        font-size: 11px;
        color: #666;
        margin-right: 10px;
    }

    .layer-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }

    .layer-indicator.active {
        background: #27ae60;
    }

    .layer-indicator.inactive {
        background: #e74c3c;
    }
`;

document.head.appendChild(dataUploadStyles);

// Initialize the data upload interface when the page loads
let dataUploadInterface;

function initializeDataUploadInterface() {
    if (typeof map !== 'undefined' && typeof layers !== 'undefined' && typeof uploadedData !== 'undefined') {
        dataUploadInterface = new DataUploadInterface(map, layers, uploadedData);
        window.dataUploadInterface = dataUploadInterface;
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(initializeDataUploadInterface, 1000); // Wait for other scripts to load
    });
} else {
    setTimeout(initializeDataUploadInterface, 1000);
}

// Export for global access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataUploadInterface;
} else {
    window.DataUploadInterface = DataUploadInterface;
}
