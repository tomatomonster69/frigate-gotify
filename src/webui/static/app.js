// Tab Navigation
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
    });
});

// Range slider value displays
const rangeInputs = [
    'poll_interval',
    'notification_priority',
    'snapshot_quality',
    'image_max_width',
    'image_max_height',
    'image_quality',
    'image_max_size_kb'
];

rangeInputs.forEach(id => {
    const input = document.getElementById(id);
    const display = document.getElementById(`${id}_value`);
    if (input && display) {
        input.addEventListener('input', () => {
            display.textContent = input.value;
        });
    }
});

// Variables loading
let variables = [];
let presets = [];

async function loadVariables() {
    try {
        const response = await fetch('/api/variables');
        const data = await response.json();
        variables = data.variables;
        renderVariables();
    } catch (error) {
        console.error('Error loading variables:', error);
    }
}

async function loadPresets() {
    try {
        const response = await fetch('/api/presets');
        const data = await response.json();
        presets = data.presets;
    } catch (error) {
        console.error('Error loading presets:', error);
    }
}

function renderVariables() {
    const container = document.getElementById('variables');
    container.innerHTML = variables.map(v => `
        <span class="chip" data-var="${v.name}" title="${v.description}">
            <span class="var-name">{{${v.name}}}</span>
        </span>
    `).join('');
    
    // Add click handlers for variable insertion
    container.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const varName = chip.dataset.var;
            insertVariable(varName);
        });
    });
}

function insertVariable(varName) {
    const template = `{{${varName}}}`;
    const titleTextarea = document.getElementById('title_template');
    const messageTextarea = document.getElementById('message_template');
    
    // Insert into the focused textarea, or message template by default
    const activeElement = document.activeElement;
    if (activeElement === titleTextarea) {
        insertAtCursor(titleTextarea, template);
    } else {
        insertAtCursor(messageTextarea, template);
    }
    
    updatePreview();
}

function insertAtCursor(textarea, text) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    
    textarea.value = value.substring(0, start) + text + value.substring(end);
    textarea.selectionStart = textarea.selectionEnd = start + text.length;
    textarea.focus();
}

// Preset buttons
document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const index = parseInt(btn.dataset.preset);
        if (presets[index]) {
            document.getElementById('title_template').value = presets[index].title;
            document.getElementById('message_template').value = presets[index].message;
            updatePreview();
        }
    });
});

// Live preview with debounce
let previewTimeout;
async function updatePreview() {
    clearTimeout(previewTimeout);
    previewTimeout = setTimeout(async () => {
        const titleTemplate = document.getElementById('title_template').value;
        const messageTemplate = document.getElementById('message_template').value;
        
        if (!titleTemplate && !messageTemplate) return;
        
        try {
            const response = await fetch('/api/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title_template: titleTemplate || '{{camera}}',
                    message_template: messageTemplate || '{{object}} detected'
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                document.getElementById('preview-title').textContent = data.title;
                document.getElementById('preview-message').textContent = data.message;
            } else {
                document.getElementById('preview-title').textContent = 'Error';
                document.getElementById('preview-message').textContent = data.detail || 'Template error';
            }
        } catch (error) {
            document.getElementById('preview-title').textContent = 'Error';
            document.getElementById('preview-message').textContent = 'Failed to load preview';
        }
    }, 300);
}

// Template textareas
document.getElementById('title_template').addEventListener('input', updatePreview);
document.getElementById('message_template').addEventListener('input', updatePreview);

