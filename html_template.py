# html_template.py
# 前端页面模板 - 支持宽高比、DeepSeek-V4优化、历史记录删除

HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>AI画图工坊</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        html,body{width:100%;height:100%;min-height:100dvh;overflow:hidden}
        :root{--primary:#3b82f6;--primary-hover:#2563eb;--success:#22c55e;--success-light:#86efac;--bg:#f5f7fb;--card:#fff;--gray-1:#f8fafc;--gray-2:#f1f5f9;--border:#cbd5e1;--text-deep:#0f172a;--text-gray:#475569;--text-light:#5b6e8c;--text-minor:#94a3b8;--shadow:0 12px 30px rgba(0,0,0,.08);--transition:.2s ease;--red:#ef4444;--red-light:#fee2e2}
        body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);display:flex;align-items:center;justify-content:center;padding:20px 20px max(20px,env(safe-area-inset-bottom)) 20px}
        .card{max-width:760px;width:100%;background:var(--card);border-radius:40px;box-shadow:var(--shadow);padding:28px 32px 24px;display:flex;flex-direction:column;height:calc(100dvh - 40px);max-height:calc(100dvh - 40px);min-height:0;flex-shrink:0;position:relative}
        .content-wrapper{flex:1;display:flex;flex-direction:column;overflow-y:auto;overflow-x:hidden;padding-bottom:16px;-webkit-overflow-scrolling:touch}
        .content-wrapper::-webkit-scrollbar{display:none}
        .content-wrapper{-ms-overflow-style:none;scrollbar-width:none}
        .top-bar{display:flex;justify-content:space-between;align-items:flex-start;flex-shrink:0;margin-bottom:4px}
        h2{font-size:1.8rem;font-weight:700;color:var(--text-deep)}
        .btn-history{background:var(--gray-2);border:none;padding:10px 20px;border-radius:60px;font-size:.9rem;font-weight:600;color:var(--text-gray);cursor:pointer;transition:var(--transition);white-space:nowrap;margin-top:6px}
        .btn-history:hover{background:var(--border);color:var(--text-deep)}
        .sub{font-size:.9rem;color:var(--text-light);border-left:3px solid var(--border);padding-left:12px;margin-bottom:24px;flex-shrink:0}
        .ai-placeholder{min-height:64px;margin-bottom:12px;flex-shrink:0}
        .ai-note{background:#e6f7ec;padding:12px 18px;border-radius:24px;font-size:.85rem;color:#166534;border-left:4px solid var(--success);transition:opacity .2s}
        .ai-note.hidden-vis{visibility:hidden;opacity:0}
        .toggle-row{display:flex;align-items:center;justify-content:space-between;background:var(--gray-2);padding:12px 20px;border-radius:60px;margin-bottom:28px;flex-shrink:0}
        .toggle-label{font-weight:600;font-size:1rem;color:var(--text-deep)}
        .toggle-switch{position:relative;display:inline-block;width:52px;height:28px;flex-shrink:0}
        .toggle-switch input{opacity:0;width:0;height:0}
        .slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:var(--border);transition:var(--transition);border-radius:28px}
        .slider:before{position:absolute;content:"";height:24px;width:24px;left:2px;bottom:2px;background:#fff;transition:var(--transition);border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.2)}
        input:checked+.slider{background:var(--success-light)}
        input:checked+.slider:before{transform:translateX(24px)}
        .mode-buttons{display:flex;gap:24px;margin-bottom:24px;background:var(--gray-1);padding:10px 20px;border-radius:60px;width:100%;justify-content:center;flex-wrap:wrap;flex-shrink:0}
        .mode-buttons label{display:inline-flex;align-items:center;gap:6px;font-weight:500;cursor:pointer;white-space:nowrap;font-size:1rem}
        .mode-buttons input{margin:0;transform:scale(1.1)}
        .params-panel{background:var(--gray-1);border-radius:32px;padding:18px 24px;margin-bottom:24px;transition:visibility .2s,opacity .2s;flex-shrink:0}
        .params-panel.param-hidden{visibility:hidden;opacity:0;height:0;padding:0;margin:0;overflow:hidden}
        .param-row{display:flex;flex-wrap:wrap;gap:20px;margin-bottom:16px}
        .param-row:last-child{margin-bottom:0}
        .param-group{flex:1;min-width:120px}
        .param-group label{display:block;font-size:.7rem;font-weight:600;text-transform:uppercase;color:var(--text-gray);margin-bottom:5px}
        select{width:100%;padding:8px 12px;border-radius:28px;border:1px solid var(--border);background:#fff;font-size:.9rem;outline:none}
        .upload-section{background:#fef9e3;border-radius:28px;padding:16px 20px;margin-bottom:18px;display:none;flex-shrink:0}
        .upload-section.active{display:block}
        .preview-container{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px}
        .preview-wrapper{position:relative}
        .preview-img{width:80px;height:80px;object-fit:cover;border-radius:16px;border:1px solid #ddd}
        .preview-del-btn{position:absolute;top:2px;right:2px;width:20px;height:20px;background:rgba(0,0,0,.5);color:#fff;border:none;border-radius:50%;cursor:pointer;font-size:12px;line-height:1}
        textarea{width:100%;padding:12px 16px;border-radius:28px;border:1px solid var(--border);font-size:.95rem;resize:none;font-family:inherit;outline:none;transition:height .1s ease;flex-shrink:0}
        textarea:focus{border-color:var(--primary)}
        .btn-generate{width:100%;padding:14px;font-size:1.1rem;font-weight:600;border:none;border-radius:44px;background:var(--primary);color:#fff;cursor:pointer;margin-top:18px;transition:var(--transition);flex-shrink:0}
        .btn-generate:hover{background:var(--primary-hover)}
        .btn-generate:disabled{background:#94a3b8;cursor:not-allowed}
        .footnote{font-size:.7rem;text-align:center;color:var(--text-minor);margin-top:16px;flex-shrink:0}
        .results-section{margin-top:28px;border-top:1px solid var(--border);padding-top:24px}
        .results-title{font-size:1.2rem;font-weight:600;margin-bottom:12px;color:var(--text-deep)}
        .results-grid{display:flex;flex-wrap:wrap;gap:16px}
        .result-card{display:flex;flex-direction:column;align-items:center}
        .result-img{width:200px;height:200px;object-fit:cover;border-radius:20px;border:1px solid var(--border);cursor:pointer;transition:transform .15s}
        .result-img:hover{transform:scale(1.02)}
        .catbox-link{font-size:.75rem;color:var(--primary);margin-top:6px;text-decoration:none}
        .catbox-link:hover{text-decoration:underline}
        .error-message{margin-top:20px;padding:14px 18px;background:var(--red-light);border-radius:24px;color:#b91c1c;font-weight:500;border-left:4px solid var(--red)}
        .image-modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.85);z-index:9999;justify-content:center;align-items:center}
        .image-modal.active{display:flex}
        .image-modal img{max-width:90vw;max-height:90vh;border-radius:20px;box-shadow:0 0 30px rgba(0,0,0,.5)}
        .modal-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.4);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:1000;visibility:hidden;opacity:0;transition:var(--transition)}
        .modal-overlay.active{visibility:visible;opacity:1}
        .modal-card{background:#fff;max-width:500px;width:90%;border-radius:48px;padding:28px}
        .modal-card h3{font-size:1.6rem;font-weight:600;margin-bottom:16px}
        .modal-params{background:var(--gray-2);border-radius:28px;padding:18px;margin:20px 0;line-height:1.6}
        .button-group{display:flex;gap:12px;justify-content:flex-end}
        .btn-confirm{background:var(--success-light);border:none;padding:8px 24px;border-radius:40px;font-weight:600;cursor:pointer}
        .btn-cancel{background:var(--border);border:none;padding:8px 24px;border-radius:40px;font-weight:600;cursor:pointer}

        /* 历史记录全屏页面 */
        .history-page{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:var(--bg);z-index:5000;flex-direction:column;padding:20px;overflow-y:auto}
        .history-page.active{display:flex}
        .history-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-shrink:0}
        .history-header h2{font-size:1.6rem;font-weight:700;color:var(--text-deep)}
        .history-header-left{display:flex;align-items:center;gap:12px}
        .btn-back{background:var(--gray-2);border:none;padding:10px 20px;border-radius:60px;font-size:.9rem;font-weight:600;color:var(--text-gray);cursor:pointer;transition:var(--transition)}
        .btn-back:hover{background:var(--border)}
        .history-actions{display:flex;gap:8px;align-items:center}
        .btn-delete-mode{background:var(--red-light);color:var(--red);border:none;padding:8px 16px;border-radius:60px;font-size:.85rem;font-weight:600;cursor:pointer;transition:var(--transition)}
        .btn-delete-mode:hover{background:var(--red);color:#fff}
        .btn-delete-mode.active{background:var(--red);color:#fff}
        .btn-select-all{background:var(--gray-2);border:none;padding:8px 16px;border-radius:60px;font-size:.85rem;font-weight:600;color:var(--text-gray);cursor:pointer;display:none}
        .btn-select-all.visible{display:inline-block}
        .btn-batch-delete{background:var(--red);color:#fff;border:none;padding:8px 16px;border-radius:60px;font-size:.85rem;font-weight:600;cursor:pointer;display:none}
        .btn-batch-delete.visible{display:inline-block}
        .btn-batch-delete:disabled{background:#ccc;cursor:not-allowed}
        .btn-cancel-delete{background:var(--gray-2);border:none;padding:8px 16px;border-radius:60px;font-size:.85rem;font-weight:600;color:var(--text-gray);cursor:pointer;display:none}
        .btn-cancel-delete.visible{display:inline-block}
        .delete-count{font-size:.85rem;color:var(--red);font-weight:600;display:none}
        .delete-count.visible{display:inline}
        .history-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;flex:1}
        .history-item{display:flex;flex-direction:column;align-items:center;gap:8px;position:relative}
        .history-item-img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:16px;border:2px solid var(--border);cursor:pointer;transition:transform .15s,border-color .15s}
        .history-item-img:hover{transform:scale(1.03)}
        .history-item-prompt{font-size:.7rem;color:var(--text-gray);width:100%;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .history-item-meta{font-size:.6rem;color:var(--text-minor)}
        .history-checkbox{position:absolute;top:8px;left:8px;width:24px;height:24px;border-radius:50%;border:2px solid var(--border);background:rgba(255,255,255,.9);cursor:pointer;display:none;align-items:center;justify-content:center;transition:var(--transition);z-index:10;font-size:14px}
        .history-checkbox.visible{display:flex}
        .history-checkbox.checked{background:var(--primary);border-color:var(--primary);color:#fff}
        .history-item.selected .history-item-img{border-color:var(--primary);box-shadow:0 0 0 3px rgba(59,130,246,.3)}
        @media(max-width:700px){.history-grid{grid-template-columns:repeat(2,1fr);gap:12px}}
        @media(max-width:600px){.card{padding:20px;border-radius:30px}h2{font-size:1.5rem}.result-img{width:150px;height:150px}.mode-buttons{gap:12px}}
    </style>
</head>
<body>
<div class="card">
    <div class="content-wrapper">
        <div class="top-bar">
            <h2>🎨 AI画图工坊</h2>
            <button class="btn-history" onclick="openHistoryPage()">📚 历史记录</button>
        </div>
        <div class="sub">自然语言绘图 · 智能增强</div>

        <div class="ai-placeholder">
            <div id="aiNote" class="ai-note hidden-vis">✨ 已启用 DeepSeek-V4 智能优化：您的描述会被自动转换为高质量绘画参数。</div>
        </div>

        <div class="toggle-row">
            <span class="toggle-label">✨ 启用 DeepSeek-V4 优化</span>
            <label class="toggle-switch"><input type="checkbox" id="aiOptimizeToggle"><span class="slider"></span></label>
        </div>

        <div class="mode-buttons">
            <label><input type="radio" name="mode" value="text2image" checked> 文生图</label>
            <label><input type="radio" name="mode" value="image2image"> 图生图</label>
        </div>

        <div id="paramsPanel" class="params-panel">
            <div class="param-row">
                <div class="param-group"><label>📐 宽高比</label><select id="aspectRatioSelect"><option value="1:1" selected>1:1 正方形 (1024×1024)</option><option value="16:9">16:9 横屏宽幅 (1792×1024)</option><option value="9:16">9:16 竖屏长图 (1024×1792)</option><option value="4:3">4:3 横屏标准 (1365×1024)</option><option value="3:4">3:4 竖屏标准 (1024×1365)</option><option value="3:2">3:2 横屏风景 (1536×1024)</option><option value="2:3">2:3 竖屏海报 (1024×1536)</option></select></div>
                <div class="param-group"><label>🎨 风格</label><select id="styleSelect"><option value="realistic">写实</option><option value="anime">二次元</option><option value="digital-painting">数字绘画</option><option value="oil-painting">油画</option><option value="pixel-art">像素风</option></select></div>
            </div>
            <div class="param-row">
                <div class="param-group"><label>🔢 数量</label><select id="numSelect"><option value="1">1张</option><option value="2">2张</option><option value="3">3张</option></select></div>
                <div class="param-group"><label>⚙️ 细节步数</label><select id="stepsSelect"><option value="30">30 - 快速</option><option value="50" selected>50 - 标准</option><option value="100">100 - 高细节</option></select></div>
            </div>
        </div>

        <div id="uploadArea" class="upload-section">
            <div>📷 上传参考图片（可多张）</div>
            <input type="file" id="imageInput" accept="image/*" multiple>
            <div id="previewContainer" class="preview-container"></div>
        </div>

        <textarea id="promptInput" rows="4" placeholder="描述你想画的内容，例如：一只穿着宇航服的柴犬，在火星上，赛博朋克风格"></textarea>
        <div id="resultsContainer"></div>
    </div>
    <button id="generateBtn" class="btn-generate">✨ 生成图片</button>
    <div class="footnote">* 开启AI优化后，点击生成会展示优化后的参数确认框</div>
</div>

<!-- 历史记录全屏页面 -->
<div id="historyPage" class="history-page">
    <div class="history-header">
        <div class="history-header-left">
            <button class="btn-back" onclick="closeHistoryPage()">← 返回</button>
            <h2>📚 历史记录</h2>
        </div>
        <div class="history-actions">
            <span id="deleteCount" class="delete-count">已选 0 项</span>
            <button id="btnSelectAll" class="btn-select-all" onclick="selectAll()">全选</button>
            <button id="btnBatchDelete" class="btn-batch-delete" onclick="batchDelete()" disabled>删除选中</button>
            <button id="btnDeleteMode" class="btn-delete-mode" onclick="toggleDeleteMode()">🗑️ 删除</button>
            <button id="btnCancelDelete" class="btn-cancel-delete" onclick="cancelDeleteMode()">取消</button>
        </div>
    </div>
    <div id="historyGrid" class="history-grid"></div>
</div>

<div id="imageModal" class="image-modal" onclick="closeImageModal()">
    <img id="imageModalImg" src="" alt="放大图片">
</div>

<div id="confirmModal" class="modal-overlay">
    <div class="modal-card">
        <h3>📝 是否生成以下内容？</h3>
        <div class="modal-params">
            <p><strong>✨ 优化后提示词：</strong><br><span id="optPromptText">—</span></p>
            <p><strong>📐 宽高比：</strong> <span id="optRatio">1:1</span> &nbsp;|&nbsp;
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
    // ===== 图片放大 =====
    function openImageModal(src){document.getElementById('imageModalImg').src=src;document.getElementById('imageModal').classList.add('active')}
    function closeImageModal(){document.getElementById('imageModal').classList.remove('active')}

    // ===== 历史记录页面 =====
    let deleteMode=false;
    let selectedItems=new Set();
    let historyData=[];

    function openHistoryPage(){
        document.getElementById('historyPage').classList.add('active');
        cancelDeleteMode();
        loadHistory();
    }
    function closeHistoryPage(){document.getElementById('historyPage').classList.remove('active')}

    function toggleDeleteMode(){
        deleteMode=true;
        selectedItems.clear();
        document.getElementById('btnDeleteMode').style.display='none';
        document.getElementById('btnSelectAll').classList.add('visible');
        document.getElementById('btnBatchDelete').classList.add('visible');
        document.getElementById('btnCancelDelete').classList.add('visible');
        document.getElementById('deleteCount').classList.add('visible');
        updateDeleteUI();
        renderHistoryGrid(historyData);
    }

    function cancelDeleteMode(){
        deleteMode=false;
        selectedItems.clear();
        document.getElementById('btnDeleteMode').style.display='';
        document.getElementById('btnSelectAll').classList.remove('visible');
        document.getElementById('btnBatchDelete').classList.remove('visible');
        document.getElementById('btnCancelDelete').classList.remove('visible');
        document.getElementById('deleteCount').classList.remove('visible');
        renderHistoryGrid(historyData);
    }

    function updateDeleteUI(){
        const count=selectedItems.size;
        document.getElementById('deleteCount').textContent='已选 '+count+' 项';
        document.getElementById('btnBatchDelete').disabled=count===0;
        const btnAll=document.getElementById('btnSelectAll');
        btnAll.textContent=count===historyData.length?'取消全选':'全选';
    }

    function toggleSelectItem(idx){
        if(selectedItems.has(idx)){selectedItems.delete(idx)}else{selectedItems.add(idx)}
        const item=document.querySelector('.history-item[data-idx="'+idx+'"]');
        if(item){
            item.classList.toggle('selected',selectedItems.has(idx));
            const cb=item.querySelector('.history-checkbox');
            if(cb){cb.classList.toggle('checked',selectedItems.has(idx));cb.innerHTML=selectedItems.has(idx)?'✓':''}
        }
        updateDeleteUI();
    }

    function selectAll(){
        if(selectedItems.size===historyData.length){
            selectedItems.clear();
        }else{
            historyData.forEach((_,i)=>selectedItems.add(i));
        }
        renderHistoryGrid(historyData);
        updateDeleteUI();
    }

    async function batchDelete(){
        if(selectedItems.size===0)return;
        if(!confirm('确定删除选中的 '+selectedItems.size+' 条记录？'))return;
        const indices=Array.from(selectedItems);
        try{
            const resp=await fetch('/api/history/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({indices})});
            const data=await resp.json();
            if(data.success){
                cancelDeleteMode();
                await loadHistory();
            }else{alert('删除失败：'+data.error)}
        }catch(e){alert('删除失败：'+e.message)}
    }

    async function loadHistory(){
        try{
            const resp=await fetch('/api/history');
            historyData=await resp.json();
            renderHistoryGrid(historyData);
        }catch(e){console.error('加载历史失败',e)}
    }

    function renderHistoryGrid(items){
        const grid=document.getElementById('historyGrid');
        if(!items||items.length===0){
            grid.innerHTML='<p style="color:var(--text-minor);font-size:.95rem;margin-top:80px;text-align:center">暂无历史记录</p>';
            return;
        }
        let html='';
        items.forEach((item,i)=>{
            const ratio=item.aspect_ratio||item.size||'';
            const isSel=selectedItems.has(i);
            html+='<div class="history-item'+(isSel?' selected':'')+'" data-idx="'+i+'">';
            if(deleteMode){
                html+='<div class="history-checkbox'+(isSel?' checked':'')+'" onclick="event.stopPropagation();toggleSelectItem('+i+')">'+(isSel?'✓':'')+'</div>';
            }
            html+='<img class="history-item-img" src="'+item.catbox_url+'" onclick="'+(deleteMode?'toggleSelectItem('+i+')':'openImageModal(this.src)')+'" alt="'+item.prompt+'">';
            html+='<div class="history-item-prompt" title="'+item.prompt+'">'+item.prompt+'</div>';
            html+='<div class="history-item-meta">'+ratio+' | '+(item.style||'')+'</div>';
            html+='</div>';
        });
        grid.innerHTML=html;
        updateDeleteUI();
    }

    // ===== 主页面逻辑 =====
    const aiToggle=document.getElementById('aiOptimizeToggle');
    const aiNoteDiv=document.getElementById('aiNote');
    const paramsPanel=document.getElementById('paramsPanel');
    const modeRadios=document.querySelectorAll('input[name="mode"]');
    const uploadArea=document.getElementById('uploadArea');
    const imageInput=document.getElementById('imageInput');
    const previewContainer=document.getElementById('previewContainer');
    const generateBtn=document.getElementById('generateBtn');
    const modal=document.getElementById('confirmModal');
    const promptInput=document.getElementById('promptInput');
    const aspectRatioSelect=document.getElementById('aspectRatioSelect');
    const styleSelect=document.getElementById('styleSelect');
    const numSelect=document.getElementById('numSelect');
    const stepsSelect=document.getElementById('stepsSelect');

    let selectedFiles=[];
    function updatePreview(){previewContainer.innerHTML='';selectedFiles.forEach((f,i)=>{const r=new FileReader();r.onload=e=>{const img=document.createElement('img');img.src=e.target.result;img.className='preview-img';const d=document.createElement('button');d.innerText='✕';d.className='preview-del-btn';d.onclick=()=>{selectedFiles.splice(i,1);updatePreview();syncFileInput()};const w=document.createElement('div');w.className='preview-wrapper';w.appendChild(img);w.appendChild(d);previewContainer.appendChild(w)};r.readAsDataURL(f)})}
    function syncFileInput(){const dt=new DataTransfer();selectedFiles.forEach(f=>dt.items.add(f));imageInput.files=dt.files}
    imageInput.addEventListener('change',e=>{Array.from(e.target.files).forEach(f=>{if(!selectedFiles.some(s=>s.name===f.name&&s.size===f.size))selectedFiles.push(f)});updatePreview();syncFileInput()});
    function toggleUploadArea(){uploadArea.classList.toggle('active',document.querySelector('input[name="mode"]:checked').value==='image2image')}
    modeRadios.forEach(r=>r.addEventListener('change',toggleUploadArea));
    function updateAIUI(){aiNoteDiv.classList.toggle('hidden-vis',!aiToggle.checked);paramsPanel.classList.toggle('param-hidden',aiToggle.checked)}
    aiToggle.addEventListener('change',updateAIUI);

    function getFormData(){const p=promptInput.value.trim();if(!p)return null;const fd=new FormData();fd.append('mode',document.querySelector('input[name="mode"]:checked').value);fd.append('prompt',p);fd.append('aspect_ratio',aspectRatioSelect.value);fd.append('style',styleSelect.value);fd.append('num',numSelect.value);fd.append('steps',stepsSelect.value);selectedFiles.forEach(f=>fd.append('image_files',f));return fd}

    async function callOptimize(prompt,mode){const r=await fetch('/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,mode})});const d=await r.json();if(!d.success)throw new Error(d.error);return d}

    function renderResults(results){const c=document.getElementById('resultsContainer');let h='';if(results&&results.length>0){h+='<div class="results-section"><div class="results-title">🖼️ 生成结果</div><div class="results-grid">';results.forEach(item=>{h+='<div class="result-card"><img class="result-img" src="'+item.display_url+'" onclick="openImageModal(this.src)" alt="生成图片">';if(item.catbox_url)h+='<a class="catbox-link" href="'+item.catbox_url+'" target="_blank">🔗 永久链接</a>';h+='</div>'});h+='</div></div>'}c.innerHTML=h}

    async function submitGenerate(fd){generateBtn.disabled=true;generateBtn.textContent='⏳ 生成中…';try{const r=await fetch('/generate',{method:'POST',body:fd});const d=await r.json();if(!d.success)throw new Error(d.error||'生成失败');renderResults(d.results)}catch(e){document.getElementById('resultsContainer').innerHTML='<div class="error-message">'+e.message+'</div>'}finally{generateBtn.disabled=false;generateBtn.textContent='✨ 生成图片'}}

    function showConfirmModal(opt){document.getElementById('optPromptText').innerText=opt.optimized_prompt;document.getElementById('optRatio').innerText=opt.aspect_ratio||'1:1';const sm={'realistic':'写实','anime':'二次元','digital-painting':'数字绘画','oil-painting':'油画','pixel-art':'像素风'};document.getElementById('optStyle').innerText=sm[opt.style]||opt.style;document.getElementById('optNum').innerText=opt.num;document.getElementById('optSteps').innerText=opt.steps;modal.classList.add('active')}

    generateBtn.addEventListener('click',async()=>{const fd=getFormData();if(!fd){alert("请输入提示词");return}if(!aiToggle.checked){await submitGenerate(fd)}else{try{const o=await callOptimize(fd.get('prompt'),fd.get('mode'));window.currentOptimized={mode:fd.get('mode'),...o,image_files:selectedFiles.slice()};showConfirmModal(window.currentOptimized)}catch(e){alert("优化失败："+e.message)}}});

    document.getElementById('modalConfirmBtn').addEventListener('click',async()=>{modal.classList.remove('active');if(!window.currentOptimized)return;const o=window.currentOptimized;const fd=new FormData();fd.append('mode',o.mode);fd.append('prompt',o.optimized_prompt);fd.append('aspect_ratio',o.aspect_ratio||'1:1');fd.append('style',o.style);fd.append('num',o.num);fd.append('steps',o.steps);(o.image_files||[]).forEach(f=>fd.append('image_files',f));await submitGenerate(fd);window.currentOptimized=null});
    document.getElementById('modalCancelBtn').addEventListener('click',()=>modal.classList.remove('active'));
    modal.addEventListener('click',e=>{if(e.target===modal)modal.classList.remove('active')});

    toggleUploadArea();updateAIUI();
</script>
</body>
</html>
"""
