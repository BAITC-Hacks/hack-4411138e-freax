import {t,number,date,language,setLanguage,translate} from './i18n.js';
import {icon,hydrateIcons} from './icons.js';
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const kinds=['department_added','department_retained','department_removed','reorganization','function_loss','function_transfer','duplication','conflict','contradiction'];
const reviewStatuses=['unknown','risk','confirmed','dismissed'];
const groupTypes={departments:kinds.slice(0,4),functions:kinds.slice(4),risks:['function_loss','duplication','conflict','contradiction']};
let files={before:null,after:null},fileErrors={before:null,after:null},result=null,busy=false,view='new',activeTab='departments',selectedId=null;
let config={base:'https://api.openai.com/v1',model:'gpt-4.1-mini',key:''},serverHasKey=false,noticeKey='',errorKey='',errorRaw='',processingKey='reading';
let evidenceOpener=null,settingsOpener=null,split=50;
const panes={left:'before',right:'after'};
const selectedFinding=()=>result?.findings.find(f=>f.id===selectedId);
const modeKey=()=>result?.mode==='ai'?'aiMode':result?.mode==='fallback'?'fallbackMode':'rulesMode';
const tone=type=>['department_removed','function_loss'].includes(type)?'loss':['duplication','conflict','contradiction'].includes(type)?'risk':type==='department_added'?'added':type==='department_retained'?'neutral':'transfer';
const typeIcon=type=>tone(type)==='loss'||tone(type)==='risk'?'triangle-alert':tone(type)==='added'?'plus':tone(type)==='neutral'?'check':'git-compare-arrows';
const typeBadge=f=>`<span class="status-badge tone-${tone(f.type)}">${icon(typeIcon(f.type))}${esc(t(f.type))}</span>`;
const method=f=>t(f.method==='llm'?'modelMethod':'ruleMethod');
const sourceText=(f,side)=>f[side+'_ids'].map(id=>result[side].paragraphs.find(p=>p.id===id)?.text||'').join(' ');
// Department filtering uses explicit names from the rule contract, never infers ownership.
function departmentNames(){
 if(!result)return [];
 return [...new Set(result.findings.filter(f=>f.method==='rules'&&f.type.startsWith('department_')&&f.title.includes(': ')).map(f=>f.title.slice(f.title.indexOf(': ')+2)))];
}
function matchesDepartment(f,name){return `${f.title} ${sourceText(f,'before')} ${sourceText(f,'after')}`.toLocaleLowerCase().includes(name.toLocaleLowerCase());}
function visibleFindings(){
 if(!result)return [];
 const search=$('finding-search').value.trim().toLocaleLowerCase(),type=$('type-filter').value,department=$('department-filter').value;
 return result.findings.filter(f=>(activeTab==='report'||groupTypes[activeTab].includes(f.type))&&
  (type==='all'||f.type===type)&&(!$('unreviewed-only').checked||!f.reviewed)&&
  (department==='all'||(department==='unassigned'?!departmentNames().some(name=>matchesDepartment(f,name)):matchesDepartment(f,department)))&&
  (!search||`${f.title} ${f.explanation} ${t(f.type)} ${sourceText(f,'before')} ${sourceText(f,'after')}`.toLocaleLowerCase().includes(search)));
}
function updateTheme(preference){
 document.documentElement.dataset.themePreference=preference;
 document.documentElement.dataset.theme=preference==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):preference;
 $('theme-select').value=preference;
 $('theme-icon').innerHTML=icon(preference==='system'?'monitor':preference==='dark'?'moon':'sun');
 try{localStorage.setItem('osnovanie.theme',preference);}catch{}
}
$('theme-select').addEventListener('change',e=>updateTheme(e.target.value));
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(document.documentElement.dataset.themePreference==='system')updateTheme('system');});
function renderLocale(){
 translate();document.querySelectorAll('[data-lang]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.lang===language)));
 $('page-title').textContent=t(view==='new'?'newAnalysis':view==='report'?'report':'results');
 $('processing-status').textContent=t(processingKey);$('key-note').hidden=!serverHasKey;
 $('run-status').textContent=noticeKey?t(noticeKey):'';
 $('error-message').textContent=errorKey?t(errorKey):'';
 updateTheme(document.documentElement.dataset.themePreference||'system');
 renderFiles();updateControls();if(result){renderFilterOptions();renderResults();if($('evidence').open)renderEvidence(false);}
 $('previous-finding').setAttribute('aria-label',t('previous'));$('next-finding').setAttribute('aria-label',t('next'));
}
document.querySelectorAll('[data-lang]').forEach(button=>button.addEventListener('click',()=>{setLanguage(button.dataset.lang);renderLocale();}));
function setNav(open){$('sidebar').inert=matchMedia('(max-width: 700px)').matches&&!open;$('sidebar').classList.toggle('open',open);$('nav-backdrop').hidden=!open;$('open-nav').setAttribute('aria-expanded',String(open));if(open)$('close-nav').focus();}
matchMedia('(max-width: 700px)').addEventListener('change',()=>setNav(false));
setNav(false);
$('open-nav').addEventListener('click',()=>setNav(true));$('close-nav').addEventListener('click',()=>{setNav(false);$('open-nav').focus();});$('nav-backdrop').addEventListener('click',()=>setNav(false));
document.addEventListener('keydown',e=>{
 if(!$('sidebar').classList.contains('open'))return;
 if(e.key==='Escape'){setNav(false);$('open-nav').focus();}
 if(e.key==='Tab'){const items=[...$('sidebar').querySelectorAll('a,button:not(:disabled)')].filter(el=>el.getClientRects().length);const first=items[0],last=items.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
});
function showView(next){
 if(busy||(next!=='new'&&!result))return;
 const changedView=view!==next;view=next;if(changedView)window.scrollTo({top:0,behavior:'instant'});if(next==='report')activeTab='report';else if(next==='results'&&activeTab==='report')activeTab='departments';
 $('new-view').hidden=next!=='new';$('results').hidden=next==='new';$('processing').hidden=true;
 document.querySelectorAll('[data-view]').forEach(el=>{el.classList.toggle('active',el.dataset.view===next);if(el.dataset.view===next)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
 $('page-title').textContent=t(next==='new'?'newAnalysis':next==='report'?'report':'results');
 setNav(false);if(result){renderFilterOptions();renderResults();}
}
document.querySelectorAll('[data-view]').forEach(el=>el.addEventListener('click',()=>showView(el.dataset.view)));
document.querySelector('.brand').addEventListener('click',e=>{e.preventDefault();showView('new');});
function updateControls(){
 $('run').disabled=busy||!files.before||!files.after;
 $('run-reason').textContent=!files.before||!files.after?t('needFiles'):t('fileReadyNote');
 $('run-label').textContent=t(errorKey?'retry':'start');
 for(const id of ['load-example','before-file','after-file','use-ai','settings-open','settings-inline'])$(id).disabled=busy;
 document.querySelectorAll('[data-remove]').forEach(el=>el.disabled=busy);
 document.querySelectorAll('[data-view]').forEach(el=>{el.disabled=busy||(el.dataset.view!=='new'&&!result);el.title=el.disabled&&!busy?t('availableAfter'):'';});
 $('connection-note').textContent=$('use-ai').checked?t('aiHint',{model:config.model,base:config.base}):t('rulesHint');
 $('upload-form').setAttribute('aria-busy',String(busy));
}
function renderFiles(){
 for(const side of ['before','after']){
  const file=files[side],box=$(side+'-list');
  box.innerHTML=file?`<div class="file-row">${icon('file-text')}<div><div class="file-name">${esc(file.name)}</div><small>DOCX · ${new Intl.NumberFormat(language,{style:'unit',unit:'kilobyte',maximumFractionDigits:1}).format(file.size/1024)}</small><span class="file-state">${icon('circle-check')}${esc(t('ready'))}</span></div><button class="icon-button" type="button" data-remove="${side}" aria-label="${esc(t('removeFile',{name:file.name}))}">${icon('trash')}</button></div>`:'';
  $(side+'-error').hidden=!fileErrors[side];$(side+'-error').textContent=fileErrors[side]?t(fileErrors[side]):'';
  const zone=document.querySelector(`.dropzone[data-side="${side}"]`);zone.querySelector('strong').textContent=t(file?'replaceFile':'dropTitle');
 }
}
function invalidateResult(){result=null;selectedId=null;$('nav-count').hidden=true;$('error-state').hidden=true;errorKey='';noticeKey='';$('run-status').textContent='';if($('evidence').open)$('evidence').close();showView('new');}
function acceptFiles(side,selection){
 if(busy||!selection.length)return;
 const file=selection[0];
 fileErrors[side]=selection.length!==1?'fileCountError':!file.name.toLowerCase().endsWith('.docx')?'fileTypeError':file.size===0||file.size>10000000?'fileSizeError':null;
 if(!fileErrors[side]){files[side]=file;invalidateResult();}
 renderFiles();updateControls();
}
for(const side of ['before','after']){
 $(side+'-file').addEventListener('change',e=>acceptFiles(side,[...e.target.files]));
 const zone=document.querySelector(`.dropzone[data-side="${side}"]`);
 for(const event of ['dragenter','dragover'])zone.addEventListener(event,e=>{e.preventDefault();if(!busy)zone.classList.add('dragging');});
 for(const event of ['dragleave','drop'])zone.addEventListener(event,e=>{e.preventDefault();zone.classList.remove('dragging');if(event==='drop')acceptFiles(side,[...e.dataTransfer.files]);});
}
document.addEventListener('click',e=>{const button=e.target.closest('[data-remove]');if(!button||busy)return;const side=button.dataset.remove;files[side]=null;fileErrors[side]=null;$(side+'-file').value='';invalidateResult();renderFiles();updateControls();$(side+'-file').focus();});
function showError(key,raw=''){errorKey=key;errorRaw=raw;$('error-state').hidden=false;$('error-message').textContent=t(key);$('error-details').hidden=!raw;$('error-raw').textContent=raw;updateControls();}
$('load-example').addEventListener('click',async()=>{
 if(busy)return;busy=true;noticeKey='loadingExample';$('run-status').textContent=t(noticeKey);updateControls();
 try{
  const loaded=await Promise.all(window.DOCUMENT_SOURCES.map(async s=>{const response=await fetch(s.file);if(!response.ok)throw Error();return new File([await response.blob()],s.name,{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'});}));
  files={before:loaded[0],after:loaded[1]};fileErrors={before:null,after:null};busy=false;invalidateResult();noticeKey='exampleLoaded';$('run-status').textContent=t(noticeKey);renderFiles();
 }catch{showError('exampleError');}finally{busy=false;updateControls();}
});
const encode=file=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve({name:file.name,data:String(reader.result).split(',')[1]});reader.onerror=()=>reject(new Error('readError'));reader.readAsDataURL(file);});
$('upload-form').addEventListener('submit',async e=>{
 e.preventDefault();if(busy||!files.before||!files.after)return;
 busy=true;errorKey='';errorRaw='';noticeKey='';$('run-status').textContent='';$('error-state').hidden=true;$('new-view').hidden=true;$('results').hidden=true;$('processing').hidden=false;processingKey='reading';$('processing-status').textContent=t(processingKey);updateControls();
 const started=performance.now();
 try{
  const [before,after]=await Promise.all([encode(files.before),encode(files.after)]);
  processingKey=$('use-ai').checked?'processingAI':'processing';$('processing-status').textContent=t(processingKey);
  const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({before,after,useAI:$('use-ai').checked,config}),signal:AbortSignal.timeout(150000)});
  const data=await response.json();if(!response.ok){const err=new Error('genericError');err.serverDetail=String(data.error||'');throw err;}
  if(!Array.isArray(data.findings)||!Array.isArray(data.before?.paragraphs)||!Array.isArray(data.after?.paragraphs))throw new Error('genericError');
  result={...data,timestamp:new Date().toISOString(),seconds:(performance.now()-started)/1000};selectedId=null;activeTab='departments';
  $('finding-search').value='';$('unreviewed-only').checked=false;$('type-filter').value='all';$('department-filter').value='all';
  panes.left='before';panes.right='after';busy=false;showView('results');$('main').focus({preventScroll:true});
 }catch(err){busy=false;showView('new');showError(err.name==='TimeoutError'?'timeout':err.message==='readError'?'readError':err instanceof TypeError?'serverUnavailable':'genericError',err.serverDetail||'');}
 finally{busy=false;$('processing').hidden=true;updateControls();}
});
function renderFilterOptions(){
 const type=$('type-filter').value||'all',department=$('department-filter').value||'all';
 $('type-filter').innerHTML=`<option value="all">${esc(t('allTypes'))}</option>`+kinds.map(key=>`<option value="${key}">${esc(t(key))}</option>`).join('');$('type-filter').value=type;
 $('department-filter').innerHTML=`<option value="all">${esc(t('allDepartments'))}</option><option value="unassigned">${esc(t('unassigned'))}</option>`+departmentNames().map(name=>`<option value="${esc(name)}">${esc(name)}</option>`).join('');
 $('department-filter').value=department;if(!$('department-filter').value)$('department-filter').value='all';
}
function warningMarkup(raw){
 let message='fallbackWarning',params={},detail=raw;
 if(raw.startsWith('Загружены одинаковые файлы')){message='sameFiles';detail='';}
 else if(raw.startsWith('Отброшено выводов')){message='rejected';params.count=number(Number(raw.match(/\d+/)?.[0]||0));detail='';}
 else if(raw.startsWith('Модель не вернула допустимых')){message='noModelFindings';detail='';}
 return `<div class="notice">${icon('triangle-alert')}<div><p>${esc(t(message,params))}</p>${detail?`<details><summary>${esc(t('technicalDetails'))}</summary>${esc(detail)}</details>`:''}</div></div>`;
}
function renderResults(){
 if(!result)return;
 const checked=result.findings.filter(f=>f.reviewed).length;
 $('result-eyebrow').textContent=t(result.mode==='fallback'?'partial':'complete');
 $('result-date').textContent=t('completedAt',{date:date(result.timestamp),seconds:number(Math.round(result.seconds*10)/10)});
 $('run-method').innerHTML=icon(result.mode==='fallback'?'triangle-alert':'git-compare-arrows')+esc(t(modeKey()));
 $('coverage').textContent=`${t('beforeShort')}: ${t('paragraphCount',{count:number(result.before.paragraphs.length)})} · ${t('afterShort')}: ${t('paragraphCount',{count:number(result.after.paragraphs.length)})}`;
 $('warnings').innerHTML=(result.warnings||[]).map(warningMarkup).join('')+(language!=='ru'?`<div class="notice">${icon('info')}<p>${esc(t('dataLanguage'))}</p></div>`:'');
 const cards=[['candidates',result.findings.length,'files'],['departments',result.findings.filter(f=>groupTypes.departments.includes(f.type)).length,'building'],['risks',result.findings.filter(f=>groupTypes.risks.includes(f.type)).length,'triangle-alert'],['reviewed',checked,'circle-check']];
 $('summary-cards').innerHTML=cards.map(([label,count,glyph])=>`<div class="summary-card"><span>${esc(t(label))}</span>${icon(glyph)}<strong>${number(count)}</strong>${label==='reviewed'?`<small>/ ${number(result.findings.length)}</small>`:''}</div>`).join('');
 $('nav-count').hidden=false;$('nav-count').textContent=number(result.findings.length);
 document.querySelectorAll('[data-tab]').forEach(button=>{const active=button.dataset.tab===activeTab;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});
 document.querySelectorAll('[data-tab-count]').forEach(el=>el.textContent=number(result.findings.filter(f=>groupTypes[el.dataset.tabCount].includes(f.type)).length));
 $('result-panel').setAttribute('aria-labelledby','tab-'+activeTab);$('filter-bar').hidden=activeTab==='report';$('findings').hidden=activeTab==='report';$('conclusion').hidden=activeTab!=='report';
 renderFindings();renderConclusion();updateControls();
}
function sourceButton(f){return `<button class="source-button" data-finding="${esc(f.id)}">${icon('external-link')}${esc(t('showSources'))}</button>`;}
function renderFindings(){
 const list=visibleFindings();$('finding-count').textContent=t('shown',{count:number(list.length),total:number(result.findings.filter(f=>groupTypes[activeTab]?.includes(f.type)).length)});
 if(!list.length){$('findings').innerHTML=`<div class="empty-results">${icon('search')}<h3>${esc(t('emptyResults'))}</h3><p>${esc(t('emptyResultsHint'))}</p><button class="secondary" data-clear-filters>${esc(t('clearFilters'))}</button></div>`;return;}
 const functional=activeTab==='functions';
 $('findings').innerHTML=`<div class="table-scroll"><table class="findings-table"><thead><tr><th>${esc(t(functional?'function':'change'))}</th>${functional?`<th>${esc(t('beforeDept'))}</th><th>${esc(t('afterDept'))}</th>`:''}<th>${esc(t('typeFilter'))}</th><th>${esc(t('sources'))}</th></tr></thead><tbody>`+list.map(f=>{
  const text=functional?(sourceText(f,'before')||sourceText(f,'after')||f.title):f.title;
  return `<tr data-row="${esc(f.id)}"><td><h3 class="finding-title">${esc(text.length>260?text.slice(0,260)+'…':text)}</h3><p class="finding-explanation">${esc(f.explanation)}</p><span class="finding-method">${esc(method(f))} · ${esc(f.id)}</span></td>${functional?`<td class="owner-cell" data-label="${esc(t('beforeDept'))}">${esc(t('unknownOwner'))}</td><td class="owner-cell" data-label="${esc(t('afterDept'))}">${esc(t('unknownOwner'))}</td>`:''}<td>${typeBadge(f)}${f.reviewed?`<div><span class="review-badge">${icon('circle-check')}${esc(t(f.status))}</span></div>`:`<p class="review-pending">${esc(t('notReviewed'))}</p>`}</td><td class="source-cell">${sourceButton(f)}<small>${esc(t('sourceCount',{count:number(f.before_ids.length+f.after_ids.length)}))}</small></td></tr>`;
 }).join('')+'</tbody></table></div>';
}
function reportLines(){const reviewed=result.findings.filter(f=>f.reviewed);return [t('reportPair',{before:result.before.name,after:result.after.name}),t('reportCounts',{total:number(result.findings.length),reviewed:number(reviewed.length),confirmed:number(reviewed.filter(f=>f.status==='confirmed').length)}),t(modeKey()),t('limitsText')];}
function renderConclusion(){
 $('conclusion').innerHTML=`<div class="report-content"><p class="eyebrow">${esc(date(result.timestamp))}</p><h2>${esc(t('reportTitle'))}</h2>${reportLines().map(line=>`<p>${esc(line)}</p>`).join('')}<div class="advisory">${icon('info')}<p>${esc(t('advisory'))}</p></div><h3>${esc(t('questions'))}</h3>${result.findings.length?result.findings.map(f=>`<div class="report-question"><div><strong>${esc(f.title)}</strong>${typeBadge(f)}<p class="helper">${esc(f.reviewed?t(f.status):t('notReviewed'))}${f.note?' · '+esc(f.note):''}</p></div>${sourceButton(f)}</div>`).join(''):`<p>${esc(t('noFindings'))}</p>`}<h3>${esc(t('recommendations'))}</h3><p>${esc(t('recommendationText'))}</p><p class="helper">${esc(t('reportLanguage'))}</p></div>`;
}
function setTab(tab){activeTab=tab;showView(tab==='report'?'report':'results');}
document.querySelectorAll('[data-tab]').forEach(el=>{
 el.addEventListener('click',()=>setTab(el.dataset.tab));
 el.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const tabs=[...document.querySelectorAll('[data-tab]')],index=tabs.indexOf(el),next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(index+(e.key==='ArrowLeft'?-1:1)+tabs.length)%tabs.length;setTab(tabs[next].dataset.tab);tabs[next].focus();});
});
for(const id of ['finding-search','type-filter','department-filter','unreviewed-only'])$(id).addEventListener(id==='finding-search'?'input':'change',()=>{if(result)renderFindings();});
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-finding]');if(button&&result){evidenceOpener=button;selectedId=button.dataset.finding;renderEvidence(true);$('evidence').showModal();$('evidence-close').focus();return;}
 if(e.target.closest('[data-clear-filters]')){$('finding-search').value='';$('type-filter').value='all';$('department-filter').value='all';$('unreviewed-only').checked=false;renderFindings();$('finding-search').focus();}
 if(e.target.closest('[data-show-context]')){$('related-only').checked=false;renderPanes(true);}
 const original=e.target.closest('[data-original]');if(original){const file=files[panes[original.dataset.original]];if(file)downloadBlob(file,file.name);}
});
function navigationFindings(){const list=activeTab==='report'?result.findings:visibleFindings();return list.some(f=>f.id===selectedId)?list:result.findings;}
function renderEvidence(focus=true){
 const f=selectedFinding();if(!f)return;
 $('evidence-title').textContent=f.title;$('evidence-explanation').textContent=f.explanation;$('evidence-method').textContent=`${method(f)} · ${f.id} · ${t(f.type)}`;
 for(const panel of ['left','right']){
  $(panel+'-document').innerHTML=['before','after'].map(side=>`<option value="${side}">${esc(t(side+'Short'))} · ${esc(result[side].name)}</option>`).join('');
  $(panel+'-document').value=panes[panel];
 }
 renderPanes(focus);
 $('review-select').innerHTML=(!f.reviewed?`<option value="" disabled selected>${esc(t('chooseReview'))}</option>`:'')+reviewStatuses.map(status=>`<option value="${status}" ${f.reviewed&&status===f.status?'selected':''}>${esc(t(status))}</option>`).join('');
 $('review-select').dataset.review=f.id;$('review-select').setAttribute('aria-label',t('reviewLabel'));
 $('analyst-note').value=f.note||'';$('analyst-note').dataset.note=f.id;
 $('review-status').textContent=t(f.reviewed?'savedSession':'notReviewed');
 $('source-language-note').hidden=language==='ru';
 const list=navigationFindings(),index=list.findIndex(item=>item.id===f.id);
 $('finding-position').textContent=t('of',{index:number(index+1),total:number(list.length)});
 $('previous-finding').disabled=index<=0;$('next-finding').disabled=index>=list.length-1;
}
function renderPanes(focus=false){for(const panel of ['left','right'])renderPane(panel,focus);}
function renderPane(panel,focus=false){
 const side=panes[panel],doc=result[side],f=selectedFinding(),ids=new Set(f[side+'_ids']),linked=doc.paragraphs.filter(p=>ids.has(p.id));
 $(panel+'-document').value=side;$(panel+'-document').title=doc.name;
 $(panel+'-meta').textContent=t('paragraphCount',{count:number(doc.paragraphs.length)});$(panel+'-meta').title=`SHA-256 ${doc.sha256}`;
 const notice=$(panel+'-notice');notice.innerHTML=icon(linked.length?'file-text':'triangle-alert')+esc(linked.length?t('linkedCount',{count:number(linked.length)}):t('noSource'));notice.classList.toggle('no-source',!linked.length);
 const text=$(panel+'-text'),previousScroll=text.scrollTop,related=$('related-only').checked;
 const keep=new Set();doc.paragraphs.forEach((p,i)=>{if(ids.has(p.id))for(let j=Math.max(0,i-1);j<=Math.min(doc.paragraphs.length-1,i+1);j++)keep.add(j);});
 if(related&&!linked.length){text.innerHTML=`<div class="empty-source">${esc(t('noEvidenceText'))}</div><button class="secondary context-button" data-show-context>${esc(t('allText'))}</button>`;return;}
 let hidden=false;
 text.innerHTML=doc.paragraphs.map((p,i)=>{
  if(related&&!keep.has(i)){hidden=true;return '';}
  const gap=hidden?`<button class="text-button context-button" data-show-context>${esc(t('allText'))}</button>`:'';hidden=false;
  return `${gap}<div class="doc-paragraph ${ids.has(p.id)?'linked tone-'+tone(f.type):''}" data-paragraph="${esc(p.id)}"><span class="paragraph-id">${esc(p.id)}</span><div><span class="source-ref">${esc(t('paragraph',{section:p.section||t('noNumber'),id:p.id}))}</span><p class="paragraph-copy">${esc(p.text)}</p></div></div>`;
 }).join('')+(hidden?`<button class="text-button context-button" data-show-context>${esc(t('allText'))}</button>`:'');
 text.scrollTop=previousScroll;
 if(focus){const target=text.querySelector('.linked');text.scrollTop=target?Math.max(0,target.offsetTop-24):0;}
}
$('evidence-close').addEventListener('click',()=>$('evidence').close());
$('evidence').addEventListener('close',()=>{
 const replacement=[...document.querySelectorAll('[data-finding]')].find(el=>el.dataset.finding===selectedId&&el.getClientRects().length);
 (evidenceOpener?.isConnected?evidenceOpener:replacement||$('finding-search')).focus({preventScroll:true});
});
for(const panel of ['left','right'])$(panel+'-document').addEventListener('change',e=>{panes[panel]=e.target.value;renderPane(panel,true);});
$('related-only').addEventListener('change',()=>renderPanes(true));
$('swap-panes').addEventListener('click',()=>{[panes.left,panes.right]=[panes.right,panes.left];renderPanes(true);});
$('review-select').addEventListener('change',e=>{const f=selectedFinding();if(!f||!reviewStatuses.includes(e.target.value))return;f.status=e.target.value;f.reviewed=true;renderResults();$('review-status').textContent=t('savedSession');});
$('analyst-note').addEventListener('input',e=>{const f=selectedFinding();if(f){f.note=e.target.value;renderConclusion();}});
for(const [id,step] of [['previous-finding',-1],['next-finding',1]])$(id).addEventListener('click',()=>{const list=navigationFindings(),index=list.findIndex(f=>f.id===selectedId);if(list[index+step]){selectedId=list[index+step].id;renderEvidence(true);}});
const resizer=$('pane-resizer');
function setSplit(value){split=Math.max(30,Math.min(70,value));$('document-panes').style.setProperty('--left-width',`calc(${split}% - 3px)`);resizer.setAttribute('aria-valuenow',String(Math.round(split)));}
resizer.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home'].includes(e.key)){e.preventDefault();setSplit(e.key==='Home'?50:split+(e.key==='ArrowLeft'?-5:5));}});
resizer.addEventListener('dblclick',()=>setSplit(50));resizer.addEventListener('pointerdown',e=>{if(e.button===0)resizer.setPointerCapture(e.pointerId);});
resizer.addEventListener('pointermove',e=>{if(resizer.hasPointerCapture(e.pointerId)){const rect=$('document-panes').getBoundingClientRect();setSplit((e.clientX-rect.left)/rect.width*100);}});
resizer.addEventListener('pointerup',e=>{if(resizer.hasPointerCapture(e.pointerId))resizer.releasePointerCapture(e.pointerId);});
function openSettings(opener){if(busy)return;$('settings-error').hidden=true;settingsOpener=opener;setNav(false);$('api-base').value=config.base;$('api-model').value=config.model;$('api-key').value=config.key;$('settings').showModal();}
for(const id of ['settings-open','settings-inline'])$(id).addEventListener('click',e=>openSettings(e.currentTarget));
$('settings-close').addEventListener('click',()=>$('settings').close());$('settings').addEventListener('close',()=>{if(settingsOpener?.getClientRects().length)settingsOpener.focus();else $('open-nav').focus();});
$('provider').addEventListener('change',()=>{$('api-base').value=$('provider').value==='local'?'http://127.0.0.1:11434/v1':'https://api.openai.com/v1';$('api-key').value='';});
$('settings-form').addEventListener('submit',e=>{e.preventDefault();let valid=false;try{valid=['http:','https:'].includes(new URL($('api-base').value.trim()).protocol)&&!!$('api-model').value.trim();}catch{}if(!valid){$('settings-error').hidden=false;return;}config={base:$('api-base').value.trim(),model:$('api-model').value.trim(),key:$('api-key').value.trim()};$('use-ai').checked=true;$('settings').close();updateControls();noticeKey='modelSettingsSaved';$('run-status').textContent=t(noticeKey);});
$('use-ai').addEventListener('change',updateControls);
function downloadBlob(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}
$('download').addEventListener('click',()=>{
 if(!result)return;
 const lines=['# '+t('reportTitle'),date(result.timestamp),'',...reportLines(),t('advisory'),...(result.warnings||[]).map(w=>t('warning')+': '+w),`SHA-256 ${t('beforeShort')}: ${result.before.sha256}`,`SHA-256 ${t('afterShort')}: ${result.after.sha256}`];
 for(const f of result.findings){
  lines.push('',`## ${f.title}`,`${t('typeFilter')}: ${t(f.type)}; ${t('status')}: ${f.reviewed?t(f.status):t('notReviewed')}; ${t('method')}: ${method(f)}`,f.explanation);
  if(f.note)lines.push(t('note')+': '+f.note);
  for(const side of ['before','after']){
   if(!f[side+'_ids'].length)lines.push(t(side+'Short')+': '+t('noSource'));
   for(const id of f[side+'_ids']){const p=result[side].paragraphs.find(p=>p.id===id);if(p)lines.push(`${t('sources')}: ${result[side].name} · ${t(side+'Short')} · ${t('paragraph',{section:p.section||t('noNumber'),id})}`,p.text.split('\n').map(line=>'> '+line).join('\n'));}
  }
 }
 lines.push('',t('recommendations'),t('recommendationText'));downloadBlob(new Blob([lines.join('\n\n')],{type:'text/markdown;charset=utf-8'}),`osnovanie-${language}.md`);noticeKey='exportDone';$('run-status').textContent=t(noticeKey);
});
hydrateIcons();renderLocale();
fetch('/api/config').then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{config.base=data.base;config.model=data.model;serverHasKey=!!data.hasKey;$('key-note').hidden=!serverHasKey;updateControls();}).catch(()=>showError('serverUnavailable'));
