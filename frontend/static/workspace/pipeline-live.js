/**
 * Pipeline Live Graph Editor
 *
 * Enhances the static pipeline page with a real interactive graph canvas.
 * Detects #/pipelines routes, adds a "Visual Editor" button, and renders
 * a draggable node + edge SVG canvas backed by GET/PUT /pipelines/{id}/graph.
 *
 * Features:
 *  - Drag nodes
 *  - Connect nodes (click source port → click target port)
 *  - Delete edges (click edge → confirm)
 *  - Node config drawer (double-click node)
 *  - Save/load graph state
 *  - Node palette (sidebar with categories)
 *  - Zoom/pan viewport
 */
(function () {
  'use strict';

  var API_BASE = window.__VEKLOM_API_BASE__ || '/api/v1';
  var EDITOR_ID = 'pipeline-graph-editor';
  var editorActive = false;
  var currentPipelineId = null;
  var graphState = { nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } };
  var connecting = null; // {sourceId, sourcePort}
  var dragging = null; // {nodeId, startX, startY, origX, origY}
  var panning = false;
  var panStart = { x: 0, y: 0 };

  async function api(method, path, body) {
    var opts = { method: method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    try {
      var r = await fetch(API_BASE + path, opts);
      if (!r.ok) return null;
      return await r.json();
    } catch (e) { return null; }
  }

  // --- Detect pipeline detail page ---
  function getCurrentPipelineId() {
    var hash = location.hash || '';
    var m = hash.match(/pipelines\/([^/]+)/);
    return m ? m[1] : null;
  }

  // --- Node colors by type ---
  var NODE_COLORS = {
    input: '#22c55e', model: '#8b5cf6', embedding: '#8b5cf6',
    gate: '#f59e0b', router: '#f59e0b', vector_store: '#06b6d4',
    retrieval: '#06b6d4', transform: '#06b6d4', tool: '#ec4899',
    output: '#ef4444', default: '#6b7280'
  };

  function nodeColor(node) {
    var t = (node.type || node.data?.nodeType || 'default').toLowerCase();
    return NODE_COLORS[t] || NODE_COLORS.default;
  }

  // --- Render SVG canvas ---
  function renderEditor() {
    var el = document.getElementById(EDITOR_ID);
    if (!el) return;
    var vp = graphState.viewport;
    var zoom = vp.zoom || 1;
    var offsetX = vp.x || 0;
    var offsetY = vp.y || 0;

    var nodesHtml = graphState.nodes.map(function (n) {
      var x = (n.position?.x || 0) * zoom + offsetX;
      var y = (n.position?.y || 0) * zoom + offsetY;
      var color = nodeColor(n);
      var label = n.data?.label || n.id;
      return '<g class="pl-node" data-id="' + n.id + '" transform="translate(' + x + ',' + y + ')">' +
        '<rect width="160" height="50" rx="8" fill="#1a1a2e" stroke="' + color + '" stroke-width="2" class="pl-node-rect"/>' +
        '<circle cx="0" cy="25" r="6" fill="' + color + '" class="pl-port pl-port-in" data-node="' + n.id + '" data-port="in"/>' +
        '<circle cx="160" cy="25" r="6" fill="' + color + '" class="pl-port pl-port-out" data-node="' + n.id + '" data-port="out"/>' +
        '<text x="80" y="30" text-anchor="middle" fill="#e2e8f0" font-size="12" font-family="Geist, sans-serif" pointer-events="none">' + label + '</text>' +
        '</g>';
    }).join('');

    var edgesHtml = graphState.edges.map(function (e) {
      var src = graphState.nodes.find(function (n) { return n.id === e.source; });
      var tgt = graphState.nodes.find(function (n) { return n.id === e.target; });
      if (!src || !tgt) return '';
      var x1 = ((src.position?.x || 0) + 160) * zoom + offsetX;
      var y1 = ((src.position?.y || 0) + 25) * zoom + offsetY;
      var x2 = (tgt.position?.x || 0) * zoom + offsetX;
      var y2 = ((tgt.position?.y || 0) + 25) * zoom + offsetY;
      var mx = (x1 + x2) / 2;
      var path = 'M' + x1 + ',' + y1 + ' C' + mx + ',' + y1 + ' ' + mx + ',' + y2 + ' ' + x2 + ',' + y2;
      var animated = e.animated ? ' class="pl-edge-animated"' : '';
      return '<path d="' + path + '" fill="none" stroke="#4b5563" stroke-width="2" data-edge="' + e.id + '"' + animated + '/>';
    }).join('');

    var svg = '<svg id="pl-canvas" width="100%" height="100%" style="position:absolute;top:0;left:0">' +
      '<defs><style>' +
      '.pl-edge-animated { stroke-dasharray: 8 4; animation: pl-dash 1s linear infinite; }' +
      '@keyframes pl-dash { to { stroke-dashoffset: -12; } }' +
      '.pl-port:hover { r: 9; cursor: crosshair; }' +
      '.pl-node-rect:hover { stroke-width: 3; }' +
      '.pl-node { cursor: grab; }' +
      '.pl-node:active { cursor: grabbing; }' +
      '</style></defs>' +
      '<g id="pl-edges">' + edgesHtml + '</g>' +
      '<g id="pl-nodes">' + nodesHtml + '</g>' +
      (connecting ? '<line id="pl-connecting-line" x1="0" y1="0" x2="0" y2="0" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5 3"/>' : '') +
      '</svg>';

    // Toolbar
    var toolbar = '<div style="position:absolute;top:12px;right:12px;display:flex;gap:8px;z-index:10">' +
      '<button id="pl-save-btn" style="padding:6px 14px;background:#22c55e;color:#000;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">Save</button>' +
      '<button id="pl-add-node-btn" style="padding:6px 14px;background:#8b5cf6;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">+ Node</button>' +
      '<button id="pl-close-btn" style="padding:6px 14px;background:#6b7280;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">Close</button>' +
      '</div>';

    // Status bar
    var status = '<div style="position:absolute;bottom:12px;left:12px;font-size:11px;color:#6b7280;font-family:Geist Mono,monospace">' +
      graphState.nodes.length + ' nodes · ' + graphState.edges.length + ' edges · zoom ' + zoom.toFixed(1) + 'x' +
      (connecting ? ' · <span style="color:#f59e0b">connecting…</span>' : '') +
      '</div>';

    el.querySelector('.pl-canvas-wrap').innerHTML = svg + toolbar + status;
    bindCanvasEvents();
  }

  // --- Event bindings ---
  function bindCanvasEvents() {
    var canvas = document.getElementById('pl-canvas');
    if (!canvas) return;

    // Node drag
    canvas.addEventListener('pointerdown', function (e) {
      var nodeG = e.target.closest('.pl-node');
      var port = e.target.closest('.pl-port');

      if (port) {
        e.stopPropagation();
        var nodeId = port.dataset.node;
        var portType = port.dataset.port;
        if (portType === 'out') {
          connecting = { sourceId: nodeId };
        } else if (portType === 'in' && connecting) {
          // Complete connection
          var edgeId = 'e-' + connecting.sourceId + '-' + nodeId + '-' + Date.now();
          graphState.edges.push({ id: edgeId, source: connecting.sourceId, target: nodeId, animated: true });
          connecting = null;
          renderEditor();
        }
        return;
      }

      if (nodeG) {
        e.stopPropagation();
        var id = nodeG.dataset.id;
        var node = graphState.nodes.find(function (n) { return n.id === id; });
        if (!node) return;
        dragging = { nodeId: id, startX: e.clientX, startY: e.clientY, origX: node.position.x, origY: node.position.y };
        return;
      }

      // Pan
      panning = true;
      panStart = { x: e.clientX - (graphState.viewport.x || 0), y: e.clientY - (graphState.viewport.y || 0) };
    });

    canvas.addEventListener('pointermove', function (e) {
      if (dragging) {
        var node = graphState.nodes.find(function (n) { return n.id === dragging.nodeId; });
        if (!node) return;
        var zoom = graphState.viewport.zoom || 1;
        node.position.x = dragging.origX + (e.clientX - dragging.startX) / zoom;
        node.position.y = dragging.origY + (e.clientY - dragging.startY) / zoom;
        renderEditor();
      }
      if (panning) {
        graphState.viewport.x = e.clientX - panStart.x;
        graphState.viewport.y = e.clientY - panStart.y;
        renderEditor();
      }
      if (connecting) {
        var line = document.getElementById('pl-connecting-line');
        if (line) {
          var rect = canvas.getBoundingClientRect();
          line.setAttribute('x2', e.clientX - rect.left);
          line.setAttribute('y2', e.clientY - rect.top);
        }
      }
    });

    canvas.addEventListener('pointerup', function () {
      dragging = null;
      panning = false;
    });

    // Zoom
    canvas.addEventListener('wheel', function (e) {
      e.preventDefault();
      var delta = e.deltaY > 0 ? -0.1 : 0.1;
      graphState.viewport.zoom = Math.max(0.3, Math.min(3, (graphState.viewport.zoom || 1) + delta));
      renderEditor();
    }, { passive: false });

    // Edge delete on click
    canvas.addEventListener('click', function (e) {
      if (e.target.tagName === 'path' && e.target.dataset.edge) {
        if (confirm('Delete this edge?')) {
          graphState.edges = graphState.edges.filter(function (edge) { return edge.id !== e.target.dataset.edge; });
          renderEditor();
        }
      }
    });

    // Double-click node for config
    canvas.addEventListener('dblclick', function (e) {
      var nodeG = e.target.closest('.pl-node');
      if (nodeG) {
        var id = nodeG.dataset.id;
        var node = graphState.nodes.find(function (n) { return n.id === id; });
        if (node) {
          var newLabel = prompt('Node label:', node.data?.label || node.id);
          if (newLabel !== null) {
            node.data = node.data || {};
            node.data.label = newLabel;
            renderEditor();
          }
        }
      }
    });

    // Toolbar buttons
    var saveBtn = document.getElementById('pl-save-btn');
    var addBtn = document.getElementById('pl-add-node-btn');
    var closeBtn = document.getElementById('pl-close-btn');

    if (saveBtn) saveBtn.onclick = async function () {
      var res = await api('PUT', '/pipelines/' + currentPipelineId + '/graph', graphState);
      if (res?.saved) {
        showToast('Graph saved (' + res.nodes_count + ' nodes, ' + res.edges_count + ' edges)', 'ok');
      }
    };

    if (addBtn) addBtn.onclick = function () { showNodePalette(); };
    if (closeBtn) closeBtn.onclick = function () { closeEditor(); };
  }

  // --- Node palette ---
  async function showNodePalette() {
    var nodesData = await api('GET', '/pipelines/nodes');
    if (!nodesData?.categories) { alert('Failed to load node database'); return; }

    var html = '<div style="position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:10001;display:flex;align-items:center;justify-content:center" id="pl-palette-overlay">' +
      '<div style="background:#1a1a2e;border:1px solid #333;border-radius:12px;padding:24px;width:560px;max-height:80vh;overflow-y:auto">' +
      '<h3 style="color:#e2e8f0;margin:0 0 16px;font-size:16px">Add Node</h3>';

    nodesData.categories.forEach(function (cat) {
      html += '<div style="margin-bottom:12px"><div style="color:#9ca3af;font-size:11px;font-weight:600;text-transform:uppercase;margin-bottom:6px">' + cat.label + '</div>';
      cat.nodes.forEach(function (n) {
        html += '<button class="pl-palette-node" data-node-id="' + n.id + '" data-node-name="' + n.name + '" data-node-type="' + n.type + '" ' +
          'style="display:block;width:100%;text-align:left;padding:8px 12px;margin-bottom:4px;background:#0f0f1a;border:1px solid #333;border-radius:6px;color:#e2e8f0;cursor:pointer;font-size:12px">' +
          '<strong>' + n.name + '</strong> <span style="color:#6b7280">— ' + n.description + '</span></button>';
      });
      html += '</div>';
    });

    html += '<button id="pl-palette-close" style="margin-top:12px;padding:8px 16px;background:#6b7280;color:#fff;border:none;border-radius:6px;cursor:pointer">Cancel</button>';
    html += '</div></div>';

    document.body.insertAdjacentHTML('beforeend', html);

    document.getElementById('pl-palette-overlay').addEventListener('click', function (e) {
      var btn = e.target.closest('.pl-palette-node');
      if (btn) {
        var newNode = {
          id: btn.dataset.nodeId + '-' + Date.now(),
          type: btn.dataset.nodeType,
          position: { x: 200 + Math.random() * 200, y: 150 + Math.random() * 200 },
          data: { label: btn.dataset.nodeName, nodeType: btn.dataset.nodeId }
        };
        graphState.nodes.push(newNode);
        document.getElementById('pl-palette-overlay').remove();
        renderEditor();
      }
      if (e.target.id === 'pl-palette-close' || e.target.id === 'pl-palette-overlay') {
        document.getElementById('pl-palette-overlay')?.remove();
      }
    });
  }

  // --- Toast ---
  function showToast(msg, type) {
    var t = document.createElement('div');
    t.style.cssText = 'position:fixed;bottom:80px;right:24px;padding:12px 20px;border-radius:8px;font-size:13px;z-index:10002;color:#fff;background:' + (type === 'ok' ? '#22c55e' : '#ef4444');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3000);
  }

  // --- Open/close editor ---
  async function openEditor(pipelineId) {
    currentPipelineId = pipelineId;
    editorActive = true;

    // Load graph
    var data = await api('GET', '/pipelines/' + pipelineId + '/graph');
    if (data) graphState = data;
    if (!graphState.viewport) graphState.viewport = { x: 50, y: 50, zoom: 1 };

    // Create editor element
    var el = document.createElement('div');
    el.id = EDITOR_ID;
    el.style.cssText = 'position:fixed;inset:0;z-index:9999;background:#0a0a1a;';
    el.innerHTML = '<div class="pl-canvas-wrap" style="width:100%;height:100%;position:relative;overflow:hidden"></div>';
    document.body.appendChild(el);

    renderEditor();
  }

  function closeEditor() {
    editorActive = false;
    currentPipelineId = null;
    var el = document.getElementById(EDITOR_ID);
    if (el) el.remove();
  }

  // --- Inject "Visual Editor" button into pipeline detail pages ---
  function injectEditorButton() {
    var pipelineId = getCurrentPipelineId();
    if (!pipelineId) return;
    if (document.getElementById('pl-open-editor-btn')) return;

    // Find a suitable place to inject — look for action buttons area
    var headers = document.querySelectorAll('h1, h2, [class*="heading"], [class*="title"]');
    var target = null;
    for (var i = 0; i < headers.length; i++) {
      if (headers[i].textContent.toLowerCase().includes('pipeline') || headers[i].closest('[class*="detail"], [class*="Pipeline"]')) {
        target = headers[i].parentElement;
        break;
      }
    }
    if (!target) {
      // Fallback: inject into first main content area
      target = document.querySelector('main') || document.querySelector('[class*="content"]') || document.querySelector('#root > div > div:nth-child(2)');
    }
    if (!target) return;

    var btn = document.createElement('button');
    btn.id = 'pl-open-editor-btn';
    btn.textContent = '◈ Visual Editor';
    btn.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);z-index:999;padding:10px 24px;background:linear-gradient(135deg,#8b5cf6,#6366f1);color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 4px 12px rgba(139,92,246,0.4)';
    btn.onclick = function () { openEditor(pipelineId); };
    document.body.appendChild(btn);
  }

  function removeEditorButton() {
    var btn = document.getElementById('pl-open-editor-btn');
    if (btn) btn.remove();
  }

  // --- Watch for route changes ---
  function onRouteChange() {
    var pipelineId = getCurrentPipelineId();
    if (pipelineId && !editorActive) {
      injectEditorButton();
    } else if (!pipelineId) {
      removeEditorButton();
      if (editorActive) closeEditor();
    }
  }

  // Init
  window.addEventListener('hashchange', onRouteChange);
  setInterval(onRouteChange, 2000);
  onRouteChange();

})();
