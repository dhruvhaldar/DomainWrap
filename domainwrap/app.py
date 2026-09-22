"""Lightweight Python web interface for DomainWrap with seamless 3D visualization."""

import argparse
import json
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from .core import generate_domain, get_geometry_info, load_surface, save_domain

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DomainWrap</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
    <style>
        :root {
            --bg-main: #090d16;
            --bg-card: #131b2e;
            --bg-card-subtle: #1c2742;
            --border-color: #273656;
            --border-highlight: #3b82f6;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --text-subtle: #64748b;
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        header {
            padding: 16px 28px;
            border-bottom: 1px solid var(--border-color);
            background-color: var(--bg-card);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header-brand {
            display: flex;
            align-items: baseline;
            gap: 12px;
        }

        h1 {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--text-main);
        }

        .subtitle {
            font-size: 13px;
            color: var(--text-muted);
        }

        .app-layout {
            display: grid;
            grid-template-columns: 440px 1fr;
            flex: 1;
            height: calc(100vh - 65px);
        }

        @media (max-width: 960px) {
            .app-layout {
                grid-template-columns: 1fr;
                height: auto;
            }
        }

        .controls-panel {
            background-color: var(--bg-card);
            border-right: 1px solid var(--border-color);
            padding: 24px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .card {
            background-color: var(--bg-card-subtle);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .card-title {
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .upload-zone {
            border: 2px dashed var(--border-color);
            border-radius: var(--radius-md);
            padding: 24px 16px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            background-color: rgba(255, 255, 255, 0.01);
        }

        .upload-zone.dragover,
        .upload-zone:hover {
            border-color: var(--border-highlight);
            background-color: rgba(59, 130, 246, 0.05);
        }

        .upload-zone-text {
            font-size: 14px;
            color: var(--text-muted);
            margin-top: 6px;
        }

        .file-status {
            font-size: 13px;
            font-weight: 500;
            color: var(--accent-cyan);
            word-break: break-all;
        }

        .hidden-input {
            display: none;
        }

        .geometry-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 12px;
        }

        .stat-item {
            background-color: var(--bg-main);
            padding: 8px 10px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
        }

        .stat-label {
            color: var(--text-subtle);
            font-size: 11px;
            text-transform: uppercase;
        }

        .stat-value {
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-main);
            margin-top: 2px;
        }

        .scaling-targets {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
        }

        .target-btn {
            background-color: var(--bg-main);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 12px;
            font-weight: 500;
            padding: 8px 4px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            text-align: center;
            transition: all 0.15s ease;
        }

        .target-btn.active {
            background-color: var(--primary);
            border-color: var(--primary);
            color: #ffffff;
        }

        .scale-input-row {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .num-input {
            background-color: var(--bg-main);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            padding: 8px 12px;
            border-radius: var(--radius-sm);
            width: 100%;
            outline: none;
        }

        .num-input:focus {
            border-color: var(--border-highlight);
        }

        .scale-presets {
            display: flex;
            gap: 6px;
        }

        .preset-btn {
            background-color: var(--bg-main);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 11px;
            padding: 4px 8px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .preset-btn:hover {
            border-color: var(--border-highlight);
            color: var(--text-main);
        }

        .slider-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .slider-control {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .slider-header {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            font-weight: 500;
        }

        .slider-label {
            color: var(--text-main);
        }

        .slider-val {
            font-family: 'JetBrains Mono', monospace;
            color: var(--accent-cyan);
        }

        .range-slider {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: var(--bg-main);
            outline: none;
            accent-color: var(--accent-cyan);
            cursor: pointer;
        }

        .options-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 13px;
        }

        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            color: var(--text-main);
        }

        .format-select {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .format-radio {
            display: flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            color: var(--text-muted);
            font-size: 13px;
        }

        .format-radio input:checked + span {
            color: var(--text-main);
            font-weight: 600;
        }

        .btn-primary {
            background-color: var(--primary);
            border: none;
            color: #ffffff;
            font-size: 14px;
            font-weight: 600;
            padding: 12px 18px;
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-primary:hover:not(:disabled) {
            background-color: var(--primary-hover);
        }

        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-secondary {
            background-color: var(--bg-card-subtle);
            border: 1px solid var(--border-color);
            color: var(--accent-green);
            font-size: 13px;
            font-weight: 600;
            padding: 10px 16px;
            border-radius: var(--radius-md);
            cursor: pointer;
            text-align: center;
            text-decoration: none;
            display: none;
            transition: all 0.15s ease;
        }

        .btn-secondary.visible {
            display: block;
        }

        .btn-secondary:hover {
            border-color: var(--accent-green);
            background-color: rgba(16, 185, 129, 0.1);
        }

        .report-box {
            background-color: var(--bg-main);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: var(--text-muted);
            min-height: 70px;
            max-height: 120px;
            overflow-y: auto;
            white-space: pre-wrap;
        }

        .viewport-container {
            position: relative;
            background-color: var(--bg-main);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        #canvas3d {
            width: 100%;
            height: 100%;
            display: block;
        }

        .viewport-toolbar {
            position: absolute;
            top: 16px;
            right: 16px;
            display: flex;
            gap: 8px;
            z-index: 10;
        }

        .tool-btn {
            background-color: rgba(19, 27, 46, 0.85);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            font-size: 12px;
            font-weight: 500;
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            backdrop-filter: blur(8px);
            transition: all 0.15s ease;
        }

        .tool-btn:hover {
            border-color: var(--border-highlight);
            color: #ffffff;
        }

        .viewport-legend {
            position: absolute;
            bottom: 16px;
            left: 16px;
            background-color: rgba(19, 27, 46, 0.85);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 8px 12px;
            font-size: 11px;
            backdrop-filter: blur(8px);
            display: flex;
            gap: 14px;
            z-index: 10;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .legend-color-source {
            width: 10px;
            height: 10px;
            background-color: #94a3b8;
            border-radius: 2px;
        }

        .legend-color-domain {
            width: 10px;
            height: 10px;
            background-color: var(--accent-cyan);
            border-radius: 2px;
        }

        .loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(9, 13, 22, 0.7);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 20;
            font-size: 14px;
            font-weight: 500;
            color: var(--text-main);
            backdrop-filter: blur(2px);
        }

        .loading-overlay.active {
            display: flex;
        }
    </style>
</head>
<body>
    <header>
        <div class="header-brand">
            <h1>DomainWrap</h1>
            <span class="subtitle">Computational boundary builder with seamless 3D visualization</span>
        </div>
    </header>

    <div class="app-layout">
        <aside class="controls-panel">
            <div class="card">
                <div class="card-title">
                    <span>Source Surface</span>
                    <span id="file-size-badge" class="file-status"></span>
                </div>
                <label id="drop-zone" class="upload-zone" for="file-input">
                    <input type="file" id="file-input" class="hidden-input" accept=".stl,.vtp">
                    <div id="upload-prompt-text" class="upload-zone-text">Click or drop .stl or .vtp file here</div>
                </label>
                <div id="geometry-stats" class="geometry-stats">
                    <div class="stat-item">
                        <div class="stat-label">Extent X</div>
                        <div id="stat-lx" class="stat-value">-</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Extent Y</div>
                        <div id="stat-ly" class="stat-value">-</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Extent Z</div>
                        <div id="stat-lz" class="stat-value">-</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Characteristic L</div>
                        <div id="stat-char" class="stat-value">-</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-title">
                    <span>Scaling</span>
                </div>
                <div class="scaling-targets">
                    <button type="button" class="target-btn active" data-target="both">Both</button>
                    <button type="button" class="target-btn" data-target="source">Source</button>
                    <button type="button" class="target-btn" data-target="domain">Domain</button>
                </div>
                <div class="scale-input-row">
                    <input type="number" id="scale-factor-input" class="num-input" value="1.0" step="0.001" min="0.00001">
                    <div class="scale-presets">
                        <button type="button" class="preset-btn" data-preset="0.001">mm→m</button>
                        <button type="button" class="preset-btn" data-preset="1000">m→mm</button>
                        <button type="button" class="preset-btn" data-preset="1.0">1.0</button>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-title">
                    <span>Boundary Offsets</span>
                    <span id="bounds-mode-indicator" class="subtitle">Relative to geometry</span>
                </div>
                <div class="slider-grid">
                    <div class="slider-control">
                        <div class="slider-header">
                            <span class="slider-label">−X (Inlet)</span>
                            <span id="val-mx" class="slider-val">500</span>
                        </div>
                        <input type="range" id="slider-mx" class="range-slider" min="0" max="10000" step="1" value="500">
                    </div>
                    <div class="slider-control">
                        <div class="slider-header">
                            <span class="slider-label">+X (Wake)</span>
                            <span id="val-px" class="slider-val">2000</span>
                        </div>
                        <input type="range" id="slider-px" class="range-slider" min="0" max="10000" step="1" value="2000">
                    </div>
                    <div class="slider-control">
                        <div class="slider-header">
                            <span class="slider-label">−Y</span>
                            <span id="val-my" class="slider-val">500</span>
                        </div>
                        <input type="range" id="slider-my" class="range-slider" min="0" max="10000" step="1" value="500">
                    </div>
                    <div class="slider-control">
                        <div class="slider-header">
                            <span class="slider-label">+Y</span>
                            <span id="val-py" class="slider-val">500</span>
                        </div>
                        <input type="range" id="slider-py" class="range-slider" min="0" max="10000" step="1" value="500">
                    </div>
                    <div class="slider-control">
                        <div class="slider-header">
                            <span class="slider-label">−Z (Ground)</span>
                            <span id="val-mz" class="slider-val">50</span>
                        </div>
                        <input type="range" id="slider-mz" class="range-slider" min="0" max="10000" step="1" value="50">
                    </div>
                    <div class="slider-control">
                        <div class="slider-header">
                            <span class="slider-label">+Z (Top)</span>
                            <span id="val-pz" class="slider-val">800</span>
                        </div>
                        <input type="range" id="slider-pz" class="range-slider" min="0" max="10000" step="1" value="800">
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-title">
                    <span>Domain Options</span>
                </div>
                <div class="options-row">
                    <label class="checkbox-label">
                        <input type="checkbox" id="check-subtract">
                        <span>Subtract model (fluid cavity)</span>
                    </label>
                    <div class="format-select">
                        <label class="format-radio">
                            <input type="radio" name="fmt" value="vtp" checked>
                            <span>VTP</span>
                        </label>
                        <label class="format-radio">
                            <input type="radio" name="fmt" value="stl">
                            <span>STL</span>
                        </label>
                    </div>
                </div>
                <button type="button" id="btn-generate" class="btn-primary" disabled>
                    <span>Generate Domain</span>
                </button>
                <a id="btn-download" class="btn-secondary" href="#" download>Download Domain</a>
            </div>

            <div class="card">
                <div class="card-title">
                    <span>Bounds and Warnings</span>
                </div>
                <div id="report-output" class="report-box">Ready. Upload an STL or VTP file to begin.</div>
            </div>
        </aside>

        <main class="viewport-container">
            <div class="viewport-toolbar">
                <button type="button" id="btn-reset-cam" class="tool-btn">Reset View</button>
                <button type="button" id="btn-toggle-wire" class="tool-btn">Edges Only</button>
            </div>
            <div class="viewport-legend">
                <div class="legend-item">
                    <div class="legend-color-source"></div>
                    <span>Obstacle Geometry</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color-domain"></div>
                    <span>Computational Domain</span>
                </div>
            </div>
            <div id="viewport-loading" class="loading-overlay">Generating domain...</div>
            <div id="canvas3d"></div>
        </main>
    </div>

    <script>
        (function() {
            if (typeof window === 'undefined' || typeof document === 'undefined') {
                return;
            }

            // State management
            var state = {
                fileId: null,
                sourceBounds: null,
                extents: null,
                scaleTarget: 'both',
                scaleFactor: 1.0,
                wireframeOnly: false
            };

            // DOM elements
            var dropZone = document.getElementById('drop-zone');
            var fileInput = document.getElementById('file-input');
            var uploadPrompt = document.getElementById('upload-prompt-text');
            var fileSizeBadge = document.getElementById('file-size-badge');
            var statLx = document.getElementById('stat-lx');
            var statLy = document.getElementById('stat-ly');
            var statLz = document.getElementById('stat-lz');
            var statChar = document.getElementById('stat-char');
            var scaleInput = document.getElementById('scale-factor-input');
            var targetBtns = document.querySelectorAll('.target-btn');
            var presetBtns = document.querySelectorAll('.preset-btn');
            var sliderMX = document.getElementById('slider-mx');
            var sliderPX = document.getElementById('slider-px');
            var sliderMY = document.getElementById('slider-my');
            var sliderPY = document.getElementById('slider-py');
            var sliderMZ = document.getElementById('slider-mz');
            var sliderPZ = document.getElementById('slider-pz');
            var valMX = document.getElementById('val-mx');
            var valPX = document.getElementById('val-px');
            var valMY = document.getElementById('val-my');
            var valPY = document.getElementById('val-py');
            var valMZ = document.getElementById('val-mz');
            var valPZ = document.getElementById('val-pz');
            var checkSubtract = document.getElementById('check-subtract');
            var btnGenerate = document.getElementById('btn-generate');
            var btnDownload = document.getElementById('btn-download');
            var reportOutput = document.getElementById('report-output');
            var btnResetCam = document.getElementById('btn-reset-cam');
            var btnToggleWire = document.getElementById('btn-toggle-wire');
            var viewportLoading = document.getElementById('viewport-loading');
            var canvasContainer = document.getElementById('canvas3d');

            // Three.js scene globals
            var scene, camera, renderer, controls;
            var obstacleMesh = null;
            var domainBoxMesh = null;
            var domainEdgesMesh = null;
            var stlLoader = null;
            var defaultCameraPosition = new THREE.Vector3(100, 100, 100);
            var defaultCameraTarget = new THREE.Vector3(0, 0, 0);

            function init3D() {
                if (canvasContainer === null || canvasContainer === undefined) return;
                var width = canvasContainer.clientWidth || 800;
                var height = canvasContainer.clientHeight || 600;

                scene = new THREE.Scene();
                scene.background = new THREE.Color(0x090d16);

                camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 100000);
                camera.position.copy(defaultCameraPosition);

                renderer = new THREE.WebGLRenderer({ antialias: true });
                renderer.setSize(width, height);
                renderer.setPixelRatio(window.devicePixelRatio || 1);
                canvasContainer.appendChild(renderer.domElement);

                controls = new THREE.OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.dampingFactor = 0.08;

                // Lighting
                var ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
                scene.add(ambientLight);

                var dirLight1 = new THREE.DirectionalLight(0xffffff, 0.7);
                dirLight1.position.set(1, 2, 3).normalize();
                scene.add(dirLight1);

                var dirLight2 = new THREE.DirectionalLight(0x94a3b8, 0.4);
                dirLight2.position.set(-1, -1, -2).normalize();
                scene.add(dirLight2);

                // Grid & Axes
                var axesHelper = new THREE.AxesHelper(50);
                scene.add(axesHelper);

                // Domain box setup (unit cube scaled dynamically)
                var boxGeom = new THREE.BoxGeometry(1, 1, 1);
                var boxMat = new THREE.MeshStandardMaterial({
                    color: 0x06b6d4,
                    transparent: true,
                    opacity: 0.3,
                    depthWrite: false,
                    roughness: 0.2
                });
                domainBoxMesh = new THREE.Mesh(boxGeom, boxMat);
                domainBoxMesh.visible = false;
                scene.add(domainBoxMesh);

                var edgesGeom = new THREE.EdgesGeometry(boxGeom);
                var edgesMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 2 });
                domainEdgesMesh = new THREE.LineSegments(edgesGeom, edgesMat);
                domainEdgesMesh.visible = false;
                scene.add(domainEdgesMesh);

                stlLoader = new THREE.STLLoader();

                window.addEventListener('resize', onWindowResize);
                animate();
            }

            function onWindowResize() {
                if (camera === null || camera === undefined || renderer === null || renderer === undefined || canvasContainer === null || canvasContainer === undefined) {
                    return;
                }
                var width = canvasContainer.clientWidth;
                var height = canvasContainer.clientHeight;
                camera.aspect = width / height;
                camera.updateProjectionMatrix();
                renderer.setSize(width, height);
            }

            function animate() {
                requestAnimationFrame(animate);
                if (controls !== null && controls !== undefined) {
                    controls.update();
                }
                if (renderer !== null && renderer !== undefined && scene !== null && scene !== undefined && camera !== null && camera !== undefined) {
                    renderer.render(scene, camera);
                }
            }

            // Real-time seamless domain box update
            function updateDomainBox() {
                if (state.sourceBounds === null || state.sourceBounds === undefined) return;
                if (domainBoxMesh === null || domainBoxMesh === undefined) return;
                if (domainEdgesMesh === null || domainEdgesMesh === undefined) return;

                var srcScale = (state.scaleTarget === 'domain') ? 1.0 : state.scaleFactor;
                var domScale = (state.scaleTarget === 'source') ? 1.0 : state.scaleFactor;

                // Scale source mesh visually if scale changed
                if (obstacleMesh !== null && obstacleMesh !== undefined) {
                    obstacleMesh.scale.set(srcScale, srcScale, srcScale);
                }

                var b = state.sourceBounds;
                var bxMin = b[0] * srcScale;
                var bxMax = b[1] * srcScale;
                var byMin = b[2] * srcScale;
                var byMax = b[3] * srcScale;
                var bzMin = b[4] * srcScale;
                var bzMax = b[5] * srcScale;

                var mx = (sliderMX !== null && sliderMX !== undefined) ? (parseFloat(sliderMX.value) || 0) * domScale : 0;
                var px = (sliderPX !== null && sliderPX !== undefined) ? (parseFloat(sliderPX.value) || 0) * domScale : 0;
                var my = (sliderMY !== null && sliderMY !== undefined) ? (parseFloat(sliderMY.value) || 0) * domScale : 0;
                var py = (sliderPY !== null && sliderPY !== undefined) ? (parseFloat(sliderPY.value) || 0) * domScale : 0;
                var mz = (sliderMZ !== null && sliderMZ !== undefined) ? (parseFloat(sliderMZ.value) || 0) * domScale : 0;
                var pz = (sliderPZ !== null && sliderPZ !== undefined) ? (parseFloat(sliderPZ.value) || 0) * domScale : 0;

                var domXMin = bxMin - mx;
                var domXMax = bxMax + px;
                var domYMin = byMin - my;
                var domYMax = byMax + py;
                var domZMin = bzMin - mz;
                var domZMax = bzMax + pz;

                var sizeX = Math.max(0.0001, domXMax - domXMin);
                var sizeY = Math.max(0.0001, domYMax - domYMin);
                var sizeZ = Math.max(0.0001, domZMax - domZMin);

                var centerX = (domXMin + domXMax) / 2.0;
                var centerY = (domYMin + domYMax) / 2.0;
                var centerZ = (domZMin + domZMax) / 2.0;

                domainBoxMesh.position.set(centerX, centerY, centerZ);
                domainBoxMesh.scale.set(sizeX, sizeY, sizeZ);
                domainBoxMesh.visible = !state.wireframeOnly;

                domainEdgesMesh.position.set(centerX, centerY, centerZ);
                domainEdgesMesh.scale.set(sizeX, sizeY, sizeZ);
                domainEdgesMesh.visible = true;

                // Update slider text displays
                if (valMX !== null && valMX !== undefined && sliderMX !== null) valMX.textContent = sliderMX.value;
                if (valPX !== null && valPX !== undefined && sliderPX !== null) valPX.textContent = sliderPX.value;
                if (valMY !== null && valMY !== undefined && sliderMY !== null) valMY.textContent = sliderMY.value;
                if (valPY !== null && valPY !== undefined && sliderPY !== null) valPY.textContent = sliderPY.value;
                if (valMZ !== null && valMZ !== undefined && sliderMZ !== null) valMZ.textContent = sliderMZ.value;
                if (valPZ !== null && valPZ !== undefined && sliderPZ !== null) valPZ.textContent = sliderPZ.value;
            }

            function loadSourceMesh(previewUrl) {
                if (stlLoader === null || stlLoader === undefined || previewUrl === undefined || previewUrl === null) return;
                stlLoader.load(previewUrl, function(geometry) {
                    if (geometry === undefined || geometry === null) return;
                    geometry.computeVertexNormals();

                    if (obstacleMesh !== null && obstacleMesh !== undefined) {
                        scene.remove(obstacleMesh);
                        if (obstacleMesh.geometry !== undefined) obstacleMesh.geometry.dispose();
                    }

                    var material = new THREE.MeshStandardMaterial({
                        color: 0x94a3b8,
                        roughness: 0.35,
                        metalness: 0.2
                    });
                    obstacleMesh = new THREE.Mesh(geometry, material);
                    scene.add(obstacleMesh);

                    updateDomainBox();
                    fitCameraToBox();
                }, undefined, function(err) {
                    console.error("Failed to load preview STL:", err);
                });
            }

            function fitCameraToBox() {
                if (domainBoxMesh === null || domainBoxMesh === undefined) return;
                if (camera === null || camera === undefined || controls === null || controls === undefined) return;

                var box = new THREE.Box3().setFromObject(domainBoxMesh);
                if (obstacleMesh !== null && obstacleMesh !== undefined) {
                    box.expandByObject(obstacleMesh);
                }

                var center = new THREE.Vector3();
                box.getCenter(center);
                var size = new THREE.Vector3();
                box.getSize(size);

                var maxDim = Math.max(size.x, size.y, size.z);
                var fov = camera.fov * (Math.PI / 180);
                var cameraDistance = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 1.6;

                defaultCameraTarget.copy(center);
                defaultCameraPosition.set(center.x + cameraDistance, center.y + cameraDistance * 0.8, center.z + cameraDistance * 1.2);

                camera.position.copy(defaultCameraPosition);
                camera.lookAt(center);
                controls.target.copy(center);
                camera.near = maxDim / 1000.0;
                camera.far = maxDim * 1000.0;
                camera.updateProjectionMatrix();
            }

            // File upload handling
            function handleFileUpload(file) {
                if (file === null || file === undefined) return;
                if (uploadPrompt !== null && uploadPrompt !== undefined) {
                    uploadPrompt.textContent = "Uploading & analyzing " + file.name + "...";
                }

                var formData = new FormData();
                formData.append('file', file);

                fetch('/api/upload', {
                    method: 'POST',
                    headers: {
                        'X-Filename': encodeURIComponent(file.name)
                    },
                    body: file
                })
                .then(function(res) {
                    if (!res.ok) throw new Error("Upload failed: HTTP " + res.status);
                    return res.json();
                })
                .then(function(data) {
                    if (data === null || data === undefined) return;
                    state.fileId = data.file_id;
                    state.sourceBounds = data.bounds;
                    state.extents = data.extents;

                    if (fileSizeBadge !== null && fileSizeBadge !== undefined) {
                        fileSizeBadge.textContent = file.name;
                    }
                    if (uploadPrompt !== null && uploadPrompt !== undefined) {
                        uploadPrompt.textContent = "Loaded: " + file.name;
                    }

                    // Populate extents
                    if (statLx !== null && statLx !== undefined) statLx.textContent = data.extents[0].toFixed(2);
                    if (statLy !== null && statLy !== undefined) statLy.textContent = data.extents[1].toFixed(2);
                    if (statLz !== null && statLz !== undefined) statLz.textContent = data.extents[2].toFixed(2);
                    var charLen = Math.max(data.extents[0], data.extents[1], data.extents[2]);
                    if (statChar !== null && statChar !== undefined) statChar.textContent = charLen.toFixed(2);

                    // Update sliders with relative defaults
                    var m = data.default_margins;
                    var maxVal = data.slider_max;
                    var stepVal = data.slider_step;

                    var sliderMap = [
                        { el: sliderMX, val: m[0] },
                        { el: sliderPX, val: m[1] },
                        { el: sliderMY, val: m[2] },
                        { el: sliderPY, val: m[3] },
                        { el: sliderMZ, val: m[4] },
                        { el: sliderPZ, val: m[5] }
                    ];

                    for (var i = 0; i < sliderMap.length; i++) {
                        var item = sliderMap[i];
                        if (item.el !== null && item.el !== undefined) {
                            item.el.min = 0;
                            item.el.max = maxVal;
                            item.el.step = stepVal;
                            item.el.value = item.val;
                        }
                    }

                    if (btnGenerate !== null && btnGenerate !== undefined) {
                        btnGenerate.disabled = false;
                    }
                    if (btnDownload !== null && btnDownload !== undefined) {
                        btnDownload.classList.remove('visible');
                    }

                    if (reportOutput !== null && reportOutput !== undefined) {
                        reportOutput.textContent = [
                            "Loaded " + file.name,
                            "Extents (Lx, Ly, Lz): " + data.extents[0].toFixed(2) + ", " + data.extents[1].toFixed(2) + ", " + data.extents[2].toFixed(2),
                            "Default relative margins initialized."
                        ].join("\\n");
                    }

                    // Load 3D preview
                    if (data.preview_url !== undefined && data.preview_url !== null) {
                        loadSourceMesh(data.preview_url);
                    }
                })
                .catch(function(err) {
                    if (reportOutput !== null && reportOutput !== undefined) {
                        reportOutput.textContent = "Error: " + err.message;
                    }
                });
            }

            // Slider events (instant real-time client-side update)
            var sliders = [sliderMX, sliderPX, sliderMY, sliderPY, sliderMZ, sliderPZ];
            for (var i = 0; i < sliders.length; i++) {
                var s = sliders[i];
                if (s !== null && s !== undefined) {
                    s.addEventListener('input', updateDomainBox);
                }
            }

            // Scaling events
            for (var j = 0; j < targetBtns.length; j++) {
                targetBtns[j].addEventListener('click', function(e) {
                    var target = e.currentTarget.getAttribute('data-target');
                    if (target === null || target === undefined) return;
                    state.scaleTarget = target;
                    for (var k = 0; k < targetBtns.length; k++) {
                        targetBtns[k].classList.remove('active');
                    }
                    e.currentTarget.classList.add('active');
                    updateDomainBox();
                });
            }

            if (scaleInput !== null && scaleInput !== undefined) {
                scaleInput.addEventListener('input', function() {
                    var val = parseFloat(scaleInput.value);
                    if (!isNaN(val) && val > 0) {
                        state.scaleFactor = val;
                        updateDomainBox();
                    }
                });
            }

            for (var p = 0; p < presetBtns.length; p++) {
                presetBtns[p].addEventListener('click', function(e) {
                    var preset = e.currentTarget.getAttribute('data-preset');
                    if (preset === null || preset === undefined) return;
                    if (scaleInput !== null && scaleInput !== undefined) {
                        scaleInput.value = preset;
                    }
                    state.scaleFactor = parseFloat(preset) || 1.0;
                    updateDomainBox();
                });
            }

            // Drag and drop & click file import
            if (dropZone !== null && dropZone !== undefined) {
                dropZone.addEventListener('dragover', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    dropZone.classList.add('dragover');
                });
                dropZone.addEventListener('dragleave', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    dropZone.classList.remove('dragover');
                });
                dropZone.addEventListener('drop', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    dropZone.classList.remove('dragover');
                    if (e.dataTransfer !== null && e.dataTransfer !== undefined && e.dataTransfer.files.length > 0) {
                        handleFileUpload(e.dataTransfer.files[0]);
                    }
                });
            }

            if (fileInput !== null && fileInput !== undefined) {
                fileInput.addEventListener('change', function(e) {
                    if (e.target !== null && e.target !== undefined && e.target.files.length > 0) {
                        handleFileUpload(e.target.files[0]);
                    }
                });
            }

            // Toolbar buttons
            if (btnResetCam !== null && btnResetCam !== undefined) {
                btnResetCam.addEventListener('click', function() {
                    if (camera !== null && camera !== undefined && controls !== null && controls !== undefined) {
                        camera.position.copy(defaultCameraPosition);
                        controls.target.copy(defaultCameraTarget);
                        camera.lookAt(defaultCameraTarget);
                    }
                });
            }

            if (btnToggleWire !== null && btnToggleWire !== undefined) {
                btnToggleWire.addEventListener('click', function() {
                    state.wireframeOnly = !state.wireframeOnly;
                    if (btnToggleWire !== null) {
                        btnToggleWire.textContent = state.wireframeOnly ? "Show Faces" : "Edges Only";
                    }
                    updateDomainBox();
                });
            }

            // Generation request
            if (btnGenerate !== null && btnGenerate !== undefined) {
                btnGenerate.addEventListener('click', function() {
                    if (state.fileId === null || state.fileId === undefined) return;
                    if (viewportLoading !== null && viewportLoading !== undefined) {
                        viewportLoading.classList.add('active');
                    }

                    var fmtRadio = document.querySelector('input[name="fmt"]:checked');
                    var outputFmt = (fmtRadio !== null && fmtRadio !== undefined) ? fmtRadio.value : 'vtp';
                    var subtractVal = (checkSubtract !== null && checkSubtract !== undefined) ? checkSubtract.checked : false;

                    var srcScale = (state.scaleTarget === 'domain') ? 1.0 : state.scaleFactor;
                    var domScale = (state.scaleTarget === 'source') ? 1.0 : state.scaleFactor;

                    var payload = {
                        file_id: state.fileId,
                        margins: [
                            parseFloat(sliderMX.value) || 0,
                            parseFloat(sliderPX.value) || 0,
                            parseFloat(sliderMY.value) || 0,
                            parseFloat(sliderPY.value) || 0,
                            parseFloat(sliderMZ.value) || 0,
                            parseFloat(sliderPZ.value) || 0
                        ],
                        subtract: subtractVal,
                        format: outputFmt,
                        source_scale: srcScale,
                        domain_scale: domScale
                    };

                    fetch('/api/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    })
                    .then(function(res) {
                        if (!res.ok) return res.json().then(function(d) { throw new Error(d.error || ("HTTP " + res.status)); });
                        return res.json();
                    })
                    .then(function(data) {
                        if (viewportLoading !== null && viewportLoading !== undefined) {
                            viewportLoading.classList.remove('active');
                        }
                        if (data === null || data === undefined) return;

                        if (reportOutput !== null && reportOutput !== undefined) {
                            reportOutput.textContent = data.report || "Domain generated successfully.";
                        }

                        if (btnDownload !== null && btnDownload !== undefined && data.download_url !== undefined && data.download_url !== null) {
                            btnDownload.href = data.download_url;
                            btnDownload.classList.add('visible');
                            btnDownload.textContent = "Download fluid_domain." + outputFmt;
                        }
                    })
                    .catch(function(err) {
                        if (viewportLoading !== null && viewportLoading !== undefined) {
                            viewportLoading.classList.remove('active');
                        }
                        if (reportOutput !== null && reportOutput !== undefined) {
                            reportOutput.textContent = "Generation failed: " + err.message;
                        }
                    });
                });
            }

            init3D();
        })();
    </script>
