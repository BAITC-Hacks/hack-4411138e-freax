(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const types={department_added:'Добавлено в перечень',department_removed:'Убрано из перечня',department_retained:'Сохранено в перечне',reorganization:'Реорганизация',function_loss:'Возможная потеря',function_transfer:'Передача функции',duplication:'Дублирование',conflict:'Конфликт интересов',contradiction:'Противоречие формулировок'};
  const statuses={unknown:'Недостаточно данных',risk:'Возможный риск',confirmed:'Подтверждено фрагментом',dismissed:'Отклонено аналитиком'};
  let files={before:null,after:null}, result=null, busy=false;
  let selectedId=null;
  const panes={left:'before',right:'after'};
  let config={base:'https://api.openai.com/v1',model:'gpt-4.1-mini',key:''};
  function setFiles(side,file){files[side]=file;$(side+'-name').textContent=file?.name||'Документ не выбран';$(side+'-size').textContent=file?`${(file.size/1024).toFixed(0)} КБ · DOCX`:'DOCX · до 10 МБ';result=null;selectedId=null;$('results').hidden=true;$('empty-state').hidden=false;document.body.classList.remove('has-results');}
  for(const side of ['before','after']) $(side+'-file').addEventListener('change',e=>setFiles(side,e.target.files[0]||null));
  function setBusy(value){busy=value;document.body.classList.toggle('is-busy',value);$('upload-form').setAttribute('aria-busy',String(value));for(const id of ['run','load-example','before-file','after-file','use-ai','settings-open']) $(id).disabled=value;$('run').textContent=value?'Идёт сравнение…':'Сравнить документы';}
  function openSettings(){$('api-base').value=config.base;$('api-model').value=config.model;$('api-key').value=config.key;$('settings').showModal();}
  $('settings-open').addEventListener('click',openSettings);
  $('settings-close').addEventListener('click',()=>$('settings').close());
  $('provider').addEventListener('change',()=>{const local=$('provider').value==='local';$('api-base').value=local?'http://127.0.0.1:11434/v1':'https://api.openai.com/v1';$('api-key').value='';});
  $('settings-form').addEventListener('submit',e=>{e.preventDefault();config={base:$('api-base').value.trim(),model:$('api-model').value.trim(),key:$('api-key').value.trim()};$('use-ai').checked=true;$('settings').close();updateMode();});
  function updateMode(){$('connection-note').textContent=$('use-ai').checked?`AI: ${config.model||'модель не выбрана'} · текст будет отправлен в ${config.base}`:'Без модели: поиск кандидатов по текстовым правилам.';}
  $('use-ai').addEventListener('change',()=>{updateMode();if($('use-ai').checked&&!config.model)openSettings();});
  fetch('/api/config').then(r=>r.json()).then(data=>{config.base=data.base;config.model=data.model; if(data.hasKey)$('key-note').textContent='На сервере настроен ключ. Пустое поле использует его. Текст документов отправляется выбранному провайдеру.';updateMode();}).catch(()=>{$('run-status').textContent='Откройте приложение через локальный сервер, указанный в README.';});
  $('load-example').addEventListener('click',async()=>{if(busy)return;setBusy(true);try{const loaded=[];for(const s of window.DOCUMENT_SOURCES){const response=await fetch(s.file);if(!response.ok)throw Error('Исходные документы недоступны.');loaded.push(new File([await response.blob()],s.name,{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}));}for(const [i,side] of ['before','after'].entries()){const transfer=new DataTransfer();transfer.items.add(loaded[i]);$(side+'-file').files=transfer.files;setFiles(side,loaded[i]);}$('run-status').textContent='Загружены реальные редакции 8 и 9. Анализ ещё не выполнялся.';}catch(e){$('run-status').textContent=e.message;}finally{setBusy(false);}});
  const encode=file=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve({name:file.name,data:String(reader.result).split(',')[1]});reader.onerror=()=>reject(Error('Не удалось прочитать файл.'));reader.readAsDataURL(file);});
  $('upload-form').addEventListener('submit',async e=>{e.preventDefault();if(busy)return;if(!files.before||!files.after)return;for(const file of Object.values(files)){if(!file.name.toLowerCase().endsWith('.docx')||file.size>10000000){$('run-status').textContent='Нужны DOCX размером до 10 МБ.';return;}}setBusy(true);result=null;$('results').hidden=true;$('empty-state').hidden=true;$('run-status').textContent=$('use-ai').checked?'Извлечение пунктов и запрос к модели. Ожидание может занять до двух минут.':'Извлечение пунктов и сравнение текстов…';const started=performance.now();try{const before=await encode(files.before),after=await encode(files.after);const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({before,after,useAI:$('use-ai').checked,config}),signal:AbortSignal.timeout(150000)});const data=await response.json();if(!response.ok)throw Error(data.error||'Ошибка анализа');result=data;result.timestamp=new Date().toISOString();$('run-status').textContent=`Обработка завершена за ${((performance.now()-started)/1000).toFixed(1)} с.`;$('type-filter').value='all';$('finding-search').value='';$('unreviewed-only').checked=false;$('related-only').checked=false;selectedId=result.findings[0]?.id||null;panes.left='before';panes.right='after';render();}catch(err){$('run-status').textContent=err.name==='TimeoutError'?'Время ожидания истекло. Повторите без AI или проверьте модель.':err.message;$('empty-state').hidden=false;}finally{setBusy(false);}});

  const currentFinding=()=>result?.findings.find(f=>f.id===selectedId);
  const versionName=side=>side==='before'?'До изменений':'После изменений';
  function tone(f){
    if(!f)return 'neutral';
    if(['function_loss','department_removed'].includes(f.type))return 'loss';
    if(['function_transfer','reorganization'].includes(f.type))return 'transfer';
    if(['duplication','conflict','contradiction'].includes(f.type))return 'risk';
    return f.type==='department_added'?'added':'neutral';
  }
  function evidenceButton(side,id){
    const p=result[side].paragraphs.find(p=>p.id===id);
    if(!p)return '';
    return `<button class="excerpt-button" data-side="${side}" data-id="${esc(id)}" title="Открыть источник с соседними абзацами">${versionName(side)} · п. ${esc(p.section||'без номера')}<span>${esc(id)} ↗</span></button>`;
  }
  function filteredFindings(){
    const filter=$('type-filter').value,query=$('finding-search').value.trim().toLocaleLowerCase('ru');
    return result.findings.filter(f=>
      (filter==='all'||(filter==='departments'?(f.type.startsWith('department_')||f.type==='reorganization'):f.type===filter))&&
      (!$('unreviewed-only').checked||!f.reviewed)&&
      (!query||`${f.title} ${f.explanation} ${types[f.type]||f.type}`.toLocaleLowerCase('ru').includes(query)));
  }
  function render(){
    if(!result)return;
    $('results').hidden=false;$('empty-state').hidden=true;$('upload-details').open=false;
    document.body.classList.add('has-results');
    $('run-method').textContent={rules:'ТЕКСТОВЫЕ ПРАВИЛА · БЕЗ LLM',ai:'AI + ПРАВИЛА · ТРЕБУЕТСЯ ПРОВЕРКА',fallback:'AI НЕ ЗАВЕРШЁН · КАНДИДАТЫ ПО ПРАВИЛАМ'}[result.mode]||result.mode;
    $('warnings').innerHTML=result.warnings.map(w=>`<p class="notice">${esc(w)}</p>`).join('');
    $('coverage').textContent=`Извлечено: ${result.before.paragraphs.length} абзацев до / ${result.after.paragraphs.length} после. ${result.mode==='ai'?'В модель передан весь извлечённый текст.':'Семантическая полнота не проверена.'}`;
    for(const panel of ['left','right']){
      $(panel+'-document').innerHTML=['before','after'].map(side=>`<option value="${side}">${versionName(side)} · ${esc(result[side].name)}</option>`).join('');
      $(panel+'-document').value=panes[panel];
    }
    renderFindings();renderInspector();renderPanes(true);renderConclusion();
  }
  function renderFindings(){
    const findings=filteredFindings();
    if(!findings.some(f=>f.id===selectedId))selectedId=findings[0]?.id||null;
    $('finding-count').textContent=`${findings.length} / ${result.findings.length}`;
    $('findings').innerHTML=findings.length?findings.map(f=>`<button class="finding-card ${f.id===selectedId?'active':''}" data-finding="${esc(f.id)}" aria-pressed="${f.id===selectedId}">
      <span class="finding-tag">${esc(types[f.type]||f.type)}</span>${f.reviewed?'<span class="reviewed-mark">✓ Проверено</span>':''}
      <strong>${esc(f.title)}</strong><span class="finding-sub">${f.method==='llm'?'Предложение модели':'Текстовое правило'} · ${esc(f.id)}</span></button>`).join(''):
      '<p class="empty-findings">Кандидатов по этим условиям нет. Это не подтверждает отсутствие риска.</p>';
    const checked=result.findings.filter(f=>f.reviewed).length;
    $('review-count').textContent=`${checked} / ${result.findings.length}`;
    $('review-progress').max=Math.max(1,result.findings.length);$('review-progress').value=checked;
  }
  function renderInspector(){
    const f=currentFinding();
    if(!f){$('review-inspector').innerHTML='<p class="empty-findings">Выберите замечание из списка. Документы доступны для самостоятельной проверки.</p>';return;}
    const visible=filteredFindings(),index=visible.findIndex(item=>item.id===f.id);
    $('review-inspector').innerHTML=`<div class="inspector-top"><span class="inspector-meta">ПРОВЕРКА ОСНОВАНИЯ · ${esc(f.id)}</span><div class="finding-navigation"><span>${index+1} из ${visible.length}</span><button class="icon-button" data-step="-1" aria-label="Предыдущее замечание" ${index===0?'disabled':''}>↑</button><button class="icon-button" data-step="1" aria-label="Следующее замечание" ${index===visible.length-1?'disabled':''}>↓</button></div></div>
      <div class="inspector-content"><div><h2>${esc(f.title)}</h2><p class="explanation">${esc(f.explanation)}</p><div class="source-links">${['before','after'].map(side=>f[side+'_ids'].length?f[side+'_ids'].map(id=>evidenceButton(side,id)).join(''):`<span class="source-missing">${versionName(side)}: ссылка не указана.</span>`).join('')}</div><p class="micro">${esc(types[f.type]||f.type)} · ${f.method==='llm'?'Предложение модели':'Текстовое правило'}. Наличие ссылки не доказывает вывод.</p><button class="quiet" id="locate-sources">Показать источники рядом ↗</button></div>
      <div class="analyst-controls"><label>Решение аналитика<select data-review="${esc(f.id)}" aria-label="Статус ${esc(f.title)}">${!f.reviewed?'<option value="" selected disabled>Дать оценку</option>':''}${Object.entries(statuses).map(([k,v])=>`<option value="${k}" ${f.reviewed&&f.status===k?'selected':''}>${v}</option>`).join('')}</select></label><label>Комментарий к решению<textarea id="analyst-note" data-note="${esc(f.id)}" placeholder="Что проверено и что нужно уточнить…" maxlength="4000">${esc(f.note||'')}</textarea></label><p class="review-state ${f.reviewed?'checked':''}">${f.reviewed?'✓ Решение включено в заключение':'Ожидает проверки человеком'}</p></div></div>`;
  }
  function renderPanes(focus=false){for(const panel of ['left','right'])renderPane(panel,focus);}
  function renderPane(panel,focus=false){
    const side=panes[panel],doc=result[side],f=currentFinding();
    const ids=new Set(f?.[side+'_ids']||[]),linked=doc.paragraphs.filter(p=>ids.has(p.id));
    const otherSide=side==='before'?'after':'before';
    const otherSource=result[otherSide].paragraphs.find(p=>f?.[otherSide+'_ids'].includes(p.id));
    const contextAnchor=!linked.length&&otherSource?.section?doc.paragraphs.find(p=>p.section===otherSource.section):null;
    $(panel+'-document').value=side;$(panel+'-document').title=doc.name;
    $(panel+'-version').textContent=side==='before'?'ДО':'ПОСЛЕ';
    $(panel+'-meta').textContent=`${doc.paragraphs.length} абзацев · SHA-256 ${doc.sha256.slice(0,12)}…`;
    $(panel+'-meta').title=`SHA-256 ${doc.sha256}`;
    const notice=$(panel+'-notice');
    notice.textContent=!f?'Полный текст документа':linked.length?`${types[f.type]||f.type} · связанных абзацев: ${linked.length}`:'Ссылка не указана. Отсутствие функции не доказано.';
    if(contextAnchor&&!$('related-only').checked)notice.textContent+=` Открыт п. ${contextAnchor.section} для ручного сопоставления.`;
    notice.classList.toggle('no-source',!!f&&!linked.length);
    const text=$(panel+'-text'),scroll=text.scrollTop,related=$('related-only').checked&&!!f;
    const keep=new Set();
    doc.paragraphs.forEach((p,i)=>{if(ids.has(p.id))for(let j=Math.max(0,i-1);j<=Math.min(doc.paragraphs.length-1,i+1);j++)keep.add(j);});
    let hidden=0,html='';
    const gap=()=>{if(hidden){html+=`<button class="context-gap" data-show-context>Показать скрытые абзацы: ${hidden}</button>`;hidden=0;}};
    doc.paragraphs.forEach((p,i)=>{
      if(related&&!keep.has(i)){hidden++;return;}
      gap();html+=`<div class="doc-paragraph ${ids.has(p.id)?'linked tone-'+tone(f):''}" data-paragraph="${esc(p.id)}"><span class="paragraph-id">${esc(p.id)}</span><p class="paragraph-copy">${esc(p.text)}</p></div>`;
    });gap();
    if(related&&!linked.length)html='<p class="empty-findings">Для этого документа у замечания нет ссылки. Откройте полный текст для проверки.</p><button class="context-gap" data-show-context>Показать весь документ</button>';
    text.innerHTML=html;text.scrollTop=scroll;
    if(focus){const target=text.querySelector('.linked')||(contextAnchor?Array.from(text.querySelectorAll('[data-paragraph]')).find(p=>p.dataset.paragraph===contextAnchor.id):null);if(target){text.scrollTop=Math.max(0,target.offsetTop-text.offsetTop-40);target.classList.add('flash');}else text.scrollTop=0;}
  }
  function selectFinding(id){selectedId=id;renderFindings();renderInspector();renderPanes(true);}
  for(const panel of ['left','right'])$(panel+'-document').addEventListener('change',e=>{panes[panel]=e.target.value;if(result)renderPane(panel,true);});
  $('related-only').addEventListener('change',()=>{if(result)renderPanes(true);});
  $('swap-panes').addEventListener('click',()=>{[panes.left,panes.right]=[panes.right,panes.left];if(result)renderPanes(true);});
  for(const id of ['type-filter','unreviewed-only','finding-search'])$(id).addEventListener(id==='finding-search'?'input':'change',()=>{if(result){renderFindings();renderInspector();renderPanes(true);}});
  document.addEventListener('input',e=>{if(!result||!e.target.dataset.note)return;const f=result.findings.find(f=>f.id===e.target.dataset.note);if(f)f.note=e.target.value;});
  document.addEventListener('click',e=>{
    if(!result)return;
    const card=e.target.closest('[data-finding]');if(card){selectFinding(card.dataset.finding);return;}
    const step=e.target.closest('[data-step]');if(step){const visible=filteredFindings(),index=visible.findIndex(f=>f.id===selectedId);if(visible[index+Number(step.dataset.step)])selectFinding(visible[index+Number(step.dataset.step)].id);return;}
    if(e.target.closest('[data-show-context]')){$('related-only').checked=false;renderPanes(true);return;}
    if(e.target.closest('#locate-sources')){panes.left='before';panes.right='after';renderPanes(true);$('left-text').focus({preventScroll:true});}
  });
  const resizer=$('pane-resizer');
  let split=50;
  function setSplit(value){split=Math.max(30,Math.min(70,value));$('document-panes').style.setProperty('--left-width',`calc(${split}% - 3px)`);resizer.setAttribute('aria-valuenow',String(Math.round(split)));}
  resizer.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home'].includes(e.key)){e.preventDefault();setSplit(e.key==='Home'?50:split+(e.key==='ArrowLeft'?-5:5));}});
  resizer.addEventListener('dblclick',()=>setSplit(50));
  resizer.addEventListener('pointerdown',e=>{if(e.button!==0)return;resizer.setPointerCapture(e.pointerId);});
  resizer.addEventListener('pointermove',e=>{if(!resizer.hasPointerCapture(e.pointerId))return;const rect=$('document-panes').getBoundingClientRect();setSplit((e.clientX-rect.left)/rect.width*100);});
  resizer.addEventListener('pointerup',e=>{if(resizer.hasPointerCapture(e.pointerId))resizer.releasePointerCapture(e.pointerId);});
  function conclusionLines(){const reviewed=result.findings.filter(f=>f.reviewed),confirmed=reviewed.filter(f=>f.status==='confirmed'),risks=result.findings.filter(f=>f.status==='risk'&&!f.reviewed||f.reviewed&&f.status==='risk');return [`Проанализированы «${result.before.name}» и «${result.after.name}».`,`Найдено кандидатов: ${result.findings.length}. Проверено аналитиком: ${reviewed.length}. Подтверждено аналитиком: ${confirmed.length}. Возможных рисков: ${risks.length}.`,`Режим: ${result.mode==='ai'?'модель и текстовые правила':result.mode==='fallback'?'резервный поиск по правилам после ошибки AI':'текстовые правила без модели'}.`,`Результаты не гарантируют полного обнаружения потерь, дублирования и конфликтов интересов. Отсутствие находки не доказывает отсутствие риска.`];}
  function renderConclusion(){$('conclusion').innerHTML='<h3>Предварительное заключение</h3>'+conclusionLines().map(l=>`<p>${esc(l)}</p>`).join('')+'<ul>'+Object.entries(types).filter(([type])=>result.findings.some(f=>f.type===type)).map(([type,label])=>`<li>${label}: ${result.findings.filter(f=>f.type===type).length}</li>`).join('')+'</ul>';}
  document.addEventListener('change',e=>{const id=e.target.dataset.review;if(!id||!result)return;const item=result.findings.find(f=>f.id===id);if(!e.target.value)return;item.status=e.target.value;item.reviewed=true;renderFindings();renderInspector();renderPanes();renderConclusion();});
  document.addEventListener('click',e=>{const button=e.target.closest('[data-side]');if(!button||!result)return;const doc=result[button.dataset.side],index=doc.paragraphs.findIndex(p=>p.id===button.dataset.id);$('evidence-meta').textContent=button.dataset.side==='before'?'ИСХОДНАЯ РЕДАКЦИЯ':'НОВАЯ РЕДАКЦИЯ';$('evidence-title').textContent='Пункт '+(doc.paragraphs[index].section||'не указан');$('evidence-file').textContent=doc.name+' · SHA-256 '+doc.sha256;$('evidence-body').innerHTML=doc.paragraphs.slice(Math.max(0,index-1),index+2).map(p=>`<p class="${p.id===button.dataset.id?'target':''}">${esc(p.text)}<small>${esc(p.id)} · пункт ${esc(p.section||'не указан')}</small></p>`).join('');$('evidence').showModal();});
  $('evidence-close').addEventListener('click',()=>$('evidence').close());
  $('download').addEventListener('click',()=>{if(!result)return;const lines=['# Предварительное заключение',result.timestamp,'',...conclusionLines(),...result.warnings.map(w=>'Ограничение: '+w),'',`SHA-256 до: ${result.before.sha256}`,`SHA-256 после: ${result.after.sha256}`];for(const f of result.findings){lines.push('',`## ${f.title}`,`Тип: ${types[f.type]}; статус: ${statuses[f.status]}; ${f.reviewed?'оценка аналитика':'не проверено человеком'}; метод: ${f.method}`,f.explanation);if(f.note)lines.push('Комментарий аналитика: '+f.note);for(const side of ['before','after']){const doc=result[side];for(const id of f[side+'_ids']){const p=doc.paragraphs.find(p=>p.id===id);lines.push(`Источник: ${doc.name}, п. ${p.section||'не указан'}, ${id}`,`> ${p.text}`);}}}const url=URL.createObjectURL(new Blob([lines.join('\n\n')],{type:'text/markdown;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='zaklyuchenie.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
})();
