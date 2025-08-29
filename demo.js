// Demo script for showcasing the Data Center Analysis Platform
// This provides guided demo functionality

class PlatformDemo {
    constructor() {
        this.currentStep = 0;
        this.steps = [
            {
                title: "Welcome to the Data Center Analysis Platform",
                description: "This platform helps you find optimal locations for data centers across Australia using government datasets.",
                action: "highlight-title",
            },
            {
                title: "Step 1: Load Infrastructure Data",
                description: "We'll start by loading sample Australian infrastructure data including power, telecommunications, and transport networks.",
                action: "load-sample-data",
            },
            {
                title: "Step 2: Configure Analysis Parameters",
                description: "Adjust the importance weights for different factors like power infrastructure (25%), telecommunications (20%), etc.",
                action: "highlight-parameters",
            },
            {
                title: "Step 3: Run Advanced Analysis",
                description: "Execute the multi-criteria analysis algorithm to evaluate all possible locations.",
                action: "run-analysis",
            },
            {
                title: "Step 4: View Results",
                description: "See the color-coded suitability map and identify the top 5 optimal locations.",
                action: "show-results",
            },
            {
                title: "Step 5: Detailed Site Information",
                description: "Click on any location to see detailed analysis including scores for each factor and risk assessment.",
                action: "show-popup",
            },
            {
                title: "Step 6: Generate Reports",
                description: "Download comprehensive reports for decision-making and stakeholder communication.",
                action: "generate-report",
            },
            {
                title: "Demo Complete!",
                description: "You can now explore the platform independently. Try uploading your own data or adjusting parameters.",
                action: "demo-complete",
            }
        ];
        this.isRunning = false;
    }

