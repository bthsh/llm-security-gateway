// UI State
const state = {
  sessionId: 'sess_' + Math.random().toString(36).substring(2, 10),
  profile: 'customer_support',
  selectedSample: null,
  activeTab: 'chat',
  files: [],
  layers: {
    classifier: true,
    judge: true,
    tool_scoping: true,
    policy_engine: true,
    output_firewall: true
  },
  lastResponse: null
};

// DOM Elements
const profileSelect = document.getElementById('profileSelect');
const healthPill = document.getElementById('healthPill');
const healthText = document.getElementById('healthText');
const layersBtn = document.getElementById('layersBtn');
const layersMenu = document.getElementById('layersMenu');
const resetBtn = document.getElementById('resetBtn');
const bannerContainer = document.getElementById('bannerContainer');

const chatInput = document.getElementById('chatInput');
const pasteInput = document.getElementById('pasteInput');
const filePicker = document.getElementById('filePicker');
const dropPicker = document.getElementById('dropPicker');
const dropZone = document.getElementById('dropZone');
const attachedFilesList = document.getElementById('attachedFilesList');
const uploadFilesList = document.getElementById('uploadFilesList');

const sendBtn = document.getElementById('sendBtn');
const scanBtn = document.getElementById('scanBtn');
const sampleList = document.getElementById('sampleList');

const pipelineEmpty = document.getElementById('pipelineEmpty');
const pipelineContent = document.getElementById('pipelineContent');
const pipelineTime = document.getElementById('pipelineTime');
const traceGuardA = document.getElementById('traceGuardA');
const traceLLM = document.getElementById('traceLLM');
const llmStatusBadge = document.getElementById('llmStatusBadge');
const llmReason = document.getElementById('llmReason');
const llmTime = document.getElementById('llmTime');
const traceGuardB = document.getElementById('traceGuardB');
const traceAuditLog = document.getElementById('traceAuditLog');

const decisionBanner = document.getElementById('decisionBanner');
const decisionWord = document.getElementById('decisionWord');
const decisionReason = document.getElementById('decisionReason');
const beforeAfterCard = document.getElementById('beforeAfterCard');
const beforeAfterContent = document.getElementById('beforeAfterContent');
const replyText = document.getElementById('replyText');
const toolCallsContent = document.getElementById('toolCallsContent');
const outboxContent = document.getElementById('outboxContent');
const redactionsContent = document.getElementById('redactionsContent');
const approvalCard = document.getElementById('approvalCard');
const approvalText = document.getElementById('approvalText');
const approvalDetails = document.getElementById('approvalDetails');
const approveBtn = document.getElementById('approveBtn');
const denyBtn = document.getElementById('denyBtn');
const addTestsetBtn = document.getElementById('addTestsetBtn');

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadHealth();
  loadProfiles();
  loadSamples();
  loadLayers();
  loadMetrics();
});

function initEventListeners() {
  // Profile Selection
  profileSelect.addEventListener('change', (e) => {
    state.profile = e.target.value;
    resetSession();
  });

  // Layers Menu Toggle
  layersBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    layersMenu.classList.toggle('hidden');
    const isExpanded = !layersMenu.classList.contains('hidden');
    layersBtn.setAttribute('aria-expanded', isExpanded);
  });

  document.addEventListener('click', (e) => {
    if (!layersMenu.contains(e.target) && e.target !== layersBtn) {
      layersMenu.classList.add('hidden');
      layersBtn.setAttribute('aria-expanded', 'false');
    }
  });

  // Layer Checkboxes
  document.querySelectorAll('.layer-toggle-label input').forEach((checkbox) => {
    checkbox.addEventListener('change', (e) => {
      const layerName = e.target.getAttribute('data-layer');
      const val = e.target.checked;
      updateLayerToggle(layerName, val);
    });
  });

  // Reset Button
  resetBtn.addEventListener('click', () => {
    resetSession();
  });

  // Tabs
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach((p) => p.classList.remove('active'));
      
      btn.classList.add('active');
      const tabName = btn.getAttribute('data-tab');
      state.activeTab = tabName;
      
      if (tabName === 'chat') document.getElementById('tabChat').classList.add('active');
      if (tabName === 'upload') document.getElementById('tabUpload').classList.add('active');
      if (tabName === 'paste') document.getElementById('tabPaste').classList.add('active');
    });
  });

  // File Inputs
  filePicker.addEventListener('change', (e) => handleFileSelection(e.target.files));
  dropPicker.addEventListener('change', (e) => handleFileSelection(e.target.files));

  dropZone.addEventListener('click', () => dropPicker.click());
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--primary-accent)';
  });
  dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = 'var(--border-color)';
  });
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--border-color)';
    if (e.dataTransfer.files) {
      handleFileSelection(e.dataTransfer.files);
    }
  });

  // Action Buttons
  sendBtn.addEventListener('click', () => runPipelineRequest(false));
  scanBtn.addEventListener('click', () => runPipelineRequest(true));

  // Approval Buttons
  approveBtn.addEventListener('click', () => handleApproval(true));
  denyBtn.addEventListener('click', () => handleApproval(false));

  // Add to Testset
  addTestsetBtn.addEventListener('click', () => handleAddTestset());
}