// Load configuration
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        
        // Frigate
        document.getElementById('frigate_url').value = config.frigate_url || '';
        document.getElementById('frigate_api_key').value = config.frigate_api_key || '';
        document.getElementById('frigate_username').value = config.frigate_username || '';
        document.getElementById('frigate_password').value = config.frigate_password || '';
        document.getElementById('verify_ssl').checked = config.verify_ssl || false;
        
        // Gotify
        document.getElementById('gotify_url').value = config.gotify_url || '';
        document.getElementById('gotify_app_token').value = config.gotify_app_token || '';
        
        // Notifications
        document.getElementById('poll_interval').value = config.poll_interval || 10;
        document.getElementById('poll_interval_value').textContent = config.poll_interval || 10;
        document.getElementById('notification_priority').value = config.notification_priority || 5;
        document.getElementById('notification_priority_value').textContent = config.notification_priority || 5;
        document.getElementById('include_snapshot').checked = config.include_snapshot !== false;
        document.getElementById('snapshot_quality').value = config.snapshot_quality || 90;
        document.getElementById('snapshot_quality_value').textContent = config.snapshot_quality || 90;
        document.getElementById('snapshot_format').value = config.snapshot_format || 'jpg';
        
        // Compression
        document.getElementById('image_compression_enabled').checked = config.image_compression_enabled !== false;
        document.getElementById('image_max_width').value = config.image_max_width || 640;
        document.getElementById('image_max_width_value').textContent = config.image_max_width || 640;
        document.getElementById('image_max_height').value = config.image_max_height || 480;
        document.getElementById('image_max_height_value').textContent = config.image_max_height || 480;
        document.getElementById('image_quality').value = config.image_quality || 75;
        document.getElementById('image_quality_value').textContent = config.image_quality || 75;
        document.getElementById('image_max_size_kb').value = config.image_max_size_kb || 100;
        document.getElementById('image_max_size_kb_value').textContent = config.image_max_size_kb || 100;
        
        // Filters
        document.getElementById('severity_filter').value = config.severity_filter || 'alert,detection';
        document.getElementById('camera_filter').value = config.camera_filter || 'all';
        
        // Templates
        document.getElementById('title_template').value = config.title_template || '';
        document.getElementById('message_template').value = config.message_template || '';
        
        // Debug
        document.getElementById('debug').checked = config.debug || false;
        
        // Update preview
        updatePreview();
        
    } catch (error) {
        showStatus('Failed to load configuration', 'error');
    }
}

// Form submission
document.getElementById('config-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        // Frigate
        frigate_url: document.getElementById('frigate_url').value,
        frigate_api_key: document.getElementById('frigate_api_key').value || null,
        frigate_username: document.getElementById('frigate_username').value || null,
        frigate_password: document.getElementById('frigate_password').value || null,
        
        // Gotify
        gotify_url: document.getElementById('gotify_url').value,
        gotify_app_token: document.getElementById('gotify_app_token').value,
        
        // SSL
        verify_ssl: document.getElementById('verify_ssl').checked,
        
        // Polling
        poll_interval: parseInt(document.getElementById('poll_interval').value),
        
        // Notifications
        notification_priority: parseInt(document.getElementById('notification_priority').value),
        include_snapshot: document.getElementById('include_snapshot').checked,
        snapshot_quality: parseInt(document.getElementById('snapshot_quality').value),
        snapshot_format: document.getElementById('snapshot_format').value,
        
        // Compression
        image_compression_enabled: document.getElementById('image_compression_enabled').checked,
        image_max_width: parseInt(document.getElementById('image_max_width').value),
        image_max_height: parseInt(document.getElementById('image_max_height').value),
        image_quality: parseInt(document.getElementById('image_quality').value),
        image_max_size_kb: parseInt(document.getElementById('image_max_size_kb').value),
        
        // Filters
        severity_filter: document.getElementById('severity_filter').value,
        camera_filter: document.getElementById('camera_filter').value,
        
        // Templates
        title_template: document.getElementById('title_template').value || null,
        message_template: document.getElementById('message_template').value || null,
        
        // Debug
        debug: document.getElementById('debug').checked
    };
    
    try {
        showStatus('Saving...', 'info');
        
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showStatus('✓ ' + data.message, 'success');
        } else {
            showStatus('✗ ' + (data.detail || 'Failed to save'), 'error');
        }
    } catch (error) {
        showStatus('✗ Network error', 'error');
    }
});

function showStatus(message, type) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = 'status ' + type;
    
    setTimeout(() => {
        status.className = 'status';
    }, 5000);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadVariables();
    loadPresets();
    loadConfig();
});