    startDemo() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.currentStep = 0;
        this.showDemoOverlay();
        this.runStep();
    }

    showDemoOverlay() {
        // Create demo overlay
        const overlay = document.createElement('div');
        overlay.id = 'demo-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        const demoBox = document.createElement('div');
        demoBox.id = 'demo-box';
        demoBox.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 15px;
            max-width: 500px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        `;

        demoBox.innerHTML = `
            <h3 id="demo-title">Demo Loading...</h3>
            <p id="demo-description">Please wait...</p>
            <div style="margin-top: 20px;">
                <button id="demo-skip" class="btn btn-danger">Skip Demo</button>
                <button id="demo-next" class="btn" style="margin-left: 10px;">Next</button>
            </div>
            <div style="margin-top: 15px;">
                <div id="demo-progress" style="width: 100%; height: 4px; background: #ddd; border-radius: 2px;">
                    <div id="demo-progress-bar" style="width: 0%; height: 100%; background: #3498db; border-radius: 2px; transition: width 0.3s;"></div>
                </div>
                <small id="demo-step-info">Step 1 of ${this.steps.length}</small>
            </div>
        `;

        overlay.appendChild(demoBox);
        document.body.appendChild(overlay);

        // Event listeners
        document.getElementById('demo-skip').onclick = () => this.stopDemo();
        document.getElementById('demo-next').onclick = () => this.nextStep();
    }

    runStep() {
        if (this.currentStep >= this.steps.length) {
            this.stopDemo();
            return;
        }

        const step = this.steps[this.currentStep];
        
        // Update demo UI
        document.getElementById('demo-title').textContent = step.title;
        document.getElementById('demo-description').textContent = step.description;
        document.getElementById('demo-step-info').textContent = `Step ${this.currentStep + 1} of ${this.steps.length}`;
        
        // Update progress bar
        const progress = ((this.currentStep + 1) / this.steps.length) * 100;
        document.getElementById('demo-progress-bar').style.width = progress + '%';

        // Execute step action
        this.executeAction(step.action);

        // Auto-advance after duration (unless it's an interactive step)
        if (!['show-popup', 'demo-complete'].includes(step.action)) {
            setTimeout(() => {
                if (this.isRunning) this.nextStep();
            }, step.duration);
        }
    }

    executeAction(action) {
        switch (action) {
            case 'highlight-title':
                this.highlightElement('h1');
                break;
                
            case 'load-sample-data':
                this.highlightElement('button[onclick="loadSampleData()"]');
                setTimeout(() => {
                    if (typeof loadSampleData === 'function') {
                        loadSampleData();
                    }
                }, 1000);
                break;
                
            case 'highlight-parameters':
                this.highlightElement('.section:has(#power-weight)');
                break;
                
            case 'run-analysis':
                this.highlightElement('button[onclick="performAdvancedSuitabilityAnalysis()"]');
                setTimeout(() => {
                    if (typeof performAdvancedSuitabilityAnalysis === 'function') {
                        performAdvancedSuitabilityAnalysis();
                    }
                }, 1500);
                break;
                
            case 'show-results':
                this.highlightElement('#analysis-results');
                setTimeout(() => {
                    if (typeof findOptimalLocations === 'function') {
                        findOptimalLocations();
                    }
                }, 2000);
                break;
                
            case 'show-popup':
                this.simulateMapClick();
                break;
                
            case 'generate-report':
                this.highlightElement('button[onclick="generateComparativeReport()"]');
                break;
                
            case 'demo-complete':
                document.getElementById('demo-next').textContent = 'Finish Demo';
                break;
        }
    }

    highlightElement(selector) {
        // Remove previous highlights
        document.querySelectorAll('.demo-highlight').forEach(el => {
            el.classList.remove('demo-highlight');
        });

        // Add highlight to target element
        const element = document.querySelector(selector);
        if (element) {
            element.classList.add('demo-highlight');
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    simulateMapClick() {
        // Simulate a click on the map to show popup
        if (typeof map !== 'undefined') {
            const center = map.getCenter();
            map.fire('click', {
                latlng: center,
                containerPoint: [300, 300],
                originalEvent: {}
            });
        }
    }

    nextStep() {
        this.currentStep++;
        if (this.currentStep >= this.steps.length) {
            this.stopDemo();
        } else {
            this.runStep();
        }
    }

    stopDemo() {
        this.isRunning = false;
        
        // Remove demo overlay
        const overlay = document.getElementById('demo-overlay');
        if (overlay) {
            overlay.remove();
        }

        // Remove highlights
        document.querySelectorAll('.demo-highlight').forEach(el => {
            el.classList.remove('demo-highlight');
        });
    }
}

// Add demo highlighting CSS
const demoStyles = document.createElement('style');
demoStyles.textContent = `
    .demo-highlight {
        position: relative;
        box-shadow: 0 0 0 3px #3498db, 0 0 20px rgba(52, 152, 219, 0.6) !important;
        border-radius: 8px !important;
        z-index: 9999;
        animation: demo-pulse 2s infinite;
    }

    @keyframes demo-pulse {
        0% { box-shadow: 0 0 0 3px #3498db, 0 0 20px rgba(52, 152, 219, 0.6); }
        50% { box-shadow: 0 0 0 6px #3498db, 0 0 30px rgba(52, 152, 219, 0.8); }
        100% { box-shadow: 0 0 0 3px #3498db, 0 0 20px rgba(52, 152, 219, 0.6); }
    }
`;
document.head.appendChild(demoStyles);

// Initialize demo
const platformDemo = new PlatformDemo();

// Add demo button to the page
function addDemoButton() {
    const demoButton = document.createElement('button');
    demoButton.textContent = '🎬 Start Demo';
    demoButton.className = 'btn';
    demoButton.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 1001;
        background: linear-gradient(45deg, #e74c3c, #c0392b);
        animation: demo-bounce 3s infinite;
    `;
    demoButton.onclick = () => platformDemo.startDemo();
    
    document.body.appendChild(demoButton);
}

// Bounce animation for demo button
const bounceStyles = document.createElement('style');
bounceStyles.textContent = `
    @keyframes demo-bounce {
        0%, 20%, 50%, 80%, 100% { transform: translateX(-50%) translateY(0); }
        40% { transform: translateX(-50%) translateY(-10px); }
        60% { transform: translateX(-50%) translateY(-5px); }
    }
`;
document.head.appendChild(bounceStyles);

// Add demo button when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addDemoButton);
} else {
    addDemoButton();
}

// Export for global access
window.PlatformDemo = PlatformDemo;
window.platformDemo = platformDemo;