function handleFileSelection(fileList) {
  state.selectedSample = null;
  renderSamplesList();

  for (let i = 0; i < fileList.length; i++) {
    state.files.push(fileList[i]);
  }
  renderFileChips();
}

function renderFileChips() {
  attachedFilesList.innerHTML = '';
  uploadFilesList.innerHTML = '';

  state.files.forEach((file, index) => {
    const chip = document.createElement('span');
    chip.className = 'file-chip';
    chip.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;

    const clone = chip.cloneNode(true);
    attachedFilesList.appendChild(chip);
    uploadFilesList.appendChild(clone);
  });
}

// API Calls
async function loadHealth() {
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      const data = await res.json();
      healthPill.className = 'health-pill health-online';
      healthText.textContent = `Gemini · Connected (${data.gemini_model})`;
    } else {
      throw new Error('Health check failed');
    }
  } catch (err) {
    healthPill.className = 'health-pill health-offline';
    healthText.textContent = 'Gemini · Unavailable';
  }
}

async function loadProfiles() {
  try {
    const res = await fetch('/api/profiles');
    if (res.ok) {
      const profiles = await res.json();
      profileSelect.innerHTML = '';
      profiles.forEach((p) => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.display_name;
        if (p.id === state.profile) opt.selected = true;
        profileSelect.appendChild(opt);
      });
    }
  } catch (err) {
    console.error('Failed to load profiles:', err);
  }
}

async function loadSamples() {
  try {
    const res = await fetch('/api/samples');
    if (res.ok) {
      const samples = await res.json();
      renderSamplesList(samples);
    }
  } catch (err) {
    sampleList.innerHTML = '<div class="text-muted">Failed to load samples</div>';
  }
}

let cachedSamples = [];
function renderSamplesList(samples) {
  if (samples) cachedSamples = samples;
  sampleList.innerHTML = '';

  cachedSamples.forEach((s) => {
    const item = document.createElement('div');
    item.className = 'sample-item' + (state.selectedSample === s.id ? ' active' : '');
    item.innerHTML = `
      <span class="sample-name">${s.name}</span>
      <span class="sample-type">${s.type}</span>
    `;
    item.addEventListener('click', () => {
      if (state.selectedSample === s.id) {
        state.selectedSample = null;
      } else {
        state.selectedSample = s.id;
        state.files = [];
        renderFileChips();
      }
      renderSamplesList();
    });
    sampleList.appendChild(item);
  });
}

async function loadLayers() {
  try {
    const res = await fetch(`/api/layers?session_id=${state.sessionId}`);
    if (res.ok) {
      const data = await res.json();
      state.layers = data;
      syncLayerCheckboxes();
      checkBanners();
    }
  } catch (err) {
    console.error('Failed to load layers:', err);
  }
}

function syncLayerCheckboxes() {
  for (const [key, val] of Object.entries(state.layers)) {
    const input = document.querySelector(`input[data-layer="${key}"]`);
    if (input) input.checked = val;
  }
}

async function updateLayerToggle(layerName, value) {
  const formData = new FormData();
  formData.append('session_id', state.sessionId);
  formData.append('layer', layerName);
  formData.append('value', value);

  try {
    const res = await fetch('/api/layers', { method: 'POST', body: formData });
    if (res.ok) {
      const updated = await res.json();
      state.layers = updated;
      checkBanners();
    }
  } catch (err) {
    console.error('Failed to update layer toggle:', err);
  }
}

async function resetSession() {
  const formData = new FormData();
  formData.append('session_id', state.sessionId);

  try {
    await fetch('/api/reset', { method: 'POST', body: formData });
    state.selectedSample = null;
    state.files = [];
    state.lastResponse = null;
    chatInput.value = '';
    pasteInput.value = '';
    renderFileChips();
    renderSamplesList();
    loadLayers();
    clearPanels();
  } catch (err) {
    console.error('Failed to reset session:', err);
  }
}

