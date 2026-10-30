/**
 * LogicFlow – Main Application JavaScript
 * Single-file JS (consolidated for simplicity); handles:
 *  - Editor + line numbers
 *  - Tab switching
 *  - API calls (analyze, run, step)
 *  - Flowchart rendering + execution highlighting
 *  - Input modal
 *  - Example loading
 */

'use strict';

// ─── Mermaid init ────────────────────────────────────────────────────────────
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    background: '#1c2128',
    primaryColor: '#2196F3',
    primaryTextColor: '#e6edf3',
    primaryBorderColor: '#30363d',
    lineColor:  '#8b949e',
    secondaryColor: '#161b22',
    tertiaryColor:  '#0d1117',
  },
  flowchart: { curve: 'basis', useMaxWidth: true },
  securityLevel: 'loose',
});

// ─── State ───────────────────────────────────────────────────────────────────
const state = {
  sessionId: null,
  stepping: false,
  pendingInputs: [],
  currentInputVar: null,
  fcScale: 1,
  executedNodes: new Set(),
  activeNodeId: null,
  flowchartNodes: {},   // node_id -> metadata from backend
  runningInputs: [],    // collected inputs for re-runs
};

// ─── DOM refs ────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const editor       = $('codeEditor');
const lineNumbers  = $('lineNumbers');
const mermaidCont  = $('mermaidContainer');
const fcPlaceholder = $('fcPlaceholder');
const outputArea   = $('outputArea');
const irView       = $('irView');
const tokenGrid    = $('tokenGrid');
const astView      = $('astView');
const errorList    = $('errorList');
const execStatus   = $('execStatus');
const inputModal   = $('inputModal');
const inputField   = $('inputField');
const inputVarName = $('inputVarName');
const exampleSelect = $('exampleSelect');

// ─── Line numbers ─────────────────────────────────────────────────────────
function updateLineNumbers() {
  const lines = editor.value.split('\n').length;
  lineNumbers.textContent = Array.from({length: lines}, (_, i) => i + 1).join('\n');
}
editor.addEventListener('input', updateLineNumbers);
editor.addEventListener('scroll', () => { lineNumbers.scrollTop = editor.scrollTop; });
updateLineNumbers();

// ─── Tabs ─────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    $(`tab-${tab.dataset.tab}`).classList.add('active');
  });
});

// ─── Zoom ─────────────────────────────────────────────────────────────────
$('btnZoomIn').addEventListener('click',  () => { state.fcScale = Math.min(state.fcScale + 0.2, 3); applyZoom(); });
$('btnZoomOut').addEventListener('click', () => { state.fcScale = Math.max(state.fcScale - 0.2, 0.3); applyZoom(); });
$('btnFit').addEventListener('click', () => { state.fcScale = 1; applyZoom(); });
function applyZoom() { mermaidCont.style.transform = `scale(${state.fcScale})`; }

// ─── Clear / New / Reset ─────────────────────────────────────────────────
$('btnClear').addEventListener('click', () => { editor.value = ''; updateLineNumbers(); });
$('btnNew').addEventListener('click', () => {
  editor.value = '';
  updateLineNumbers();
  clearAll();
});
$('btnReset').addEventListener('click', () => {
  resetExecution();
  clearOutputArea();
  setExecStatus('', '');
});

// ─── Examples ─────────────────────────────────────────────────────────────
async function loadExamples() {
  try {
    const res = await fetch('/api/examples');
    const examples = await res.json();
    Object.entries(examples).forEach(([key, ex]) => {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = ex.name;
      exampleSelect.appendChild(opt);
    });
    // Store full data
    window._examples = examples;
  } catch(e) { console.warn('Could not load examples', e); }
}

exampleSelect.addEventListener('change', () => {
  const key = exampleSelect.value;
  if (!key || !window._examples) return;
  editor.value = window._examples[key].code;
  updateLineNumbers();
  clearAll();
  exampleSelect.value = '';
});

loadExamples();