</body>
</html>
"""


def build(
    input_file: str | Path,
    mx: float,
    px: float,
    my: float,
    py: float,
    mz: float,
    pz: float,
    subtract: bool = False,
    output_format: str = "vtp",
    source_scale: float = 1.0,
    domain_scale: float = 1.0,
) -> tuple[str, str, str]:
    """Compatibility entry point for tests and headless automation."""
    if not input_file:
        raise ValueError("Upload an STL or VTP file first")
    result = generate_domain(
        input_file,
        (float(mx), float(px), float(my), float(py), float(mz), float(pz)),
        subtract=subtract,
        source_scale=float(source_scale),
        domain_scale=float(domain_scale),
    )
    directory = Path(tempfile.mkdtemp(prefix="domainwrap-"))
    output = save_domain(result.mesh, directory / f"fluid_domain.{output_format}")
    preview = save_domain(result.mesh, directory / "preview.stl")
    report = (
        f"Source bounds: {result.source_bounds}\n"
        f"Domain bounds: {result.domain_bounds}\n"
        + "\n".join(result.warnings)
    )
    return str(preview), str(output), report


class DomainWrapHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for DomainWrap web interface."""

    server: "DomainWrapServer"

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ("", "/"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if path.startswith("/api/preview/"):
            file_id = path[len("/api/preview/"):]
            file_path = self.server.files.get(file_id)
            if file_path is None or not file_path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "Preview file not found")
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "model/stl")
            self.send_header("Content-Length", str(file_path.stat().st_size))
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
            return

        if path.startswith("/api/download/"):
            parts = path[len("/api/download/"):].split("/")
            file_id = parts[0]
            file_path = self.server.files.get(file_id)
            if file_path is None or not file_path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "Download file not found")
                return
            filename = parts[1] if len(parts) > 1 else file_path.name
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(file_path.stat().st_size))
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))

        if path == "/api/upload":
            raw_filename = self.headers.get("X-Filename", "surface.stl")
            filename = unquote(raw_filename)
            ext = Path(filename).suffix.lower()
            if ext not in (".stl", ".vtp"):
                self._send_json({"error": "Only .stl and .vtp files are supported"}, status=HTTPStatus.BAD_REQUEST)
                return

            body = self.rfile.read(content_length)
            temp_dir = Path(tempfile.mkdtemp(prefix="domainwrap-upload-", dir=self.server.temp_dir))
            saved_path = temp_dir / filename
            saved_path.write_bytes(body)

            try:
                info = get_geometry_info(saved_path)
                mesh = load_surface(saved_path)
                preview_id = f"prev_{temp_dir.name}"
                preview_path = temp_dir / "preview_source.stl"
                save_domain(mesh, preview_path)
                self.server.files[preview_id] = preview_path
                self.server.files[temp_dir.name] = saved_path

                response_data = {
                    "file_id": temp_dir.name,
                    "filename": filename,
                    "bounds": info["bounds"],
                    "extents": info["extents"],
                    "default_margins": info["default_margins"],
                    "slider_max": info["slider_max"],
                    "slider_step": info["slider_step"],
                    "preview_url": f"/api/preview/{preview_id}",
                }
                self._send_json(response_data)
            except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/generate":
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                file_id = data.get("file_id")
                input_path = self.server.files.get(file_id)
                if input_path is None or not input_path.is_file():
                    self._send_json({"error": "Uploaded file not found"}, status=HTTPStatus.BAD_REQUEST)
                    return

                raw_m = data.get("margins", [500, 2000, 500, 500, 50, 800])
                margins = (
                    float(raw_m[0]), float(raw_m[1]),
                    float(raw_m[2]), float(raw_m[3]),
                    float(raw_m[4]), float(raw_m[5]),
                )
                subtract = bool(data.get("subtract", False))
                output_fmt = data.get("format", "vtp").lower()
                source_scale = float(data.get("source_scale", 1.0))
                domain_scale = float(data.get("domain_scale", 1.0))

                result = generate_domain(
                    input_path,
                    margins,
                    subtract=subtract,
                    source_scale=source_scale,
                    domain_scale=domain_scale,
                )

                gen_dir = Path(tempfile.mkdtemp(prefix="domainwrap-gen-", dir=self.server.temp_dir))
                out_filename = f"fluid_domain.{output_fmt}"
                output_file = save_domain(result.mesh, gen_dir / out_filename)
                preview_file = save_domain(result.mesh, gen_dir / "preview.stl")

                dl_id = f"dl_{gen_dir.name}"
                prev_id = f"prev_{gen_dir.name}"
                self.server.files[dl_id] = output_file
                self.server.files[prev_id] = preview_file

                report = (
                    f"Source bounds: {result.source_bounds}\n"
                    f"Domain bounds: {result.domain_bounds}\n"
                    + "\n".join(result.warnings)
                )

                self._send_json({
                    "download_url": f"/api/download/{dl_id}/{out_filename}",
                    "preview_url": f"/api/preview/{prev_id}",
                    "source_bounds": result.source_bounds,
                    "domain_bounds": result.domain_bounds,
                    "warnings": result.warnings,
                    "report": report,
                })
            except (ValueError, RuntimeError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def _send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress noisy request logs in production console."""
        return


class DomainWrapServer(ThreadingHTTPServer):
    """Threading HTTP Server holding application state and temp files."""

    def __init__(self, server_address: tuple[str, int]) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="domainwrap-server-"))
        self.files: dict[str, Path] = {}
        super().__init__(server_address, DomainWrapHandler)

    def launch(self, server_name: str | None = None, server_port: int | None = None) -> None:
        host = server_name if server_name is not None else self.server_address[0]
        port = server_port if server_port is not None else self.server_address[1]
        print(f"DomainWrap running on http://{host}:{port}")
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            self.server_close()


def create_app(host: str = "127.0.0.1", port: int = 7860) -> DomainWrapServer:
    """Create server instance."""
    return DomainWrapServer((host, port))


def main() -> None:
    parser = argparse.ArgumentParser(description="DomainWrap Web Interface")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    server = create_app(host=args.host, port=args.port)
    server.launch()


if __name__ == "__main__":
    main()