async function loadMetrics() {
  const statAttacks = document.getElementById('statAttacks');
  const statNormal = document.getElementById('statNormal');
  const statGatewayMs = document.getElementById('statGatewayMs');
  const statLlmMs = document.getElementById('statLlmMs');
  const evalTimestamp = document.getElementById('evalTimestamp');

  try {
    const res = await fetch('/api/metrics');
    if (res.ok) {
      const data = await res.json();
      if (data.measured) {
        statAttacks.textContent = `${data.attacks_caught || 0} / ${data.attacks_total || 0}`;
        statNormal.textContent = `${data.normal_wrongly_blocked || 0} / ${data.normal_total || 0}`;
        statGatewayMs.textContent = `${data.gateway_ms_median || 0} ms`;
        statLlmMs.textContent = `${data.llm_ms_median || 0} s`;
        evalTimestamp.textContent = `Evaluation: ${data.run_at || 'Completed'}`;
      } else {
        statAttacks.textContent = 'Not measured yet';
        statNormal.textContent = 'Not measured yet';
        statGatewayMs.textContent = 'Not measured yet';
        statLlmMs.textContent = 'Not measured yet';
        evalTimestamp.textContent = 'Evaluation: Not measured yet';
      }
    }
  } catch (err) {
    statAttacks.textContent = 'Not measured yet';
    statNormal.textContent = 'Not measured yet';
    statGatewayMs.textContent = 'Not measured yet';
    statLlmMs.textContent = 'Not measured yet';
    evalTimestamp.textContent = 'Evaluation: Not measured yet';
  }
}

function checkBanners() {
  bannerContainer.innerHTML = '';
  const offLayers = Object.entries(state.layers)
    .filter(([_, on]) => !on)
    .map(([name, _]) => name.replace('_', ' '));

  if (offLayers.length > 0) {
    const banner = document.createElement('div');
    banner.className = 'banner banner-warning';
    banner.textContent = `Demo mode: ${offLayers.join(', ')} is OFF`;
    bannerContainer.appendChild(banner);
  }
}

function clearPanels() {
  pipelineEmpty.classList.remove('hidden');
  pipelineContent.classList.add('hidden');
  pipelineTime.textContent = '0.0 ms';

  decisionBanner.className = 'decision-banner decision-none';
  decisionWord.textContent = 'NO REQUEST YET';
  decisionReason.textContent = 'Awaiting input';

  beforeAfterCard.classList.add('hidden');
  replyText.innerHTML = '<em class="text-muted">No reply generated yet.</em>';
  toolCallsContent.innerHTML = '<em class="text-muted">No tool calls.</em>';
  outboxContent.innerHTML = '<em class="text-muted">Empty · nothing was sent</em>';
  redactionsContent.innerHTML = '<em class="text-muted">None</em>';
  approvalCard.classList.add('hidden');
  addTestsetBtn.classList.add('hidden');
}

// Request Execution
async function runPipelineRequest(isScanMode) {
  const formData = new FormData();
  formData.append('session_id', state.sessionId);
  formData.append('profile', state.profile);

  let userMsg = '';
  if (state.activeTab === 'chat') userMsg = chatInput.value.trim();
  if (state.activeTab === 'paste') userMsg = pasteInput.value.trim();

  if (userMsg) formData.append('message', userMsg);
  if (state.selectedSample) formData.append('sample', state.selectedSample);

  state.files.forEach((f) => formData.append('files', f));

  if (!userMsg && !state.selectedSample && state.files.length === 0) {
    alert('Please enter a message, select a sample file, or attach a file first.');
    return;
  }

  sendBtn.disabled = true;
  scanBtn.disabled = true;
  sendBtn.textContent = 'Checking...';
  scanBtn.textContent = 'Checking...';

  const endpoint = isScanMode ? '/api/scan' : '/api/chat';

  try {
    const res = await fetch(endpoint, { method: 'POST', body: formData });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText || `Server error (${res.status})`);
    }

    const data = await res.json();
    state.lastResponse = data;
    renderResponse(data);
  } catch (err) {
    bannerContainer.innerHTML = `
      <div class="banner banner-error">
        Error executing request: ${err.message}
      </div>
    `;
  } finally {
    sendBtn.disabled = false;
    scanBtn.disabled = false;
    sendBtn.textContent = 'Send (Full Pipeline)';
    scanBtn.textContent = 'Check Only (Guard A)';
  }
}