// ─── Analyze ──────────────────────────────────────────────────────────────
$('btnAnalyze').addEventListener('click', analyze);

async function analyze() {
  const code = editor.value.trim();
  if (!code) return;
  setExecStatus('Analyzing…', 'wait');
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({code}),
    });
    const data = await res.json();
    displayTokens(data.tokens || []);
    displayAST(data.ast);
    displayIR(data.intermediate_text || '');
    displayErrors(data.errors || []);
    if (data.flowchart && data.flowchart.mermaid) {
      await renderFlowchart(data.flowchart.mermaid, data.flowchart.nodes || {});
    }
    if (data.errors && data.errors.length > 0) {
      setExecStatus(`${data.errors.length} error(s) found`, 'error');
      switchTab('errors');
    } else {
      setExecStatus('Analysis complete ✓', 'ok');
    }
  } catch(e) {
    setExecStatus('Request failed', 'error');
  }
}

// ─── Run ──────────────────────────────────────────────────────────────────
$('btnRun').addEventListener('click', () => runProgram([]));

async function runProgram(inputs) {
  const code = editor.value.trim();
  if (!code) return;
  resetExecution();
  clearOutputArea();
  setExecStatus('Running…', 'wait');
  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({code, inputs}),
    });
    const data = await res.json();

    // Render flowchart
    if (data.flowchart && data.flowchart.mermaid) {
      await renderFlowchart(data.flowchart.mermaid, data.flowchart.nodes || {});
    }

    displayErrors(data.errors || []);

    if (data.status === 'waiting_input') {
      state.runningInputs = inputs.slice();
      showInputModal(data.waiting_for, (val) => {
        state.runningInputs.push(val);
        runProgram(state.runningInputs);
      });
      setExecStatus(`Waiting for input: ${data.waiting_for}`, 'wait');
      return;
    }

    // Display output
    displayOutput(data.output || []);

    // Highlight execution path
    if (data.events) {
      highlightExecutionPath(data.events);
    }

    if (data.status === 'completed') {
      setExecStatus('Execution complete ✓', 'ok');
    } else if (data.status === 'error') {
      setExecStatus('Runtime error', 'error');
    }

    if (data.errors && data.errors.length > 0) {
      switchTab('errors');
    } else {
      switchTab('output');
    }
  } catch(e) {
    setExecStatus('Request failed', 'error');
  }
}

// ─── Step ─────────────────────────────────────────────────────────────────
$('btnStep').addEventListener('click', doStep);
$('btnContinue').addEventListener('click', doContinue);

