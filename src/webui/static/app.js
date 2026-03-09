// DOM elements
const variablesContainer = document.getElementById('variables');
const titleTemplate = document.getElementById('title-template');
const messageTemplate = document.getElementById('message-template');
const presetSelect = document.getElementById('preset-select');
const previewTitle = document.getElementById('preview-title');
const previewMessage = document.getElementById('preview-message');
const saveBtn = document.getElementById('save-btn');
const statusDiv = document.getElementById('status');

// State
let variables = [];
let presets = [];
let lastFocusedTextarea = null;
let debounceTimer = null;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([
        loadVariables(),
        loadPresets(),
        loadConfig()
    ]);
    
    // Set up event listeners
    titleTemplate.addEventListener('input', schedulePreview);
    messageTemplate.addEventListener('input', schedulePreview);
    titleTemplate.addEventListener('focus', () => lastFocusedTextarea = titleTemplate);
    messageTemplate.addEventListener('focus', () => lastFocusedTextarea = messageTemplate);
    presetSelect.addEventListener('change', loadPreset);
    saveBtn.addEventListener('click', saveTemplate);
    
    // Initial preview
    updatePreview();
});

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
        renderPresets();
    } catch (error) {
        console.error('Error loading presets:', error);
    }
}

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        titleTemplate.value = config.title_template || '';
        messageTemplate.value = config.message_template || '';
        updatePreview();
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

function renderVariables() {
    variablesContainer.innerHTML = '';
    variables.forEach(v => {
        const chip = document.createElement('button');
        chip.className = 'chip';
        chip.innerHTML = `
            <span class="chip-name">{{${v.name}}}</span>
            <span class="chip-desc">${v.description}</span>
        `;
        chip.addEventListener('click', () => insertVariable(v.name));
        variablesContainer.appendChild(chip);
    });
}

function renderPresets() {
    presetSelect.innerHTML = '<option value="">-- Load Preset --</option>';
    presets.forEach((preset, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = preset.name;
        presetSelect.appendChild(option);
    });
}

function insertVariable(varName) {
    // Determine which textarea to use
    const textarea = lastFocusedTextarea || titleTemplate;
    const variable = `{{${varName}}}`;
    
    // Get cursor position
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    
    // Insert at cursor
    textarea.value = text.substring(0, start) + variable + text.substring(end);
    
    // Move cursor after inserted variable
    const newCursorPos = start + variable.length;
    textarea.setSelectionRange(newCursorPos, newCursorPos);
    textarea.focus();
    
    // Update preview
    schedulePreview();
}

function loadPreset() {
    const index = parseInt(presetSelect.value);
    if (isNaN(index)) return;
    
    const preset = presets[index];
    titleTemplate.value = preset.title;
    messageTemplate.value = preset.message;
    
    // Update preview
    updatePreview();
    
    // Reset select
    presetSelect.value = '';
}

function schedulePreview() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(updatePreview, 300);
}

async function updatePreview() {
    const title = titleTemplate.value;
    const message = messageTemplate.value;
    
    if (!title && !message) {
        previewTitle.textContent = 'No template';
        previewMessage.textContent = 'Start typing to see preview...';
        return;
    }
    
    try {
        const response = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title_template: title,
                message_template: message
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Preview error');
        }
        
        const data = await response.json();
        previewTitle.textContent = data.title || '(empty)';
        previewMessage.textContent = data.message || '(empty)';
        
        // Clear any error styling
        previewTitle.style.color = '';
        previewMessage.style.color = '';
        
    } catch (error) {
        previewTitle.textContent = 'Error';
        previewTitle.style.color = '#e74c3c';
        previewMessage.textContent = error.message;
        previewMessage.style.color = '#e74c3c';
    }
}

async function saveTemplate() {
    const title = titleTemplate.value;
    const message = messageTemplate.value;
    
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    statusDiv.textContent = '';
    statusDiv.className = 'status';
    
    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title_template: title,
                message_template: message
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Save error');
        }
        
        const data = await response.json();
        statusDiv.textContent = '✓ ' + data.message;
        statusDiv.className = 'status success';
        
    } catch (error) {
        statusDiv.textContent = '✗ ' + error.message;
        statusDiv.className = 'status error';
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 Save Template';
    }
}