async function handleApproval(approveBool) {
  if (!state.lastResponse || !state.lastResponse.pending_action) return;

  const formData = new FormData();
  formData.append('session_id', state.sessionId);
  formData.append('pending_id', state.lastResponse.pending_action.id);
  formData.append('approve', approveBool);

  try {
    const res = await fetch('/api/approve', { method: 'POST', body: formData });
    if (res.ok) {
      const data = await res.json();
      state.lastResponse = data;
      renderResponse(data);
    }
  } catch (err) {
    console.error('Approval failed:', err);
  }
}

async function handleAddTestset() {
  if (!state.lastResponse) return;

  const formData = new FormData();
  formData.append('request_id', state.lastResponse.request_id);
  formData.append('session_id', state.sessionId);
  formData.append('profile', state.profile);

  let userMsg = '';
  if (state.activeTab === 'chat') userMsg = chatInput.value.trim();
  if (state.activeTab === 'paste') userMsg = pasteInput.value.trim();
  if (userMsg) formData.append('message', userMsg);
  if (state.selectedSample) formData.append('sample', state.selectedSample);

  try {
    const res = await fetch('/api/testset', { method: 'POST', body: formData });
    if (res.ok) {
      addTestsetBtn.textContent = 'Saved!';
      setTimeout(() => {
        addTestsetBtn.textContent = 'Add to test set';
      }, 2000);
    }
  } catch (err) {
    console.error('Failed to add to testset:', err);
  }
}

// Render Response
function renderResponse(data) {
  pipelineEmpty.classList.add('hidden');
  pipelineContent.classList.remove('hidden');

  // Timings
  const totalMs = data.timings ? data.timings.total_ms || 0 : 0;
  pipelineTime.textContent = `${totalMs.toFixed(1)} ms`;

  // Pipeline Trace Rows
  renderTrace(data.trace);

  // Decision Banner
  renderDecisionBanner(data.decision, data.decision_reason);

  // Before / After Diff
  renderBeforeAfter(data.before_after);

  // AI Reply
  replyText.textContent = data.reply || '(No reply text)';

  // Tool Calls
  renderToolCalls(data.tool_calls, data.hidden_tools);

  // Outbox
  renderOutbox(data.outbox);

  // Redactions
  renderRedactions(data.redactions);

  // Pending Approval Card
  if (data.pending_action) {
    approvalCard.classList.remove('hidden');
    approvalText.textContent = `The AI assistant attempts to run risky action '${data.pending_action.tool}'. Approve?`;
    approvalDetails.textContent = `Args: ${JSON.stringify(data.pending_action.args, null, 2)}\nReason: ${data.pending_action.reason}`;
  } else {
    approvalCard.classList.add('hidden');
  }

  addTestsetBtn.classList.remove('hidden');
}

function renderTrace(trace) {
  traceGuardA.innerHTML = '';
  traceGuardB.innerHTML = '';
  traceAuditLog.innerHTML = '';

  if (!trace || !Array.isArray(trace)) return;

  trace.forEach((step) => {
    if (step.name === 'llm') {
      llmStatusBadge.className = getStatusBadgeClass(step.status);
      llmStatusBadge.textContent = step.status;
      llmReason.textContent = step.reason || 'gemini';
      llmTime.textContent = `${(step.ms || 0).toFixed(1)} ms`;
      return;
    }

    const row = document.createElement('div');
    row.className = 'trace-row';
    const isFlaggedOrBlocked = ['FLAGGED', 'BLOCKED', 'ERROR'].includes(step.status);
    const reasonClass = isFlaggedOrBlocked ? 'trace-reason bold' : 'trace-reason';

    row.innerHTML = `
      <span class="trace-step">${step.step}</span>
      <span class="trace-name">${step.name}</span>
      <span class="status-badge ${getStatusBadgeClass(step.status)}">${step.status}</span>
      <span class="${reasonClass}" title="${escapeHtml(step.reason)}">${escapeHtml(step.reason)}</span>
      <span class="trace-time font-mono">${(step.ms || 0).toFixed(1)} ms</span>
    `;

    if (typeof step.step === 'number' && step.step <= 7) {
      traceGuardA.appendChild(row);
    } else if (typeof step.step === 'number' && (step.step === 8 || step.step === 9)) {
      traceGuardB.appendChild(row);
    } else {
      traceAuditLog.appendChild(row);
    }
  });
}

function getStatusBadgeClass(status) {
  switch (status) {
    case 'PASSED': return 'status-passed';
    case 'FLAGGED': return 'status-flagged';
    case 'CLEANED': return 'status-cleaned';
    case 'BLOCKED': return 'status-blocked';
    case 'SKIPPED': return 'status-skipped';
    case 'INFO': return 'status-info';
    case 'LOGGED': return 'status-logged';
    case 'ERROR': return 'status-error';
    default: return 'status-info';
  }
}