async function doStep() {
  const code = editor.value.trim();
  if (!code) return;

  if (!state.stepping) {
    resetExecution();
    clearOutputArea();
    state.stepping = true;
    $('btnContinue').disabled = false;
  }

  setExecStatus('Stepping…', 'wait');
  try {
    const body = {code};
    if (state.sessionId) body.session_id = state.sessionId;

    const res = await fetch('/api/step', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (data.errors && data.errors.length > 0) {
      displayErrors(data.errors);
      setExecStatus('Error during step', 'error');
      state.stepping = false;
      return;
    }

    state.sessionId = data.session_id;

    // Render flowchart once
    if (data.flowchart && data.flowchart.mermaid && !state._fcRendered) {
      await renderFlowchart(data.flowchart.mermaid, data.flowchart.nodes || {});
      state._fcRendered = true;
    }

    // Highlight current event
    if (data.event) {
      applyEventHighlight(data.event);
      showStepEvent(data.event);
      switchTab('output');
    }

    // Update output
    if (data.output) displayOutput(data.output);

    if (data.done || data.status === 'completed') {
      setExecStatus(`Stepped: done (${data.event_index + 1}/${data.total_events} events) ✓`, 'ok');
      $('btnContinue').disabled = true;
      state.stepping = false;
      state.sessionId = null;
      state._fcRendered = false;
    } else {
      setExecStatus(`Step ${data.event_index + 1} / ${data.total_events}`, 'wait');
    }
  } catch(e) {
    setExecStatus('Step failed', 'error');
  }
}

async function doContinue() {
  while (state.stepping && state.sessionId) {
    await doStep();
    await delay(150);
    if (!state.stepping) break;
  }
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

// ─── Flowchart rendering ──────────────────────────────────────────────────

async function renderFlowchart(mermaidText, nodesMap) {
  state.flowchartNodes = nodesMap;
  state.executedNodes.clear();
  state.activeNodeId = null;

  fcPlaceholder.style.display = 'none';
  mermaidCont.innerHTML = '';
  mermaidCont.removeAttribute('data-processed');

  try {
    const id = 'lf-diagram-' + Date.now();
    const { svg } = await mermaid.render(id, mermaidText);
    mermaidCont.innerHTML = svg;

    // Give Mermaid nodes data-id attributes by injecting CSS class targets
    // Mermaid uses node ids in class names like .node.default#start etc.
    // We query by g.node elements and their id attributes
    const svgEl = mermaidCont.querySelector('svg');
    if (svgEl) {
      svgEl.style.maxWidth = '100%';
      svgEl.style.height = 'auto';
    }
  } catch(e) {
    mermaidCont.innerHTML = `<p style="color:#f85149;padding:20px">Flowchart render error: ${e.message}</p>`;
    console.error('Mermaid error', e, mermaidText);
  }
}

function highlightExecutionPath(events) {
  // Process all events and highlight visited/active nodes
  const visitedIds = new Set();
  let lastNodeId = null;

  events.forEach(evt => {
    if (evt.node_id && evt.node_id !== 'start' && evt.node_id !== 'end') {
      visitedIds.add(evt.node_id);
      lastNodeId = evt.node_id;
    }
    if (evt.event === 'program_start') visitedIds.add('node_start');
    if (evt.event === 'program_end')   visitedIds.add('node_end');
  });

  visitedIds.forEach(id => highlightNode(id, 'visited'));
  if (lastNodeId) highlightNode(lastNodeId, 'active');
}

function applyEventHighlight(event) {
  // Clear previous active
  clearActiveHighlights();

  const nid = event.node_id;
  if (!nid) return;

  state.executedNodes.add(nid);
  highlightNode(nid, 'visited');
  highlightNode(nid, 'active');
  state.activeNodeId = nid;
}

function highlightNode(nodeId, cls) {
  const svgEl = mermaidCont.querySelector('svg');
  if (!svgEl) return;
  // Mermaid 10 puts node IDs as the id of <g> elements: flowchart-<nodeId>-N
  // We search for g elements whose id starts with flowchart-<nodeId>
  const candidates = svgEl.querySelectorAll(`g[id^="flowchart-${nodeId}"]`);
  candidates.forEach(g => {
    g.classList.add(`node-${cls}`);
    // Also directly style the shape element
    const shape = g.querySelector('rect, polygon, circle, ellipse, path');
    if (shape) {
      if (cls === 'active') {
        shape.style.stroke = '#d29922';
        shape.style.strokeWidth = '4px';
        shape.style.filter = 'drop-shadow(0 0 8px #d29922)';
      } else if (cls === 'visited') {
        if (!shape.style.stroke || shape.style.stroke === '') {
          shape.style.stroke = '#3fb950';
          shape.style.strokeWidth = '2px';
        }
      }
    }
  });
}

function clearActiveHighlights() {
  const svgEl = mermaidCont.querySelector('svg');
  if (!svgEl) return;
  svgEl.querySelectorAll('.node-active').forEach(el => {
    el.classList.remove('node-active');
    const shape = el.querySelector('rect, polygon, circle, ellipse, path');
    if (shape) { shape.style.filter = ''; shape.style.strokeWidth = '2px'; }
  });
}

// ─── Output / IR / Tokens / AST / Errors ──────────────────────────────────

function displayOutput(lines) {
  if (!lines || lines.length === 0) {
    outputArea.innerHTML = '<span class="output-placeholder">No output produced.</span>';
    return;
  }
  outputArea.textContent = lines.join('\n');
}

function clearOutputArea() {
  outputArea.innerHTML = '<span class="output-placeholder">Running…</span>';
}

function displayIR(text) {
  irView.textContent = text || '(No intermediate code)';
}

function displayTokens(tokens) {
  if (!tokens || tokens.length === 0) {
    tokenGrid.textContent = 'No tokens.';
    return;
  }
  tokenGrid.innerHTML = '';
  tokens.filter(t => t.type !== 'NEWLINE' && t.type !== 'EOF').forEach(t => {
    const chip = document.createElement('div');
    chip.className = 'token-chip';
    chip.title = `Line ${t.line}, Col ${t.column}`;
    chip.innerHTML = `<span class="token-type">${escHtml(t.type)}</span><span class="token-val">${escHtml(String(t.value))}</span>`;
    tokenGrid.appendChild(chip);
  });
}

function displayAST(ast) {
  astView.textContent = ast ? JSON.stringify(ast, null, 2) : '(No AST)';
}

function displayErrors(errors) {
  if (!errors || errors.length === 0) {
    errorList.innerHTML = '<span class="output-placeholder">No errors detected. ✓</span>';
    return;
  }
  errorList.innerHTML = '';
  errors.forEach(err => {
    const item = document.createElement('div');
    item.className = 'error-item';
    const loc = (err.line ? `Line ${err.line}` : '') + (err.column ? `, Col ${err.column}` : '');
    item.innerHTML = `
      <span class="error-badge">${escHtml(err.category || 'Error')}</span>
      <span class="error-msg">${escHtml(err.message || '')}</span>
      ${loc ? `<span class="error-loc">${escHtml(loc)}</span>` : ''}
    `;
    errorList.appendChild(item);
  });
}

function showStepEvent(event) {
  const existing = $('tab-output').querySelector('.step-event-display');
  if (existing) existing.remove();
  const div = document.createElement('div');
  div.className = 'step-event-display';
  div.textContent = `Event: ${event.event} → node: ${event.node_id}  ${JSON.stringify(event.detail)}`;
  $('tab-output').appendChild(div);
}

// ─── Input Modal ──────────────────────────────────────────────────────────

let _inputCallback = null;

function showInputModal(varName, callback) {
  inputVarName.textContent = varName;
  inputField.value = '';
  inputModal.style.display = 'flex';
  inputField.focus();
  _inputCallback = callback;
}

function hideInputModal() {
  inputModal.style.display = 'none';
  _inputCallback = null;
}

function submitInput() {
  const val = inputField.value;
  hideInputModal();
  if (_inputCallback) _inputCallback(val);
}

$('btnSubmitInput').addEventListener('click', submitInput);
inputField.addEventListener('keydown', e => { if (e.key === 'Enter') submitInput(); });

// ─── Utilities ────────────────────────────────────────────────────────────

function setExecStatus(msg, type) {
  execStatus.textContent = msg;
  execStatus.className = 'exec-status';
  if (type) execStatus.classList.add(`status-${type}`);
}

function resetExecution() {
  state.sessionId = null;
  state.stepping = false;
  state._fcRendered = false;
  state.runningInputs = [];
  state.executedNodes.clear();
  state.activeNodeId = null;
  $('btnContinue').disabled = true;
  if (state._stepResetFetch) {
    fetch('/api/reset', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
  }
}

function clearAll() {
  resetExecution();
  clearOutputArea();
  irView.textContent = 'Run Analyze to see intermediate code…';
  tokenGrid.textContent = 'Run Analyze to see tokens…';
  astView.textContent = 'Run Analyze to see AST…';
  errorList.innerHTML = '<span class="output-placeholder">No errors detected.</span>';
  mermaidCont.innerHTML = '';
  fcPlaceholder.style.display = 'block';
  setExecStatus('', '');
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  const tab = document.querySelector(`.tab[data-tab="${name}"]`);
  if (tab) tab.classList.add('active');
  const pane = $(`tab-${name}`);
  if (pane) pane.classList.add('active');
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}
