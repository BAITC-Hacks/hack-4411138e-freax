import {t,number,date,language,setLanguage,translate,dictionaries} from './i18n.js';
import {icon,hydrateIcons} from './icons.js';
import {initPresentation,renderPresentation,renderInfo} from './ayqyn.js';
import {buildReport} from './report.js';
import {createWorkspace} from './workspace.js';
import {adaptDemo} from './demo.js';
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const kinds=['department_added','department_retained','department_removed','reorganization','function_loss','function_transfer','duplication','conflict','contradiction'];
const reviewStatuses=['unknown','risk','confirmed','dismissed'];
const groupTypes={departments:kinds.slice(0,4),functions:kinds.slice(4),risks:['function_loss','duplication','conflict','contradiction']};
let files=[],batchError='',classificationReview=false,result=null,busy=false,view='new',activeTab='departments',selectedId=null;
let config={base:'https://api.openai.com/v1',model:'gpt-4.1-mini',key:''},serverHasKey=false,noticeKey='',errorKey='',errorRaw='',processingKey='reading';
let liveResult=null,demoResult=null,route='/',fileRejections=[],sampleFiles=false,demoLoading=null;
let evidenceOpener=null,settingsOpener=null,split=50;
let caseWorkspace,configTouched=false,configReady=false;
let navCollapsed=false;try{navCollapsed=localStorage.getItem('distingt.sidebarCollapsed')==='true';}catch{}
const panes={left:'before',right:'after'};
const selectedFinding=()=>result?.findings.find(f=>f.id===selectedId);
const modeKey=(snapshot=result)=>snapshot?.mode==='demo'?'demoMode':snapshot?.mode==='ai'?'aiMode':snapshot?.mode==='fallback'?'fallbackMode':'rulesMode';
const tone=type=>['department_removed','function_loss'].includes(type)?'loss':['duplication','conflict','contradiction'].includes(type)?'risk':type==='department_added'?'added':type==='department_retained'?'neutral':'transfer';
const typeIcon=type=>tone(type)==='loss'||tone(type)==='risk'?'triangle-alert':tone(type)==='added'?'plus':tone(type)==='neutral'?'check':'git-compare-arrows';
const typeBadge=f=>`<span class="status-badge tone-${tone(f.type)}">${icon(typeIcon(f.type))}${esc(t(f.type))}</span>`;
const method=(f,tt=t)=>tt(f.method==='demo'?'demoMethod':f.method==='llm'?'modelMethod':'ruleMethod');
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
 return result.findings.filter(f=>(['report','overview'].includes(activeTab)||groupTypes[activeTab].includes(f.type))&&
  (type==='all'||f.type===type)&&(!$('unreviewed-only').checked||!f.reviewed)&&
  (department==='all'||(department==='unassigned'?!departmentNames().some(name=>matchesDepartment(f,name)):matchesDepartment(f,department)))&&
  (!search||`${f.title} ${f.explanation} ${t(f.type)} ${sourceText(f,'before')} ${sourceText(f,'after')}`.toLocaleLowerCase().includes(search)));
}
function updateTheme(preference){
 document.documentElement.dataset.themePreference=preference;
 document.documentElement.dataset.theme=preference==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):preference;
 document.body.classList.toggle('light',document.documentElement.dataset.theme==='light');$('theme-select').value=preference;
 $('theme-icon').innerHTML=icon(preference==='system'?'monitor':preference==='dark'?'moon':'sun');
 try{localStorage.setItem('osnovanie.theme',preference);}catch{}
}
$('theme-select').addEventListener('change',e=>updateTheme(e.target.value));
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(document.documentElement.dataset.themePreference==='system')updateTheme('system');});
function renderLocale(){
 renderPresentation();if(route==='/guide'||route==='/about'||route==='/data-policy')renderInfo(route);hydrateIcons();translate();document.querySelectorAll('[data-lang]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.lang===language)));
 $('page-title').textContent=t(view==='new'?'newAnalysis':view==='report'?'report':'results');
 $('processing-status').textContent=t(processingKey);$('key-note').hidden=!serverHasKey;
 $('run-status').textContent=noticeKey?t(noticeKey):'';
 $('error-message').textContent=errorKey?t(errorKey):'';
 updateTheme(document.documentElement.dataset.themePreference||'system');applySidebarPreference();
 renderFiles();updateControls();if(result){renderFilterOptions();renderResults();if($('evidence').open)renderEvidence(false);}
 caseWorkspace?.locale();
 $('previous-finding').setAttribute('aria-label',t('previous'));$('next-finding').setAttribute('aria-label',t('next'));
}
document.querySelectorAll('[data-lang]').forEach(button=>button.addEventListener('click',()=>{setLanguage(button.dataset.lang);renderLocale();}));
document.addEventListener('change',e=>{if(e.target.matches('[data-approved-language]')){setLanguage(e.target.value);renderLocale();}});
document.addEventListener('click',e=>{if(e.target.closest('[data-approved-theme]')){updateTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');renderPresentation();if(route==='/guide'||route==='/about'||route==='/data-policy')renderInfo(route);}});
const navMedia=matchMedia('(max-width: 750px)');
function applySidebarPreference(){
 document.body.classList.toggle('nav-collapsed',navCollapsed&&!navMedia.matches);
 $('collapse-sidebar').setAttribute('aria-expanded',String(!navCollapsed));
 $('collapse-sidebar').setAttribute('aria-label',t(navCollapsed?'expandNav':'collapseNav'));
 $('collapse-sidebar').innerHTML=icon(navCollapsed?'menu':'chevron-left');
 $('sidebar').inert=navMedia.matches?!$('sidebar').classList.contains('open'):navCollapsed;
}
function setNav(open){
 $('sidebar').classList.toggle('open',open);$('nav-backdrop').hidden=!open;
 $('open-nav').setAttribute('aria-expanded',String(open));
 document.body.classList.toggle('mobile-nav-open',open&&navMedia.matches);
 applySidebarPreference();if(open)$('close-nav').focus({preventScroll:true});
}
navMedia.addEventListener('change',()=>setNav(false));setNav(false);
$('collapse-sidebar').addEventListener('click',()=>{navCollapsed=!navCollapsed;try{localStorage.setItem('distingt.sidebarCollapsed',String(navCollapsed));}catch{}applySidebarPreference();dispatchEvent(new Event('resize'));});
$('open-nav').addEventListener('click',()=>setNav(true));
for(const id of ['close-nav','nav-backdrop'])$(id).addEventListener('click',()=>{setNav(false);$('open-nav').focus({preventScroll:true});});
function closeLanguageMenus(returnFocus=false){
 document.querySelectorAll('[data-language-toggle][aria-expanded="true"]').forEach(button=>{button.setAttribute('aria-expanded','false');button.parentElement.querySelector('.language-options').hidden=true;if(returnFocus)button.focus({preventScroll:true});});
}
document.addEventListener('click',e=>{
 const toggle=e.target.closest('[data-language-toggle]'),choice=e.target.closest('[data-language-choice]');
 if(toggle){const opening=toggle.getAttribute('aria-expanded')!=='true';closeLanguageMenus();toggle.setAttribute('aria-expanded',String(opening));const menu=toggle.parentElement.querySelector('.language-options');menu.hidden=!opening;if(opening)menu.querySelector('[aria-checked="true"]')?.focus({preventScroll:true});return;}
 if(choice){const container=choice.closest('#workspace-controls')||choice.closest('#info-view')||$('landing-view');setLanguage(choice.dataset.languageChoice);renderLocale();container.querySelector('[data-language-toggle]')?.focus({preventScroll:true});return;}
 if(!e.target.closest('.language-menu'))closeLanguageMenus();
 if(e.target.closest('[data-processing-settings]'))openSettings(e.target.closest('[data-processing-settings]'));
});
document.addEventListener('keydown',e=>{
 const menu=e.target.closest('.language-menu');
 if(menu){const toggle=menu.querySelector('[data-language-toggle]'),items=[...menu.querySelectorAll('[data-language-choice]')];
  if(e.key==='Escape'){e.preventDefault();closeLanguageMenus(true);return;}
  if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();if(toggle.getAttribute('aria-expanded')!=='true'){closeLanguageMenus();toggle.setAttribute('aria-expanded','true');menu.querySelector('.language-options').hidden=false;}const i=items.indexOf(document.activeElement);items[e.key==='Home'?0:e.key==='End'?items.length-1:e.key==='ArrowDown'?(i+1)%items.length:i<0?items.length-1:(i-1+items.length)%items.length].focus();return;}
  if(e.key==='Tab')closeLanguageMenus();
 }
 if(!$('sidebar').classList.contains('open'))return;
 if(e.key==='Escape'){e.preventDefault();setNav(false);$('open-nav').focus({preventScroll:true});}
 if(e.key==='Tab'){const items=[...$('sidebar').querySelectorAll('a,button:not(:disabled)')].filter(el=>el.getClientRects().length);const first=items[0],last=items.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
});
function showView(next){
 view=next;
 const publicView=['landing','info'].includes(next);
 document.body.dataset.context=publicView?'public':'workspace';
 for(const [id,value] of [['landing-view','landing'],['info-view','info'],['empty-view','empty'],['new-view','new'],['results','results'],['case-workspace','case'],['cases-view','cases']])$(id).hidden=next!==value;
 if(next==='report')$('results').hidden=false;
 $('processing').hidden=!busy||next!=='new';
 if(busy&&next==='new'){$('new-view').hidden=true;$('results').hidden=true;}
 $('page-title').textContent=t(next==='new'?'newAnalysis':next==='report'?'report':'results');
 document.querySelectorAll('[data-view]').forEach(el=>{el.classList.toggle('active',el.dataset.view===next);if(el.dataset.view===next)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
 setNav(false);if(result){renderFilterOptions();renderResults();}if(next==='case')caseWorkspace?.render();updateControls();
}
function navigate(path){if(location.hash==='#'+path)applyRoute();else location.hash=path;}
async function applyRoute(){
 const requested=location.hash.slice(1)||'/';
 if(['#main','#capabilities'].includes(location.hash))return;
 route=requested==='/capabilities'?'/':requested.split('#')[0];
 if($('evidence').open)$('evidence').close();caseWorkspace?.deactivate();
 if(['/guide','/about','/data-policy'].includes(route)){renderInfo(route);showView('info');}
 else if(route==='/app/demo'){
  try{
   if(!demoResult){demoLoading??=fetch('assets/c010/demo.json').then(r=>{if(!r.ok)throw Error();return r.json();}).then(adaptDemo).finally(()=>{demoLoading=null;});demoResult=await demoLoading;}
   if(route!=='/app/demo')return;
   const c=await caseWorkspace.create(demoResult,[],'','demo-C010-v1');
   if(route!=='/app/demo')return;
   await caseWorkspace.open(c.id);showView('case');
   const demoFinding=requested.split('#finding-')[1];if(demoFinding&&result.findings.some(f=>f.id===demoFinding)){caseWorkspace.showTab('results');activeTab='risks';renderResults();selectedId=demoFinding;renderEvidence(true);$('evidence').showModal();renderPanes(true);$('evidence-close').focus();}
  }catch{showView('empty');showError('exampleError');}
 }else if(route.startsWith('/app/cases/')){
  const requestedRoute=route;const id=decodeURIComponent(route.slice('/app/cases/'.length));
  const found=await caseWorkspace.open(id);if(route!==requestedRoute)return;showView(found?'case':'cases');
 }else if(route==='/app'||route==='/app/cases'){
  await caseWorkspace.ready;caseWorkspace.renderList();showView('cases');
 }else if(['/app/results','/app/report'].includes(route)){
  await caseWorkspace.ready;const c=caseWorkspace.active||caseWorkspace.records.find(c=>c.kind!=='demo');
  if(c){await caseWorkspace.open(c.id,route==='/app/report'?'report':'results');showView('case');}else showView('empty');
 }else if(route==='/app/new'||route==='new'){result=liveResult;showView('new');}
 else {route='/';showView('landing');}
 hydrateIcons();window.scrollTo({top:0,behavior:'instant'});
 const anchor=requested==='/capabilities'?'capabilities':requested.split('#')[1];if(anchor&&['capabilities','how'].includes(anchor))$(anchor)?.scrollIntoView({block:'start'});
}
function resetFilters(){$('finding-search').value='';$('unreviewed-only').checked=false;$('type-filter').value='all';$('department-filter').value='all';}
history.scrollRestoration='manual';
window.addEventListener('hashchange',applyRoute);
document.addEventListener('click',e=>{const link=e.target.closest('a[href^="#/"]');if(link&&!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&!e.altKey){e.preventDefault();navigate(link.getAttribute('href').slice(1));}});
document.querySelectorAll('[data-view]').forEach(el=>el.addEventListener('click',()=>{
 if(el.dataset.view==='new')navigate('/app/new');
 else if(caseWorkspace?.active){caseWorkspace.showTab(el.dataset.view==='report'?'report':'results');navigate(caseWorkspace.casePath(caseWorkspace.active.id));}
 else navigate(el.dataset.view==='report'?'/app/report':'/app/results');
}));
function updateControls(){
 if(!result)$('nav-count').hidden=true;
 $('run').disabled=busy||!configReady||files.length<2;
 $('run-reason').textContent=files.length<2?t('needFiles'):t('packetReady',{count:files.length});
 $('run-label').textContent=t(errorKey?'retry':'start');
 for(const id of ['load-example','batch-file','use-ai','settings-open','settings-inline','before-file','after-file'])$(id).disabled=busy;
 document.querySelectorAll('[data-remove],[data-side-select]').forEach(el=>el.disabled=busy);
 document.querySelectorAll('[data-view]').forEach(el=>{el.disabled=busy||(el.dataset.view!=='new'&&!result);el.title=el.disabled&&!busy?t('availableAfter'):'';});
 $('processing-availability').textContent=t(!configReady?'checkingAvailability':$('use-ai').checked?'analysisAvailable':'textComparisonAvailable');
 $('upload-form').setAttribute('aria-busy',String(busy));
}
function renderFiles(){
 $('batch-list').innerHTML=files.map((item,index)=>`<div class="packet-file"><span class="file-glyph">${icon('file-text')}</span><div class="packet-name"><strong>${esc(item.file.name)}</strong><small>${number(Math.round(item.file.size/1024))} KB · ${item.classification?esc(t('class_'+item.classification)):esc(t('awaitingClassification'))}</small></div><label><span class="sr-only">${esc(t('versionFor',{name:item.file.name}))}</span><select data-side-select="${index}" aria-label="${esc(t('versionFor',{name:item.file.name}))}">${['auto','before','after'].map(side=>`<option value="${side}" ${item.side===side?'selected':''}>${esc(t(side==='auto'?'automatic':side+'Short'))}</option>`).join('')}</select></label><button type="button" class="icon-button" data-remove="${index}" aria-label="${esc(t('removeFile',{name:item.file.name}))}">${icon('trash')}</button></div>`).join('');
 $('batch-error').hidden=!batchError;$('batch-error').textContent=batchError?t(batchError):'';
 $('classification-review').hidden=!classificationReview;
 $('file-rejections').innerHTML=fileRejections.map(item=>`<p class="file-error"><strong>${esc(item.name)}</strong> — ${esc(t(item.reason))}</p>`).join('');
 for(const side of ['before','after'])$(side+'-packet-count').textContent=t('packetCount',{count:number(files.filter(item=>item.side===side).length)});
 $('packet-count').textContent=t('packetCount',{count:number(files.length)});
}
function invalidateResult(){liveResult=null;result=null;selectedId=null;$('nav-count').hidden=true;$('error-state').hidden=true;errorKey='';noticeKey='';$('run-status').textContent='';if($('evidence').open)$('evidence').close();showView('new');}
function acceptFiles(selection,side='auto'){
 if(busy||!selection.length)return;
 fileRejections=[];let accepted=0;
 for(const file of selection){
  const reason=!file.name.toLowerCase().endsWith('.docx')?'fileTypeError':!file.size||file.size>10000000?'fileSizeError':files.length>=20?'packetCountError':files.reduce((sum,item)=>sum+item.file.size,0)+file.size>20000000?'packetSizeError':'';
  if(reason)fileRejections.push({name:file.name,reason});else{files.push({file,side,classification:side==='auto'?null:'manual'});accepted++;}
 }
 if(accepted){sampleFiles=false;classificationReview=false;invalidateResult();}
 batchError='';for(const id of ['batch-file','before-file','after-file'])$(id).value='';renderFiles();updateControls();
}
for(const [id,side,zone] of [['batch-file','auto',$('packet-drop')],['before-file','before',document.querySelector('[data-upload-side="before"]')],['after-file','after',document.querySelector('[data-upload-side="after"]')]]){
 $(id).addEventListener('change',e=>acceptFiles([...e.target.files],side));
 for(const event of ['dragenter','dragover'])zone.addEventListener(event,e=>{e.preventDefault();if(!busy)zone.classList.add('dragging');});
 for(const event of ['dragleave','drop'])zone.addEventListener(event,e=>{e.preventDefault();zone.classList.remove('dragging');if(event==='drop')acceptFiles([...e.dataTransfer.files],side);});
}
$('batch-list').addEventListener('change',e=>{const index=e.target.dataset.sideSelect;if(index===undefined||busy)return;files[Number(index)].side=e.target.value;files[Number(index)].classification=e.target.value==='auto'?null:'manual';invalidateResult();renderFiles();updateControls();});
document.addEventListener('click',e=>{const button=e.target.closest('[data-remove]');if(!button||busy)return;files.splice(Number(button.dataset.remove),1);classificationReview=false;batchError='';invalidateResult();renderFiles();updateControls();$('batch-file').focus();});
function showError(key,raw=''){errorKey=key;errorRaw=raw;$('error-state').hidden=false;$('error-message').textContent=t(key);$('error-details').hidden=!raw;$('error-raw').textContent=raw;updateControls();}
$('load-example').addEventListener('click',async()=>{
 if(busy)return;busy=true;noticeKey='loadingExample';$('run-status').textContent=t(noticeKey);updateControls();
 try{
  const loaded=await Promise.all(window.AYQYN_EXAMPLE_SOURCES.map(async s=>{const response=await fetch(s.file);if(!response.ok)throw Error();return new File([await response.blob()],s.name,{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'});}));
  files=loaded.map(file=>({file,side:'auto'}));sampleFiles=true;fileRejections=[];batchError='';classificationReview=false;busy=false;invalidateResult();noticeKey='exampleLoaded';$('run-status').textContent=t(noticeKey);renderFiles();
 }catch{showError('exampleError');}finally{busy=false;updateControls();}
});
const encode=file=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve({name:file.name,data:String(reader.result).split(',')[1]});reader.onerror=()=>reject(new Error('readError'));reader.readAsDataURL(file);});
$('upload-form').addEventListener('submit',async e=>{
 e.preventDefault();if(busy||!configReady||files.length<2)return;
 busy=true;errorKey='';errorRaw='';noticeKey='';$('run-status').textContent='';$('error-state').hidden=true;$('new-view').hidden=true;$('results').hidden=true;$('processing').hidden=false;processingKey='reading';$('processing-status').textContent=t(processingKey);updateControls();
 const started=performance.now(),submittedRoute=location.hash,submittedFiles=files.map(item=>({...item})),submittedName=$('new-case-name').value.trim();
 try{
  const documents=await Promise.all(files.map(async item=>({...await encode(item.file),side:item.side})));
  processingKey=$('use-ai').checked?'processingAI':'processing';$('processing-status').textContent=t(processingKey);
  const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({documents,useAI:$('use-ai').checked,config}),signal:AbortSignal.timeout(270000)});
  const data=await response.json();if(!response.ok){const err=new Error('genericError');err.serverDetail=String(data.error||'');throw err;}
  if(data.needs_review){data.documents.forEach((doc,index)=>{files[index].side=doc.side||'auto';files[index].classification=doc.classification;});classificationReview=true;busy=false;showView('new');if(data.classification_warning)showError('classificationModelError',data.classification_warning);renderFiles();$('classification-review').focus();return;}
  if(!Array.isArray(data.findings)||!Array.isArray(data.before?.paragraphs)||!Array.isArray(data.after?.paragraphs))throw new Error('genericError');
  const completed={...data,synthetic:sampleFiles,timestamp:new Date().toISOString(),seconds:(performance.now()-started)/1000};
  liveResult=completed;const record=await caseWorkspace.create(completed,submittedFiles,submittedName);
  busy=false;
  if(location.hash===submittedRoute&&view==='new'){navigate(caseWorkspace.casePath(record.id));$('main').focus({preventScroll:true});}
  else caseWorkspace.notify(record.id);
 }catch(err){busy=false;if(location.hash===submittedRoute)showView('new');showError(err.name==='TimeoutError'?'timeout':err.message==='readError'?'readError':err instanceof TypeError?'serverUnavailable':'genericError',err.serverDetail||'');}
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
 $('agent-trace-list').innerHTML=(result.trace||[]).map(event=>`<li>${icon('check')}<span>${esc(t(event.stage,{count:number(event.count)}))}</span><small>${number(event.elapsed_ms)} ms</small></li>`).join('');
 $('manifest').innerHTML=(result.documents||[]).map(doc=>`<div><span class="mono">${esc(doc.id)}</span><strong>${esc(doc.name)}</strong><span class="quiet-badge">${esc(t(doc.side+'Short'))}</span><small>${esc(t('class_'+doc.classification))}</small>${doc.classification_reason?`<p class="classification-evidence">${esc(doc.classification_reason)} — «${esc(doc.classification_quote)}»</p>`:''}</div>`).join('');
 $('result-eyebrow').textContent=t(result.mode==='demo'?'demoLabel':result.mode==='fallback'?'partial':'complete');
 $('result-date').textContent=result.mode==='demo'?t('staticExample'):t('completedAt',{date:date(result.timestamp),seconds:number(Math.round(result.seconds*10)/10)});
 $('demo-banner').hidden=!result.synthetic;$('demo-banner').querySelector('p').textContent=t(result.mode==='demo'?'demoDisclosure':'sampleProcessed');
 document.querySelector('.agent-trace [data-i18n=completedRun]').hidden=result.mode==='demo';
 $('run-method').innerHTML=icon(result.mode==='fallback'?'triangle-alert':'git-compare-arrows')+esc(t(modeKey()));
 $('coverage').textContent=`${t('beforeShort')}: ${t('paragraphCount',{count:number(result.before.paragraphs.length)})} · ${t('afterShort')}: ${t('paragraphCount',{count:number(result.after.paragraphs.length)})}`;
 $('warnings').innerHTML=(result.warnings||[]).map(warningMarkup).join('')+(language!=='ru'?`<div class="notice">${icon('info')}<p>${esc(t('dataLanguage'))}</p></div>`:'');
 const cards=[['candidates',result.findings.length,'files'],['departments',result.findings.filter(f=>groupTypes.departments.includes(f.type)).length,'building'],['risks',result.findings.filter(f=>groupTypes.risks.includes(f.type)).length,'triangle-alert'],['reviewed',checked,'circle-check']];
 $('summary-cards').innerHTML=cards.map(([label,count,glyph])=>`<div class="summary-card stat"><span>${esc(t(label))}</span>${icon(glyph)}<strong>${number(count)}</strong>${label==='reviewed'?`<small>/ ${number(result.findings.length)}</small>`:''}</div>`).join('');
 $('nav-count').hidden=false;$('nav-count').textContent=t('findingsBadge',{count:number(result.findings.length)});
 document.querySelectorAll('[data-tab]').forEach(button=>{const active=button.dataset.tab===activeTab;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});
 document.querySelectorAll('[data-tab-count]').forEach(el=>el.textContent=number(result.findings.filter(f=>groupTypes[el.dataset.tabCount].includes(f.type)).length));
 $('result-panel').setAttribute('aria-labelledby','tab-'+activeTab);$('filter-bar').hidden=['report','overview'].includes(activeTab);$('findings').hidden=['report','overview'].includes(activeTab);$('overview').hidden=activeTab!=='overview';$('conclusion').hidden=activeTab!=='report';
 renderOverview();renderFindings();renderConclusion();updateControls();
}
function renderOverview(){
 const risks=result.findings.filter(f=>groupTypes.risks.includes(f.type));
 $('overview').innerHTML=`<div class="workspace-grid"><section class="panel"><h3>${esc(t('risks'))}</h3><p class="helper">${esc(t('overviewText'))}</p>${risks.map(f=>`<article class="risk"><div class="risk-top"><span class="risk-icon">${icon(typeIcon(f.type))}</span><div><h4>${esc(t(f.type))}</h4><p>${esc(f.explanation)}</p>${sourceButton(f)}<p>${esc(t(f.reviewed?f.status:'notReviewed'))}</p></div></div></article>`).join('')||`<p>${esc(t('noRisksScoped'))}</p>`}</section><div><section class="panel"><h3>${esc(t('documents'))}</h3>${(result.documents||[]).map(d=>`<div class="file-line">${icon('file-text')}<div>${esc(d.name)}<small>${esc(t(d.side+'Short'))} · ${esc(t('paragraphCount',{count:d.paragraphs.length}))}</small></div></div>`).join('')}</section><section class="panel" style="margin-top:22px"><h3>${esc(t('savedSummary'))}</h3><p class="helper">${esc(t(modeKey()))}</p>${(result.trace||[]).map(event=>`<div class="trace-row">${icon('check')}<div>${esc(t(event.stage,{count:number(event.count)}))}<small>${number(event.elapsed_ms)} ms</small></div></div>`).join('')}<p class="helper">${esc(t(result.mode==='demo'?'demoDisclosure':'advisory'))}</p></section></div></div>`;
}
function scopeText(f,snapshot=result,tt=t){
 if(f.type!=='function_loss')return '';
 const docs=(snapshot.documents||[]).filter(d=>f.search_scope?f.search_scope.includes(d.id):d.side==='after');
 return `${tt('searchScope')}: ${docs.map(d=>d.name+' ['+d.id+']').join('; ')||snapshot.after.name}. ${tt('lossCaution')}`;
}
function sourceButton(f){return `<button class="source-button" data-finding="${esc(f.id)}">${icon('external-link')}${esc(t('showSources'))}</button>${caseWorkspace?.active?`<button class="discuss-button text-button" data-discuss="${esc(f.id)}">${icon('list-checks')}${esc(t('discussAgent'))}</button>`:''}`;}
function renderFindings(){
 const list=visibleFindings();$('finding-count').textContent=t('shown',{count:number(list.length),total:number(result.findings.filter(f=>groupTypes[activeTab]?.includes(f.type)).length)});
 if(!list.length){$('findings').innerHTML=`<div class="empty-results">${icon('search')}<h3>${esc(t('emptyResults'))}</h3><p>${esc(t('emptyResultsHint'))}</p><button class="secondary" data-clear-filters>${esc(t('clearFilters'))}</button></div>`;return;}
 const functional=activeTab==='functions';
 $('findings').innerHTML=`<div class="table-scroll"><table class="findings-table"><thead><tr><th>${esc(t(functional?'function':'change'))}</th>${functional?`<th>${esc(t('beforeDept'))}</th><th>${esc(t('afterDept'))}</th>`:''}<th>${esc(t('typeFilter'))}</th><th>${esc(t('sources'))}</th></tr></thead><tbody>`+list.map(f=>{
  const text=functional?(sourceText(f,'before')||sourceText(f,'after')||f.title):f.title;
  return `<tr data-row="${esc(f.id)}"><td><h3 class="finding-title">${esc(text.length>260?text.slice(0,260)+'…':text)}</h3><p class="finding-explanation">${esc(f.explanation)}</p><span class="finding-method">${esc(method(f))} · ${esc(f.id)}</span></td>${functional?`<td class="owner-cell" data-label="${esc(t('beforeDept'))}">${esc(t('unknownOwner'))}</td><td class="owner-cell" data-label="${esc(t('afterDept'))}">${esc(t('unknownOwner'))}</td>`:''}<td>${typeBadge(f)}${f.reviewed?`<div><span class="review-badge">${icon('circle-check')}${esc(t(f.status))}</span></div>`:`<p class="review-pending">${esc(t('notReviewed'))}</p>`}</td><td class="source-cell">${sourceButton(f)}<small>${esc(t('sourceCount',{count:number(f.before_ids.length+f.after_ids.length)}))}</small></td></tr>`;
 }).join('')+'</tbody></table></div>';
}
function reportLines(snapshot=result,tt=t,nn=number){const reviewed=snapshot.findings.filter(f=>f.reviewed);return [...(snapshot.synthetic?[tt('demoLabel'),tt('demoDisclosure')]:[]),tt('reportPair',{before:snapshot.before.name,after:snapshot.after.name}),tt('reportCounts',{total:nn(snapshot.findings.length),reviewed:nn(reviewed.length),confirmed:nn(reviewed.filter(f=>f.status==='confirmed').length)}),tt(modeKey(snapshot)),tt('limitsText')];}
function renderConclusion(){
 $('conclusion').innerHTML=`<div class="report-content"><p class="eyebrow">${esc(result.mode==='demo'?t('staticExample'):date(result.timestamp))}</p><h2>${esc(t('reportTitle'))}</h2>${reportLines().map(line=>`<p>${esc(line)}</p>`).join('')}<div class="advisory">${icon('info')}<p>${esc(t('advisory'))}</p></div><h3>${esc(t('questions'))}</h3>${result.findings.length?result.findings.map(f=>`<div class="report-question"><div><strong>${esc(f.title)}</strong>${typeBadge(f)}<p class="helper">${esc(f.reviewed?t(f.status):t('notReviewed'))}${f.note?' · '+esc(f.note):''}</p></div>${sourceButton(f)}</div>`).join(''):`<p>${esc(t('noFindings'))}</p>`}<h3>${esc(t('recommendations'))}</h3><p>${esc(t('recommendationText'))}</p><p class="helper">${esc(t('reportLanguage'))}</p></div>`;
}
function setTab(tab){activeTab=tab;caseWorkspace?.saveResultTab(tab);renderResults();}
document.querySelectorAll('[data-tab]').forEach(el=>{
 el.addEventListener('click',()=>setTab(el.dataset.tab));
 el.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const tabs=[...document.querySelectorAll('[data-tab]')],index=tabs.indexOf(el),next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(index+(e.key==='ArrowLeft'?-1:1)+tabs.length)%tabs.length;setTab(tabs[next].dataset.tab);tabs[next].focus();});
});
for(const id of ['finding-search','type-filter','department-filter','unreviewed-only'])$(id).addEventListener(id==='finding-search'?'input':'change',()=>{if(result)renderFindings();});
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-finding]');if(button&&result){evidenceOpener=button;selectedId=button.dataset.finding;renderEvidence(true);$('evidence').showModal();$('evidence').querySelector('.drawer-body').scrollTop=0;renderPanes(true);$('evidence-close').focus();return;}
 if(e.target.closest('[data-clear-filters]')){$('finding-search').value='';$('type-filter').value='all';$('department-filter').value='all';$('unreviewed-only').checked=false;renderFindings();$('finding-search').focus();}
 if(e.target.closest('[data-show-context]')){$('related-only').checked=false;renderPanes(true);}
 const original=e.target.closest('[data-original]');if(original){const docId=panes[original.dataset.original],index=result.documents?.findIndex(doc=>doc.id===docId);const doc=result.documents?.[index];if(result.mode==='demo'&&doc?.original_url){const a=document.createElement('a');a.href=doc.original_url;a.download=doc.id+'.pdf';a.click();}else{const file=(caseWorkspace?.active?.files||files)[index]?.file;if(file)downloadBlob(file,file.name);}}
});
function navigationFindings(){const list=activeTab==='report'?result.findings:visibleFindings();return list.some(f=>f.id===selectedId)?list:result.findings;}
function renderEvidence(focus=true){
 const f=selectedFinding();if(!f)return;
 $('evidence-demo').hidden=!result.synthetic;$('evidence-demo').textContent=t(result.mode==='demo'?'demoDisclosure':'sampleProcessed');$('evidence-scope').hidden=f.type!=='function_loss';$('evidence-scope').textContent=scopeText(f);
 $('evidence-title').textContent=f.title;$('evidence-explanation').textContent=f.explanation;$('evidence-explanation').hidden=f.title===f.explanation;$('evidence-method').textContent=`${method(f)} · ${f.id} · ${t(f.type)}`;
 for(const panel of ['left','right']){
  const docs=result.documents?.length?result.documents:['before','after'].map(side=>({...result[side],id:side,side}));
  if(focus){const side=panel==='left'?'before':'after',linked=docs.find(doc=>doc.side===side&&doc.paragraphs.some(p=>f[side+'_ids'].includes(p.id)));panes[panel]=(linked||docs.find(doc=>doc.side===side)).id;}
  $(panel+'-document').innerHTML=docs.map(doc=>`<option value="${esc(doc.id)}">${esc(t(doc.side+'Short'))} · ${esc(doc.name)}</option>`).join('');
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
 const doc=result.documents?.find(doc=>doc.id===panes[panel])||result[panes[panel]],side=doc.side||panes[panel],f=selectedFinding(),ids=new Set(f[side+'_ids']),linked=doc.paragraphs.filter(p=>ids.has(p.id));
 $(panel+'-document').value=panes[panel];$(panel+'-document').title=doc.name;
 $(panel+'-meta').textContent=t('paragraphCount',{count:number(doc.paragraphs.length)});$(panel+'-meta').title=doc.sha256?`SHA-256 ${doc.sha256}`:'';
 const notice=$(panel+'-notice');notice.innerHTML=icon(linked.length?'file-text':'triangle-alert')+esc(linked.length?t('linkedCount',{count:number(linked.length)}):t(ids.size?'otherDocumentSource':'noSource'));notice.classList.toggle('no-source',!linked.length);
 const text=$(panel+'-text'),previousScroll=text.scrollTop,related=$('related-only').checked;
 const keep=new Set();doc.paragraphs.forEach((p,i)=>{if(ids.has(p.id))for(let j=Math.max(0,i-1);j<=Math.min(doc.paragraphs.length-1,i+1);j++)keep.add(j);});
 if(related&&!linked.length){text.innerHTML=`<div class="empty-source">${esc(t('noEvidenceText'))}</div><button class="secondary context-button" data-show-context>${esc(t('allText'))}</button>`;return;}
 let hidden=false;
 text.innerHTML=doc.paragraphs.map((p,i)=>{
  if(related&&!keep.has(i)){hidden=true;return '';}
  const gap=hidden?`<button class="text-button context-button" data-show-context>${esc(t('allText'))}</button>`:'';hidden=false;
  return `${gap}<div class="doc-paragraph ${ids.has(p.id)?'linked tone-'+tone(f.type):''}" data-paragraph="${esc(p.id)}"><span class="paragraph-id" title="${esc(p.id)}">${esc(p.section||p.original_id||p.id)}</span><div><span class="source-ref">${esc(t('paragraph',{section:p.section||t('noNumber'),id:p.id}))} · ${esc(p.page?t('pageNumber',{page:p.page}):t('pageUnavailable'))}</span><p class="paragraph-copy">${esc(p.text)}</p></div></div>`;
 }).join('')+(hidden?`<button class="text-button context-button" data-show-context>${esc(t('allText'))}</button>`:'');
 text.scrollTop=previousScroll;
 if(focus){const target=text.querySelector('.linked');text.scrollTop=target?Math.max(0,target.offsetTop-24):0;}
}
// Keep keyboard focus in the modal, including at the browser chrome boundary.
for(const dialog of [$('evidence'),$('settings')])dialog.addEventListener('keydown',e=>{
 if(e.key!=='Tab')return;
 const items=[...dialog.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]')].filter(el=>el.getClientRects().length);
 const first=items[0],last=items.at(-1);
 if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
 else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
});
$('evidence-close').addEventListener('click',()=>$('evidence').close());
$('evidence').addEventListener('close',()=>{
 const replacement=[...document.querySelectorAll('[data-finding]')].find(el=>el.dataset.finding===selectedId&&el.getClientRects().length);
 (evidenceOpener?.isConnected?evidenceOpener:replacement||$('finding-search')).focus({preventScroll:true});
});
for(const panel of ['left','right'])$(panel+'-document').addEventListener('change',e=>{panes[panel]=e.target.value;renderPane(panel,true);});
$('related-only').addEventListener('change',()=>renderPanes(true));
$('swap-panes').addEventListener('click',()=>{[panes.left,panes.right]=[panes.right,panes.left];renderPanes(true);});
$('review-select').addEventListener('change',e=>{const f=selectedFinding();if(!f||!reviewStatuses.includes(e.target.value))return;f.status=e.target.value;f.reviewed=true;caseWorkspace?.saveReview();renderResults();$('review-status').textContent=t('savedSession');});
$('analyst-note').addEventListener('input',e=>{const f=selectedFinding();if(f){f.note=e.target.value;caseWorkspace?.saveReview();renderConclusion();}});
for(const [id,step] of [['previous-finding',-1],['next-finding',1]])$(id).addEventListener('click',()=>{const list=navigationFindings(),index=list.findIndex(f=>f.id===selectedId);if(list[index+step]){selectedId=list[index+step].id;renderEvidence(true);}});
const resizer=$('pane-resizer');
function setSplit(value){split=Math.max(30,Math.min(70,value));$('document-panes').style.setProperty('--left-width',`calc(${split}% - 3px)`);resizer.setAttribute('aria-valuenow',String(Math.round(split)));}
resizer.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home'].includes(e.key)){e.preventDefault();setSplit(e.key==='Home'?50:split+(e.key==='ArrowLeft'?-5:5));}});
resizer.addEventListener('dblclick',()=>setSplit(50));resizer.addEventListener('pointerdown',e=>{if(e.button===0)resizer.setPointerCapture(e.pointerId);});
resizer.addEventListener('pointermove',e=>{if(resizer.hasPointerCapture(e.pointerId)){const rect=$('document-panes').getBoundingClientRect();setSplit((e.clientX-rect.left)/rect.width*100);}});
resizer.addEventListener('pointerup',e=>{if(resizer.hasPointerCapture(e.pointerId))resizer.releasePointerCapture(e.pointerId);});
function openSettings(opener){if(busy)return;$('settings-error').hidden=true;settingsOpener=opener;setNav(false);$('api-base').value=config.base;$('api-model').value=config.model;$('api-key').value=config.key;$('processing-enabled').checked=$('use-ai').checked;$('settings').showModal();}
for(const id of ['settings-open','settings-inline'])$(id).addEventListener('click',e=>openSettings(e.currentTarget));
$('settings-close').addEventListener('click',()=>$('settings').close());$('settings').addEventListener('close',()=>{if(settingsOpener?.getClientRects().length)settingsOpener.focus();else $('open-nav').focus();});
$('provider').addEventListener('change',()=>{$('api-base').value=$('provider').value==='local'?'http://127.0.0.1:11434/v1':'https://api.openai.com/v1';$('api-key').value='';});
$('settings-form').addEventListener('submit',e=>{e.preventDefault();let valid=false;try{valid=['http:','https:'].includes(new URL($('api-base').value.trim()).protocol)&&!!$('api-model').value.trim();}catch{}if(!valid){$('settings-error').hidden=false;return;}config={base:$('api-base').value.trim(),model:$('api-model').value.trim(),key:$('api-key').value.trim()};configTouched=true;$('use-ai').checked=$('processing-enabled').checked;$('settings').close();updateControls();noticeKey='modelSettingsSaved';$('run-status').textContent=t(noticeKey);});
$('use-ai').addEventListener('change',updateControls);
function downloadBlob(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}
$('download').addEventListener('click',()=>{
 if(!result)return;
 const markdown=buildReport(result,{t,date,reportLines,method,scopeText});
 downloadBlob(new Blob([markdown],{type:'text/markdown;charset=utf-8'}),`distingt-${language}.md`);noticeKey='exportDone';$('run-status').textContent=t(noticeKey);
});
function markdownFor(snapshot,locale=language){
 const tt=(key,params={})=>(dictionaries[locale][key]||key).replace(/\{(\w+)\}/g,(_,name)=>String(params[name]??''));
 const nn=value=>new Intl.NumberFormat(locale).format(value),dd=value=>new Intl.DateTimeFormat(locale,{dateStyle:'medium',timeStyle:'short'}).format(new Date(value));
 return buildReport(snapshot,{t:tt,date:dd,reportLines:()=>reportLines(snapshot,tt,nn),method:f=>method(f,tt),scopeText:f=>scopeText(f,snapshot,tt)});
}
caseWorkspace=createWorkspace({activate:(snapshot,record)=>{result=snapshot;activeTab=record.resultTab;selectedId=null;renderFilterOptions();},renderResults:tab=>{activeTab=tab;renderResults();},download:downloadBlob,markdown:markdownFor});
initPresentation();hydrateIcons();renderLocale();applyRoute();
fetch('/api/config').then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{if(!configTouched){config.base=data.base;config.model=data.model;serverHasKey=!!data.hasKey;const host=new URL(config.base).hostname;$('use-ai').checked=serverHasKey||['localhost','127.0.0.1','[::1]'].includes(host);}$('key-note').hidden=!serverHasKey;configReady=true;updateControls();}).catch(()=>{configReady=true;showError('serverUnavailable');});