function renderDecisionBanner(decision, reason) {
  decisionBanner.className = 'decision-banner';

  switch (decision) {
    case 'ALLOWED':
      decisionBanner.classList.add('decision-allowed');
      decisionWord.textContent = 'ALLOWED · Prompt passed security checks';
      break;
    case 'CLEANED':
      decisionBanner.classList.add('decision-cleaned');
      decisionWord.textContent = 'CLEANED · Answered safely (untrusted risk removed)';
      break;
    case 'BLOCKED':
      decisionBanner.classList.add('decision-blocked');
      decisionWord.textContent = 'BLOCKED · Stopped at security guard';
      break;
    case 'BLOCKED_ACTION':
      decisionBanner.classList.add('decision-blocked-action');
      decisionWord.textContent = 'BLOCKED ACTION · AI tool action stopped by policy';
      break;
    case 'NEEDS_APPROVAL':
      decisionBanner.classList.add('decision-needs-approval');
      decisionWord.textContent = 'NEEDS APPROVAL · User authorization required';
      break;
    default:
      decisionBanner.classList.add('decision-none');
      decisionWord.textContent = decision || 'UNKNOWN';
  }
  decisionReason.textContent = reason || '';
}

function renderBeforeAfter(beforeAfter) {
  if (!beforeAfter || beforeAfter.length === 0) {
    beforeAfterCard.classList.add('hidden');
    return;
  }

  let hasDiff = false;
  let html = '';

  beforeAfter.forEach((item) => {
    if (item.removed && item.removed.length > 0) {
      hasDiff = true;
      html += `<div><strong>${escapeHtml(item.origin || 'Attachment')}:</strong></div>`;
      if (item.kept_text) {
        html += `<div>${escapeHtml(item.kept_text)}</div>`;
      }
      item.removed.forEach((rem) => {
        html += `
          <span class="diff-removed">
            ${escapeHtml(rem.text)}
            <span class="diff-reason">[Removed: ${escapeHtml(rem.reason)}]</span>
          </span>
        `;
      });
    }
  });

  if (hasDiff) {
    beforeAfterCard.classList.remove('hidden');
    beforeAfterContent.innerHTML = html;
  } else {
    beforeAfterCard.classList.add('hidden');
  }
}

function renderToolCalls(toolCalls, hiddenTools) {
  toolCallsContent.innerHTML = '';
  let html = '';

  if (hiddenTools && hiddenTools.length > 0) {
    html += `<div class="text-amber font-bold mb-2">Notice: Tool '${hiddenTools.join(', ')}' was hidden from AI because session is tainted.</div>`;
  }

  if (toolCalls && toolCalls.length > 0) {
    toolCalls.forEach((tc) => {
      const badgeClass = getStatusBadgeClass(tc.status);
      html += `
        <div style="margin-bottom: 8px;">
          <div><strong>${escapeHtml(tc.tool)}</strong>(${escapeHtml(JSON.stringify(tc.args))})</div>
          <div>Status: <span class="status-badge ${badgeClass}">${tc.status}</span> - ${escapeHtml(tc.reason || '')}</div>
        </div>
      `;
    });
  } else if (!hiddenTools || hiddenTools.length === 0) {
    html = '<em class="text-muted">No tool calls.</em>';
  }

  toolCallsContent.innerHTML = html;
}

function renderOutbox(outbox) {
  if (!outbox || outbox.length === 0) {
    outboxContent.innerHTML = '<em class="text-muted">Empty · nothing was sent</em>';
    return;
  }

  let html = '';
  outbox.forEach((mail, i) => {
    html += `
      <div style="border-bottom: 1px solid var(--border-color); padding-bottom: 6px; margin-bottom: 6px;">
        <div><strong>To:</strong> ${escapeHtml(mail.to || '')}</div>
        <div><strong>Subject:</strong> ${escapeHtml(mail.subject || '')}</div>
        <div><strong>Body:</strong> ${escapeHtml(mail.body || '')}</div>
      </div>
    `;
  });
  outboxContent.innerHTML = html;
}

function renderRedactions(redactions) {
  if (!redactions || redactions.length === 0) {
    redactionsContent.innerHTML = '<em class="text-muted">None</em>';
    return;
  }

  let html = '';
  redactions.forEach((r) => {
    html += `<div><strong>${escapeHtml(r.type)}:</strong> ${escapeHtml(r.preview)} → <code>${escapeHtml(r.replacement)}</code></div>`;
  });
  redactionsContent.innerHTML = html;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
