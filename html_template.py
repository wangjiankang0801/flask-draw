# html_template.py
# 优化后的前端页面模板，支持文生图/图生图、AI优化、历史记录

HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>AI画图工坊 · 智能优化</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { width: 100%; height: 100%; min-height: 100dvh; overflow: hidden; }
        :root {
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --success: #22c55e;
            --success-light: #86efac;
            --bg: #f5f7fb;
            --card: #ffffff;
            --gray-1: #f8fafc;
            --gray-2: #f1f5f9;
            --border: #cbd5e1;
            --text-deep: #0f172a;
            --text-gray: #475569;
            --text-light: #5b6e8c;
            --text-minor: #94a3b8;
            --shadow: 0 12px 30px rgba(0,0,0,0.08);
            --transition: 0.2s ease;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            display: flex; align-items: center; justify-content: center;
            padding: 20px 20px max(20px, env(safe-area-inset-bottom)) 20px;
        }
        .card {
            max-width: 760px; width: 100%;
            background: var(--card); border-radius: 40px; box-shadow: var(--shadow);
            padding: 28px 32px 24px;
            display: flex; flex-direction: column;
            height: calc(100dvh - 40px); max-height: calc(100dvh - 40px);
            min-height: 0; flex-shrink: 0;
        }
        .content-wrapper {
            flex: 1; display: flex; flex-direction: column;
            overflow-y: auto; overflow-x: hidden; padding-bottom: 16px;
            -webkit-overflow-scrolling: touch;
        }
        .content-wrapper::-webkit-scrollbar { display: none; }
        .content-wrapper { -ms-overflow-style: none; scrollbar-width: none; }
        h2 { font-size: 1.8rem; font-weight: 700; color: var(--text-deep); margin-bottom: 4px; flex-shrink: 0; }
        .sub { font-size: 0.9rem; color: var(--text-light); border-left: 3px solid var(--border); padding-left: 12px; margin-bottom: 24px; flex-shrink: 0; }
        .ai-placeholder { min-height: 64px; margin-bottom: 12px; flex-shrink: 0; }
        .ai-note { background: #e6f7ec; padding: 12px 18px; border-radius: 24px; font-size: 0.85rem; color: #166534; border-left: 4px solid var(--success); transition: opacity 0.2s; }
        .ai-note.hidden-vis { visibility: hidden; opacity: 0; }
        .toggle-row { display: flex; align-items: center; justify-content: space-between; background: var(--gray-2); padding: 12px 20px; border-radius: 60px; margin-bottom: 28px; flex-shrink: 0; }
        .toggle-label { font-weight: 600; font-size: 1rem; color: var(--text-deep); }
        .toggle-switch { position: relative; display: inline-block; width: 52px; height: 28px; flex-shrink: 0; }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: var(--border); transition: var(--transition); border-radius: 28px; }
        .slider:before { position: absolute; content: ""; height: 24px; width: 24px; left: 2px; bottom: 2px; background: white; transition: var(--transition); border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
        input:checked + .slider { background: var(--success-light); }
        input:checked + .slider:before { transform: translateX(24px); }
        .mode-buttons { display: flex; gap: 24px; margin-bottom: 24px; background: var(--gray-1); padding: 10px 20px; border-radius: 60px; width: 100%; justify-content: center; flex-wrap: wrap; flex-shrink: 0; }
        .mode-buttons label { display: inline-flex; align-items: center; gap: 6px; font-weight: 500; cursor: pointer; white-space: nowrap; font-size: 1rem; }
        .mode-buttons input { margin: 0; transform: scale(1.1); }
        .params-panel { background: var(--gray-1); border-radius: 32px; padding: 18px 24px; margin-bottom: 24px; transition: visibility 0.2s, opacity 0.2s; flex-shrink: 0; }
        .params-panel.param-hidden { visibility: hidden; opacity: 0; height: 0; padding: 0; margin: 0; overflow: hidden; }
        .param-row { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 16px; }
        .param-row:last-child { margin-bottom: 0; }
        .param-group { flex: 1; min-width: 120px; }
        .param-group label { display: block; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; color: var(--text-gray); margin-bottom: 5px; }
        select { width: 100%; padding: 8px 12px; border-radius: 28px; border: 1px solid var(--border); background: white; font-size: 0.9rem; outline: none; }
        .upload-section { background: #fef9e3; border-radius: 28px; padding: 16px 20px; margin-bottom: 18px; display: none; flex-shrink: 0; }
        .upload-section.active { display: block; }
        .preview-container { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }
        .preview-wrapper { position: relative; }
        .preview-img { width: 80px; height: 80px; object-fit: cover; border-radius: 16px; border: 1px solid #ddd; }
        .preview-del-btn { position: absolute; top: 2px; right: 2px; width: 20px; height: 20px; background: rgba(0,0,0,0.5); color: white; border: none; border-radius: 50%; cursor: pointer; font-size: 12px; line-height: 1; }
        textarea { width: 100%; padding: 12px 16px; border-radius: 28px; border: 1px solid var(--border); font-size: 0.95rem; resize: none; font-family: inherit; outline: none; transition: height 0.1s ease; flex-shrink: 0; }
        textarea:focus { border-color: var(--primary); }
        .btn-generate { width: 100%; padding: 14px; font-size: 1.1rem; font-weight: 600; border: none; border-radius: 44px; background: var(--primary); color: white; cursor: pointer; margin-top: 18px; transition: var(--transition); flex-shrink: 0; }
        .btn-generate:hover { background: var(--primary-hover); }
        .btn-generate:disabled { background: #94a3b8; cursor: not-allowed; }
        .footnote { font-size: 0.7rem; text-align: center; color: var(--text-minor); margin-top: 16px; flex-shrink: 0; }
        .results-section { margin-top: 28px; border-top: 1px solid var(--border); padding-top: 24px; }
        .results-title { font-size: 1.2rem; font-weight: 600; margin-bottom: 12px; color: var(--text-deep); }
        .results-grid { display: flex; flex-wrap: wrap; gap: 16px; }
        .result-card { display: flex; flex-direction: column; align-items: center; }
        .result-img { width: 200px; height: 200px; object-fit: cover; border-radius: 20px; border: 1px solid var(--border); cursor: pointer; transition: transform 0.15s; }
        .result-img:hover { transform: scale(1.02); }
        .catbox-link { font-size: 0.75rem; color: var(--primary); margin-top: 6px; text-decoration: none; }
        .catbox-link:hover { text-decoration: underline; }
        .history-prompt { font-size: 0.7rem; color: var(--text-gray); max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 4px; }
        .history-meta { font-size: 0.65rem; color: var(--text-minor); }
        .error-message { margin-top: 20px; padding: 14px 18px; background: #fee2e2; border-radius: 24px; color: #b91c1c; font-weight: 500; border-left: 4px solid #ef4444; }
        .image-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; justify-content: center; align-items: center; }
        .image-modal.active { display: flex; }
        .image-modal img { max-width: 90vw; max-height: 90vh; border-radius: 20px; box-shadow: 0 0 30px rgba(0,0,0,0.5); }
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 1000; visibility: hidden; opacity: 0; transition: var(--transition); }
        .modal-overlay.active { visibility: visible; opacity: 1; }
        .modal-card { background: white; max-width: 500px; width: 90%; border-radius: 48px; padding: 28px; }
        .modal-card h3 { font-size: 1.6rem; font-weight: 600; margin-bottom: 16px; }
        .modal-params { background: var(--gray-2); border-radius: 28px; padding: 18px; margin: 20px 0; line-height: 1.6; }
        .button-group { display: flex; gap: 12px; justify-content: flex-end; }
        .btn-confirm { background: var(--success-light); border: none; padding: 8px 24px; border-radius: 40px; font-weight: 600; cursor: pointer; }
        .btn-cancel { background: var(--border); border: none; padding: 8px 24px; border-radius: 40px; font-weight: 600; cursor: pointer; }
        @media (max-width: 600px) {
            .card { padding: 20px; border-radius: 30px; }
            h2 { font-size: 1.5rem; }
            .result-img { width: 150px; height: 150px; }
            .mode-buttons { gap: 12px; }
        }
    </style>
</head>
<body>
<div class="card">
    <div class="content-wrapper">
        <h2>🎨 AI画图工坊</h2>
        <div class="sub">自然语言绘图 · 智能增强</div>

        <div class="ai-placeholder">
            <div id="aiNote" class="ai-note hidden-vis">
                ✨ 已启用 AI 智能优化：您的描述会被自动转换为高质量绘画参数。
            </div>
        </div>

        <div class="toggle-row">
            <span class="toggle-label">✨ 启用 AI 优化</span>
            <label class="toggle-switch">
                <input type="checkbox" id="aiOptimizeToggle">
                <span class="slider"></span>
            </label>
        </div>

        <div class="mode-buttons">
            <label><input type="radio" name="mode" value="text2image" checked> 文生图</label>
            <label><input type="radio" name="mode" value="image2image"> 图生图</label>
        </div>

        <div id="paramsPanel" class="params-panel">
            <div class="param-row">
                <div class="param-group">
                    <label>📐 尺寸</label>
                    <select id="sizeSelect">
                        <option value="256">256x256</option>
                        <option value="512" selected>512x512</option>
                        <option value="1024">1024x1024</option>
                    </select>
                </div>
                <div class="param-group">
                    <label>🎨 风格</label>
                    <select id="styleSelect">
                        <option value="realistic">写实</option>
                        <option value="anime">二次元</option>
                        <option value="digital-painting">数字绘画</option>
                        <option value="oil-painting">油画</option>
                        <option value="pixel-art">像素风</option>
                    </select>
                </div>
            </div>
            <div class="param-row">
                <div class="param-group">
                    <label>🔢 数量</label>
                    <select id="numSelect">
                        <option value="1">1张</option>
                        <option value="2">2张</option>
                        <option value="3">3张</option>
                    </select>
                </div>
                <div class="param-group">
                    <label>⚙️ 细节步数</label>
                    <select id="stepsSelect">
                        <option value="30">30 - 快速</option>
                        <option value="50" selected>50 - 标准</option>
                        <option value="100">100 - 高细节</option>
                    </select>
                </div>
            </div>
        </div>

        <div id="uploadArea" class="upload-section">
            <div>📷 上传参考图片（可多张）</div>
            <input type="file" id="imageInput" accept="image/*" multiple>
            <div id="previewContainer" class="preview-container"></div>
        </div>

        <textarea id="promptInput" rows="4" placeholder="描述你想画的内容，例如：一只穿着宇航服的柴犬，在火星上，赛博朋克风格"></textarea>

        <div id="historyContainer"></div>
        <div id="resultsContainer"></div>
    </div>

    <button id="generateBtn" class="btn-generate">✨ 生成图片</button>
    <div class="footnote">* 开启AI优化后，点击生成会展示优化后的参数确认框</div>
</div>

<div id="imageModal" class="image-modal" onclick="closeImageModal()">
    <img id="imageModalImg" src="" alt="放大图片">
</div>

<div id="confirmModal" class="modal-overlay">
    <div class="modal-card">
        <h3>📝 是否生成以下内容？</h3>
        <div class="modal-params">
            <p><strong>✨ 优化后提示词：</strong><br><span id="optPromptText">—</span></p>
            <p><strong>📏 尺寸：</strong> <span id="optSize">512x512</span> &nbsp;|&nbsp;
               <strong>🎨 风格：</strong> <span id="optStyle">写实</span> &nbsp;|&nbsp;
               <strong>🔢 数量：</strong> <span id="optNum">1</span> &nbsp;|&nbsp;
               <strong>⚙️ 步数：</strong> <span id="optSteps">50</span>
            </p>
        </div>
        <div class="button-group">
            <button id="modalCancelBtn" class="btn-cancel">取消</button>
            <button id="modalConfirmBtn" class="btn-confirm">确认生成</button>
        </div>
    </div>
</div>

<script>
    function openImageModal(src) {
        document.getElementById('imageModalImg').src = src;
        document.getElementById('imageModal').classList.add('active');
    }
    function closeImageModal() {
        document.getElementById('imageModal').classList.remove('active');
    }

    const aiToggle = document.getElementById('aiOptimizeToggle');
    const aiNoteDiv = document.getElementById('aiNote');
    const paramsPanel = document.getElementById('paramsPanel');
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    const uploadArea = document.getElementById('uploadArea');
    const imageInput = document.getElementById('imageInput');
    const previewContainer = document.getElementById('previewContainer');
    const generateBtn = document.getElementById('generateBtn');
    const modal = document.getElementById('confirmModal');
    const modalCancel = document.getElementById('modalCancelBtn');
    const modalConfirm = document.getElementById('modalConfirmBtn');
    const promptInput = document.getElementById('promptInput');
    const sizeSelect = document.getElementById('sizeSelect');
    const styleSelect = document.getElementById('styleSelect');
    const numSelect = document.getElementById('numSelect');
    const stepsSelect = document.getElementById('stepsSelect');

    let selectedFiles = [];

    function updatePreview() {
        previewContainer.innerHTML = '';
        selectedFiles.forEach((file, idx) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.className = 'preview-img';
                const delBtn = document.createElement('button');
                delBtn.innerText = '✕';
                delBtn.className = 'preview-del-btn';
                delBtn.onclick = () => { selectedFiles.splice(idx, 1); updatePreview(); syncFileInput(); };
                const wrapper = document.createElement('div');
                wrapper.className = 'preview-wrapper';
                wrapper.appendChild(img);
                wrapper.appendChild(delBtn);
                previewContainer.appendChild(wrapper);
            };
            reader.readAsDataURL(file);
        });
    }
    function syncFileInput() {
        const dt = new DataTransfer();
        selectedFiles.forEach(f => dt.items.add(f));
        imageInput.files = dt.files;
    }
    imageInput.addEventListener('change', (e) => {
        Array.from(e.target.files).forEach(file => {
            if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) selectedFiles.push(file);
        });
        updatePreview(); syncFileInput();
    });

    function toggleUploadArea() {
        const mode = document.querySelector('input[name="mode"]:checked').value;
        uploadArea.classList.toggle('active', mode === 'image2image');
    }
    modeRadios.forEach(r => r.addEventListener('change', toggleUploadArea));

    function updateAIUI() {
        const isEnabled = aiToggle.checked;
        aiNoteDiv.classList.toggle('hidden-vis', !isEnabled);
        paramsPanel.classList.toggle('param-hidden', isEnabled);
    }
    aiToggle.addEventListener('change', updateAIUI);

    function getFormData() {
        const mode = document.querySelector('input[name="mode"]:checked').value;
        const prompt = promptInput.value.trim();
        if (!prompt) return null;
        const formData = new FormData();
        formData.append('mode', mode);
        formData.append('prompt', prompt);
        formData.append('size', sizeSelect.value);
        formData.append('style', styleSelect.value);
        formData.append('num', numSelect.value);
        formData.append('steps', stepsSelect.value);
        for (let file of selectedFiles) formData.append('image_files', file);
        return formData;
    }

    async function callOptimize(prompt, mode) {
        const resp = await fetch('/optimize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt, mode }) });
        const data = await resp.json();
        if (!data.success) throw new Error(data.error);
        return data;
    }

    function renderResults(results) {
        const container = document.getElementById('resultsContainer');
        let html = '';
        if (results && results.length > 0) {
            html += '<div class="results-section"><div class="results-title">🖼️ 生成结果</div><div class="results-grid">';
            results.forEach(item => {
                html += '<div class="result-card">';
                html += '<img class="result-img" src="' + item.display_url + '" onclick="openImageModal(this.src)" alt="生成图片">';
                if (item.catbox_url) html += '<a class="catbox-link" href="' + item.catbox_url + '" target="_blank">🔗 永久链接</a>';
                html += '</div>';
            });
            html += '</div></div>';
        }
        container.innerHTML = html;
    }

    async function submitGenerate(formData) {
        generateBtn.disabled = true;
        generateBtn.textContent = '⏳ 生成中…';
        try {
            const resp = await fetch('/generate', { method: 'POST', body: formData });
            const data = await resp.json();
            if (!data.success) throw new Error(data.error || '生成失败');
            renderResults(data.results);
            loadHistory();
        } catch (err) {
            document.getElementById('resultsContainer').innerHTML = '<div class="error-message">' + err.message + '</div>';
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = '✨ 生成图片';
        }
    }

    async function loadHistory() {
        try {
            const resp = await fetch('/api/history');
            const history = await resp.json();
            renderHistory(history);
        } catch (e) { console.error('加载历史失败', e); }
    }

    function renderHistory(history) {
        const container = document.getElementById('historyContainer');
        let html = '<div class="results-section"><div class="results-title">📚 历史记录</div>';
        if (!history || history.length === 0) {
            html += '<p style="color: var(--text-minor); font-size: 0.85rem; margin-top: 8px;">暂无历史记录</p>';
        } else {
            html += '<div class="results-grid">';
            history.forEach(item => {
                html += '<div class="result-card">';
                html += '<img class="result-img" src="' + item.catbox_url + '" onclick="openImageModal(this.src)" alt="' + item.prompt + '">';
                html += '<div class="history-prompt" title="' + item.prompt + '">' + item.prompt.substring(0, 20) + '...</div>';
                html += '<div class="history-meta">' + item.size + 'x' + item.size + ' | ' + item.style + '</div>';
                html += '</div>';
            });
            html += '</div>';
        }
        html += '</div>';
        container.innerHTML = html;
    }

    function showConfirmModal(opt) {
        document.getElementById('optPromptText').innerText = opt.optimized_prompt;
        document.getElementById('optSize').innerText = opt.size;
        const styleMap = { 'realistic':'写实', 'anime':'二次元', 'digital-painting':'数字绘画', 'oil-painting':'油画', 'pixel-art':'像素风' };
        document.getElementById('optStyle').innerText = styleMap[opt.style] || opt.style;
        document.getElementById('optNum').innerText = opt.num;
        document.getElementById('optSteps').innerText = opt.steps;
        modal.classList.add('active');
    }

    generateBtn.addEventListener('click', async () => {
        const rawFormData = getFormData();
        if (!rawFormData) { alert("请输入提示词"); return; }
        if (!aiToggle.checked) {
            await submitGenerate(rawFormData);
        } else {
            try {
                const optResult = await callOptimize(rawFormData.get('prompt'), rawFormData.get('mode'));
                window.currentOptimized = { mode: rawFormData.get('mode'), ...optResult, image_files: selectedFiles.slice() };
                showConfirmModal(window.currentOptimized);
            } catch (err) { alert("优化失败：" + err.message); }
        }
    });

    modalConfirm.addEventListener('click', async () => {
        modal.classList.remove('active');
        if (!window.currentOptimized) return;
        const opt = window.currentOptimized;
        const formData = new FormData();
        formData.append('mode', opt.mode);
        formData.append('prompt', opt.optimized_prompt);
        formData.append('size', opt.size);
        formData.append('style', opt.style);
        formData.append('num', opt.num);
        formData.append('steps', opt.steps);
        for (let file of opt.image_files) formData.append('image_files', file);
        await submitGenerate(formData);
        window.currentOptimized = null;
    });
    modalCancel.addEventListener('click', () => modal.classList.remove('active'));
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('active'); });

    toggleUploadArea();
    updateAIUI();
    loadHistory();
</script>
</body>
</html>
"""
