import {t,number,language,dictionaries} from './i18n.js';
import {icon} from './icons.js';
import {listCases,getCase,saveCase} from './case-store.js';
import {makeCase,resolveRef,beginRun,applyEvent,interruptUnfinished,terminal,markArtifactsOutdated,artifactMarkdown} from './agent-model.js';
import {executeDemo} from './demo-agent.js';
const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tx=(key,params)=>esc(t(key,params));
const uid=()=>crypto.randomUUID();
export function createWorkspace(hooks){
 let sourceOpenerId=null;
 let active=null,records=[],loaded=false,storageFailed=false,sourceOpener=null,controller=null,activeRunCase=null,queue=Promise.resolve(),routeToken=0;const persistTimers=new Map();
 const media=matchMedia('(max-width: 900px)');
 function fitChat(){if(!active||active.view!=='agent'||$('case-workspace').hidden)return;requestAnimationFrame(()=>{const layout=document.querySelector('.agent-layout'),height=window.visualViewport?.height||innerHeight;layout.style.setProperty('--agent-space',Math.max(260,height-layout.getBoundingClientRect().top-18)+'px');});}
 window.addEventListener('resize',fitChat);window.visualViewport?.addEventListener('resize',fitChat);document.fonts?.addEventListener('loadingdone',fitChat);
 const ready=listCases().then(items=>{records=items;loaded=true;renderList();}).catch(()=>{storageFailed=true;loaded=true;renderList();});
 function warn(key){$('case-warning').hidden=!key;$('case-warning').textContent=key?t(key):'';}
 function persist(record=active){
  if(!record)return Promise.resolve();
  // Serialize writes so local revisions remain monotonic, including rapid draft edits.
  queue=queue.catch(()=>{}).then(async()=>{if(storageFailed)throw Error('storageUnavailable');await saveCase(record);const i=records.findIndex(c=>c.id===record.id);if(i<0)records.unshift(record);else records[i]=record;}).catch(error=>{warn(error.message==='caseConflict'?'caseConflict':'storageUnavailable');throw error;});
  return queue;
 }
 function saveSoon(debounce=false){const record=active;if(!record)return;if(!debounce){persist(record).catch(()=>{});return;}clearTimeout(persistTimers.get(record.id));persistTimers.set(record.id,setTimeout(()=>{persistTimers.delete(record.id);persist(record).catch(()=>{});},150));}
 function name(record){return record.name||(record.kind==='demo'?t('demoCaseName'):t('caseDefault'));}
 function casePath(id){return '/app/cases/'+encodeURIComponent(id);}
 function renderList(){
  const list=records.slice().sort((a,b)=>b.createdAt.localeCompare(a.createdAt));
  $('case-shortcuts').innerHTML=list.slice(0,6).map(c=>`<a href="#${casePath(c.id)}" class="case-shortcut ${c.id===active?.id?'active':''}">${icon(c.kind==='demo'?'monitor':'file-text')}<span>${esc(name(c))}</span></a>`).join('');
  $('cases-view').innerHTML=`<div class="page-heading"><div><p class="eyebrow">DISTINGT / FREAX</p><h1>${tx('cases')}</h1><p class="helper">${tx('localCaseStorage')}</p></div><a class="primary" href="#/app/new">${icon('plus')}${tx('newAnalysis')}</a></div>${storageFailed?`<p class="notice">${tx('storageUnavailable')}</p>`:''}<div class="case-list">${list.map(c=>`<a href="#${casePath(c.id)}" class="case-list-item surface"><span class="case-list-icon">${icon(c.kind==='demo'?'monitor':'files')}</span><div><span class="eyebrow">${tx(c.kind==='demo'?'demoLabel':'savedAnalysis')} · V${c.analysisVersion}</span><h2>${esc(name(c))}</h2><p>${tx('caseSummary',{documents:c.snapshot.documents.length,findings:c.snapshot.findings.length})}</p></div>${icon('arrow-right')}</a>`).join('')||`<div class="workspace-empty surface"><h2>${tx('noCases')}</h2><p>${tx('emptyWorkspaceText')}</p><a class="secondary" href="#/app/demo">${tx('viewExample')}</a></div>`}</div>`;
 }
 async function create(snapshot,files=[],title='',id){
  await ready;
  if(id){const existing=records.find(c=>c.id===id)||await getCase(id).catch(()=>null);if(existing)return existing;}
  const record=makeCase(structuredClone(snapshot),files.map(item=>({...item})),title,id);
  records.unshift(record);await persist(record).catch(()=>{});renderList();return record;
 }
 async function open(id,tab){
  const token=++routeToken;await ready;await queue.catch(()=>{});
  const record=activeRunCase===id?records.find(c=>c.id===id):(await getCase(id).catch(()=>null)||records.find(c=>c.id===id));
  if(token!==routeToken)return false;
  if(!record){$('cases-view').innerHTML=`<div class="workspace-empty surface"><h1>${tx('caseMissing')}</h1><p>${tx('caseMissingText')}</p><a class="secondary" href="#/app/cases">${tx('cases')}</a></div>`;return false;}
  if(active&&active.id!==id)closeSource(false);
  active=record;const recordIndex=records.findIndex(c=>c.id===id);if(recordIndex>=0)records[recordIndex]=record;try{const draft=sessionStorage.getItem('distingt.draft.'+id);if(draft!==null)active.draft=draft;}catch{}
  // A reload never automatically resumes a fixture operation or sends a message again.
  if(activeRunCase!==record.id&&interruptUnfinished(record))await persist(record).catch(()=>{});
  hooks.activate(record.snapshot,record);
  if(tab)record.view=tab;
  render();renderList();
  if(record.source&&record.view==='agent')openSource(record.source,null,false);
  return true;
 }
 function showTab(tab){if(!active)return;active.view=tab;render();saveSoon();}
 function render(){
  if(!active)return;
  $('case-title').textContent=name(active);$('page-title').textContent=t('cases');
  $('case-meta').textContent=`${t(active.kind==='demo'?'demoLabel':'savedAnalysis')} · ${t('analysisVersion',{version:active.analysisVersion})} · ${t(active.snapshot.mode==='fallback'?'partial':'complete')}`;
  $('case-storage').textContent=t('localCaseStorage');
  const view=active.view;
  document.querySelectorAll('[data-case-tab]').forEach(el=>{const selected=el.dataset.caseTab===view;el.setAttribute('aria-selected',String(selected));el.tabIndex=selected?0:-1;});
  $('agent-view').hidden=view!=='agent';$('case-documents').hidden=view!=='documents';$('results').hidden=!['results','report'].includes(view);$('case-artifacts').hidden=view!=='report';
  $('case-workspace').classList.toggle('agent-active',view==='agent');
  if(view!=='agent'&&$('chat-source').open)closeSource(false);
  if(view==='results'||view==='report')hooks.renderResults(view==='report'?'report':active.resultTab);
  renderChat();renderDocuments();renderArtifacts();fitChat();
  if(storageFailed)warn('storageUnavailable');
 }
 function contextLabel(ref){try{const obj=resolveRef(active,ref);return ref.type==='finding'?`${t('riskContext')} ${obj.id}`:`${t(obj.doc.side+'Short')} · ${obj.doc.name} · § ${obj.fragment.section||obj.fragment.id}`;}catch{return t('staleContext');}}
 function addContext(ref,opener){if(!active)return;try{resolveRef(active,ref);}catch{warn('staleContext');return;}if(!active.contextRefs.some(x=>x.type===ref.type&&x.id===ref.id))active.contextRefs.push(ref);if(ref.type==='finding')active.operation='recheck';active.view='agent';render();saveSoon();$('agent-input').focus();}
 function refFor(id){const doc=active.snapshot.documents.find(d=>d.paragraphs.some(p=>p.id===id));return doc?{type:'fragment',id,documentId:doc.id,versionId:active.analysisVersionId}:null;}
 function summaryMarkup(){
  const s=active.snapshot,riskTypes=['function_loss','duplication','conflict','contradiction'],risks=s.findings.filter(f=>riskTypes.includes(f.type));
  return `<p class="message-eyebrow">${tx('savedSummary')} · V${active.analysisVersion}</p><h2>${tx('agentWelcome')}</h2><p>${tx('summaryCounts',{documents:number(s.documents.length),findings:number(s.findings.length),risks:number(risks.length)})}</p><p class="helper">${tx(risks.length?'summaryCaution':'noRisksScoped')}</p>${s.mode==='fallback'?`<p class="notice">${tx('partialAgent')}</p>`:''}<div class="summary-actions">${risks.slice(0,3).map(f=>`<button class="suggestion" data-quick-finding="${esc(f.id)}">${icon(f.type==='duplication'?'git-compare-arrows':'search')}<span>${esc(t(f.type))}</span>${icon('arrow-right')}</button>`).join('')}<button class="suggestion" data-quick-draft>${icon('file-text')}<span>${tx('draftConclusion')}</span>${icon('arrow-right')}</button></div>`;
 }
 function partMarkup(part){
  if(part.type==='summary')return summaryMarkup();
  if(part.type==='text')return `<p class="message-text">${esc(part.text)}</p>`;
  if(part.type==='notice')return `<p class="message-notice">${tx(part.key)}</p>`;
  if(part.type==='tool')return `<details class="tool-card tool-${esc(part.status)}"><summary>${icon(part.status==='completed'?'check':part.status==='failed'?'triangle-alert':part.status==='cancelled'?'x':'loader-circle')}<span>${tx(part.name||'toolAction')}</span><span class="tool-status">${tx('tool_'+part.status)}</span></summary><div><p>${tx('localDemoExecution')}</p>${part.scope?`<p class="helper">${tx('documents')}: ${part.scope.map(id=>esc(active.snapshot.documents.find(d=>d.id===id)?.name||id)).join('; ')}</p>`:''}${part.count!==undefined?`<p>${tx('toolItems',{count:part.count})}</p>`:''}${part.errorKey?`<p>${tx(part.errorKey)}</p>`:''}</div></details>`;
  if(part.type==='citation'){
   try{const {doc,fragment}=resolveRef(active,part.ref);return `<button class="citation-card" data-chat-source="${esc(fragment.id)}"><span class="citation-meta">${icon('file-text')}<span>${esc(t(doc.side+'Short'))} · ${esc(doc.name)}<small>V${active.analysisVersion} · ${esc(fragment.page?t('pageNumber',{page:fragment.page}):t('pageUnavailable'))} · § ${esc(fragment.section||fragment.id)}</small></span>${icon('external-link')}</span><blockquote lang="ru">${esc(fragment.text)}</blockquote></button>`;}catch{return `<p class="notice">${tx('sourceUnavailable')}</p>`;}
  }
  if(part.type==='finding'){const f=active.snapshot.findings.find(f=>f.id===part.id);return f?`<div class="comparison-part"><p class="eyebrow">${tx('preliminary')} · ${esc(f.id)}</p><p>${esc(f.explanation)}</p>${part.common?`<p class="helper">${tx('commonWording')}</p><blockquote>${esc(part.common)}</blockquote>`:''}<button class="text-button" data-finding="${esc(f.id)}">${tx('showSources')}${icon('external-link')}</button></div>`:'';}
  if(part.type==='artifact'){const a=active.artifacts.find(a=>a.id===part.id);return a?artifactMarkup(a):`<p>${tx('artifactMissing')}</p>`;}
  return '';
 }
 function artifactMarkup(a){return `<div class="artifact-card">${icon('file-text')}<div><strong>${tx('report')} · V${a.version}</strong><p>${tx(a.status==='outdated'?'artifactOutdated':'artifactReady')} · Markdown · ${esc(a.locale.toUpperCase())}</p><small>${tx('analysisVersion',{version:active.analysisVersion})} · ${tx(active.kind==='demo'?'demoLabel':'savedAnalysis')}</small><details class="artifact-preview"><summary>${tx('previewArtifact')}</summary><pre>${esc(a.content)}</pre></details></div><button class="secondary" data-artifact-download="${esc(a.id)}">${icon('download')}${tx('downloadVersion',{version:a.version})}</button></div>`;}
 function renderChat(newContent=false){
  if(!active)return;
  const scroller=$('chat-messages'),nearBottom=scroller.scrollHeight-scroller.clientHeight-scroller.scrollTop<90,scroll=scroller.scrollTop;
  $('agent-mode-note').innerHTML=icon('info')+`<span>${tx(active.kind==='demo'?'demoAgentDisclosure':'agentUnavailable')}</span>`+(active.kind==='demo'?'':`<a href="#/app/demo">${tx('openDemoAgent')}</a>`);
  scroller.innerHTML=active.conversation.messages.map(m=>`<article class="chat-message ${m.role==='user'?'user-message':'assistant-message'}"><div class="message-author">${m.role==='user'?tx('you'):`<img src="distingt-assets/mark.svg" alt="" width="23" height="23"> Distingt`}<span>${m.role==='user'?tx('userClarification'):tx(active.kind==='demo'?'demoAdapter':'savedSummary')}</span></div><div class="message-parts">${m.role==='user'&&m.contextRefs?.length?`<div class="message-context">${m.contextRefs.map(ref=>`<span>${esc(contextLabel(ref))} · V${active.analysisVersion}</span>`).join('')}</div>`:''}${m.parts.map(partMarkup).join('')}${['failed','interrupted','cancelled'].includes(m.status)?`<div class="run-end"><p>${tx('run_'+m.status)}</p><button class="text-button" data-retry-run="${esc(m.id)}">${tx('retryOperation')}</button></div>`:''}</div></article>`).join('');
  scroller.scrollTop=nearBottom?scroller.scrollHeight:scroll;
  if(newContent&&!nearBottom)$('new-answer').hidden=false;
  renderComposer();
 }
 function renderComposer(){
  if(!active)return;
  if($('agent-input').value!==active.draft)$('agent-input').value=active.draft;$('agent-operation').value=active.operation;
  $('context-chips').innerHTML=active.contextRefs.map((ref,i)=>`<span class="context-chip">${icon('file-text')}<span>${esc(contextLabel(ref))}</span><button type="button" class="icon-button" data-remove-context="${i}" aria-label="${tx('removeContext')}">${icon('x')}</button></span>`).join('');
  const run=active.conversation.runs.find(r=>!terminal.has(r.status));
  $('agent-send').disabled=active.kind!=='demo'||!!run||!active.draft.trim();$('agent-send').title=active.kind==='demo'?'':t('agentUnavailable');
  $('agent-send').disabled ||=!!controller;
  $('agent-stop').hidden=!run||activeRunCase!==active.id;$('agent-stop').disabled=run?.status==='cancel_requested';
  $('agent-stop').querySelector('[data-i18n]').textContent=t(run?.status==='cancel_requested'?'stopping':'stop');
  $('composer-hint').textContent=t(active.kind==='demo'?'demoComposerHint':'liveComposerHint');
  $('agent-operation').disabled=active.kind!=='demo';
 }
 function renderDocuments(){
  if(!active)return;
  $('case-documents').innerHTML=`<div class="case-doc-header"><h2>${tx('documents')}</h2><p>${tx('documentsContext')}</p><p class="helper">${tx('documentEditingUnavailable')}</p></div><div class="case-document-sets">${['before','after'].map(side=>`<section><p class="eyebrow">${esc(t(side))}</p>${active.snapshot.documents.filter(d=>d.side===side).map(doc=>`<details class="case-document"><summary>${icon('file-text')}<span>${esc(doc.name)}<small>${tx('paragraphCount',{count:doc.paragraphs.length})} · V${active.analysisVersion}</small></span></summary><div>${doc.paragraphs.map(p=>`<article><span class="mono">§ ${esc(p.section||p.id)}</span><p>${esc(p.text)}</p><div><button class="text-button" data-chat-source="${esc(p.id)}">${tx('showSources')}</button><button class="text-button" data-ask-fragment="${esc(p.id)}">${tx('askFragment')}</button></div></article>`).join('')}</div></details>`).join('')}</section>`).join('')}</div>`;
 }
 function renderArtifacts(){if(!active)return;$('case-artifacts').innerHTML=active.artifacts.length?`<h2>${tx('artifactVersions')}</h2>${active.artifacts.slice().reverse().map(artifactMarkup).join('')}`:'';}
 async function send({text=active?.draft,refs=active?.contextRefs,operation=active?.operation,clientMessageId=uid()}={}){
  if(!active||active.kind!=='demo')return;if(controller){warn('runActive');return;}
  const record=active;let started;
  try{started=beginRun(record,{clientMessageId,text,contextRefs:refs,operation,locale:language});}catch(error){warn(error.message);return;}
  if(started.duplicate)return;
  const {run}=started;controller=new AbortController();activeRunCase=record.id;record.draft='';try{sessionStorage.setItem('distingt.draft.'+record.id,'');}catch{}record.contextRefs=[];renderChat();
  try{await persist(record);}catch{run.status='failed';record.conversation.messages.find(m=>m.id===run.id).status='failed';controller=null;activeRunCase=null;renderChat();return;}
  async function emit(type,payload){
   const event={eventId:uid(),sequence:record.conversation.sequence+1,conversationId:record.conversation.id,analysisVersionId:record.analysisVersionId,runId:run.id,type,payload};
   applyEvent(record,event);await persist(record);if(active?.id===record.id){renderChat(true);if(type==='run-status'&&terminal.has(payload.status))$('agent-announcement').textContent=t('run_'+payload.status);}
  }
  const artifactCount=record.artifacts.length;
  try{await executeDemo(record,run,{emit,signal:controller.signal,buildMarkdown:s=>artifactMarkdown(record,hooks.markdown(s,run.locale),dictionaries[run.locale])});}
  catch{run.status='failed';record.conversation.messages.find(m=>m.id===run.id).status='failed';record.artifacts.splice(artifactCount);warn('storageUnavailable');}
  finally{controller=null;activeRunCase=null;if(active?.id===record.id){renderChat();renderArtifacts();}else notify(record.id,'answerReady');}
 }
 function notify(id,key='analysisReady'){$('analysis-ready').hidden=false;$('analysis-ready').innerHTML=`${icon('circle-check')}<a href="#${casePath(id)}">${tx(key)}</a><button class="icon-button" data-dismiss-ready aria-label="${tx('close')}">${icon('x')}</button>`;}
 function sourceMarkup(ref){const {doc,fragment}=resolveRef(active,ref),index=doc.paragraphs.indexOf(fragment);return `<p class="source-version">${tx(active.kind==='demo'?'demoLabel':'savedAnalysis')} · V${active.analysisVersion} · ${esc(t(doc.side+'Short'))}</p><p class="helper">${esc(fragment.page?t('pageNumber',{page:fragment.page}):t('pageUnavailable'))} · § ${esc(fragment.section||fragment.id)}</p><p class="source-exact-label">${tx('originalQuote')}</p><blockquote class="exact-quote" data-source-fragment="${esc(fragment.id)}">${esc(fragment.text)}</blockquote><details class="source-neighbors"><summary>${tx('surroundingContext')}</summary>${doc.paragraphs.slice(Math.max(0,index-1),index+2).filter(p=>p.id!==fragment.id).map(p=>`<p><span class="mono">§ ${esc(p.section||p.id)}</span>${esc(p.text)}</p>`).join('')}</details><p class="source-id mono">${esc(fragment.id)}</p>`;}
 function openSource(ref,opener,save=true){
  if(!active)return;try{const {doc}=resolveRef(active,ref);sourceOpener=opener||sourceOpener;sourceOpenerId=opener?.dataset.chatSource||sourceOpenerId;active.source=ref;active.view='agent';render();$('chat-source-title').textContent=doc.name;$('chat-source-body').innerHTML=sourceMarkup(ref);const dialog=$('chat-source');if(!dialog.open){if(media.matches)dialog.showModal();else dialog.show();}dialog.classList.remove('expanded');$('chat-source-expand').setAttribute('aria-label',t('expandSource'));$('chat-source-body').scrollTop=0;$('chat-source-close').focus();if(save)saveSoon();}catch{warn('sourceUnavailable');}
 }
 function closeSource(clear=true){const dialog=$('chat-source');if(dialog.open)dialog.close();if(clear&&active){active.source=null;saveSoon();}const target=sourceOpener?.isConnected?sourceOpener:[...document.querySelectorAll('[data-chat-source]')].find(el=>el.dataset.chatSource===sourceOpenerId&&el.getClientRects().length);target?.focus({preventScroll:true});}
 $('chat-source-expand').addEventListener('click',()=>{const expanded=$('chat-source').classList.toggle('expanded');$('chat-source-expand').setAttribute('aria-label',t(expanded?'restoreChat':'expandSource'));});
 $('chat-source-close').addEventListener('click',()=>closeSource());
 $('chat-source').addEventListener('cancel',e=>{e.preventDefault();closeSource();});
 $('chat-source').addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();closeSource();}if(e.key==='Tab'&&media.matches){const items=[...$('chat-source').querySelectorAll('button,summary,a[href]')].filter(el=>el.getClientRects().length&&!el.disabled);if(e.shiftKey&&document.activeElement===items[0]){e.preventDefault();items.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===items.at(-1)){e.preventDefault();items[0].focus();}}});
 media.addEventListener('change',()=>{if($('chat-source').open&&active?.source){const ref=active.source;$('chat-source').close();openSource(ref,null,false);}});
 $('chat-source-ask').addEventListener('click',()=>{const ref=active?.source;if(!ref)return;closeSource();addContext(ref);});
 $('chat-source-original').addEventListener('click',()=>{if(!active?.source)return;const {doc}=resolveRef(active,active.source),index=active.snapshot.documents.indexOf(doc);if(doc.original_url){const a=document.createElement('a');a.href=doc.original_url;a.download=doc.id+'.pdf';a.click();}else{const file=active.files[index]?.file;if(file)hooks.download(file,file.name);else warn('originalUnavailable');}});
 $('composer').addEventListener('submit',e=>{e.preventDefault();send();});
 $('agent-input').addEventListener('input',e=>{if(active){active.draft=e.target.value;try{sessionStorage.setItem('distingt.draft.'+active.id,active.draft);}catch{}saveSoon(true);renderComposer();}});
 $('agent-input').addEventListener('focus',fitChat);$('agent-input').addEventListener('blur',fitChat);
 $('agent-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){e.preventDefault();if(!$('agent-send').disabled)send();}});
 $('agent-operation').addEventListener('change',e=>{if(active){active.operation=e.target.value;saveSoon();}});
 $('agent-stop').addEventListener('click',async()=>{if(!controller||activeRunCase!==active?.id)return;const run=active.conversation.runs.find(r=>!terminal.has(r.status));if(run){run.status='cancel_requested';renderComposer();const currentController=controller;await persist().catch(()=>{});currentController?.abort();}});
 $('chat-messages').addEventListener('scroll',()=>{const el=$('chat-messages');if(el.scrollHeight-el.clientHeight-el.scrollTop<80)$('new-answer').hidden=true;});
 $('new-answer').addEventListener('click',()=>{$('chat-messages').scrollTop=$('chat-messages').scrollHeight;$('new-answer').hidden=true;});
 document.querySelectorAll('[data-case-tab]').forEach(el=>{el.addEventListener('click',()=>showTab(el.dataset.caseTab));el.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const tabs=[...document.querySelectorAll('[data-case-tab]')],i=tabs.indexOf(el),next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;showTab(tabs[next].dataset.caseTab);tabs[next].focus();});});
 document.addEventListener('click',e=>{
  const el=e.target.closest('[data-discuss],[data-ask-fragment],[data-chat-source],[data-remove-context],[data-quick-finding],[data-quick-draft],[data-artifact-download],[data-retry-run],[data-dismiss-ready]');if(!el)return;
  if(el.hasAttribute('data-dismiss-ready')){$('analysis-ready').hidden=true;return;}if(!active)return;
  if(el.dataset.discuss){addContext({type:'finding',id:el.dataset.discuss,versionId:active.analysisVersionId},el);return;}
  if(el.dataset.askFragment){const ref=refFor(el.dataset.askFragment);if(ref)addContext(ref,el);return;}
  if(el.dataset.chatSource){const ref=refFor(el.dataset.chatSource);if(ref)openSource(ref,el);else warn('sourceUnavailable');return;}
  if(el.dataset.removeContext!==undefined){active.contextRefs.splice(Number(el.dataset.removeContext),1);renderComposer();saveSoon();return;}
  if(el.dataset.quickFinding){const f=active.snapshot.findings.find(f=>f.id===el.dataset.quickFinding);active.draft=t('questionFinding',{type:t(f.type)});addContext({type:'finding',id:f.id,versionId:active.analysisVersionId});return;}
  if(el.hasAttribute('data-quick-draft')){active.draft=t('draftQuestion');active.operation='draft';active.contextRefs=[];renderComposer();saveSoon();$('agent-input').focus();return;}
  if(el.dataset.artifactDownload){const a=active.artifacts.find(a=>a.id===el.dataset.artifactDownload);if(a)hooks.download(new Blob([a.content],{type:'text/markdown;charset=utf-8'}),`distingt-${active.kind==='demo'?'DEMO-C010':'case'}-conclusion-v${a.version}-${a.locale}.md`);return;}
  if(el.dataset.retryRun){const run=active.conversation.runs.find(r=>r.id===el.dataset.retryRun);if(run&&terminal.has(run.status)){active.draft=run.text;active.contextRefs=run.contextRefs;active.operation=run.operation;renderComposer();saveSoon();$('agent-input').focus();}}
 });
 $('case-export').addEventListener('click',()=>{if(active)hooks.download(new Blob([hooks.markdown(active.snapshot)],{type:'text/markdown;charset=utf-8'}),`distingt-${active.kind==='demo'?'DEMO-C010':'case'}-analysis-v${active.analysisVersion}-${language}.md`);});
 $('collapse-sidebar').addEventListener('click',()=>{document.body.classList.toggle('nav-collapsed');$('collapse-sidebar').setAttribute('aria-expanded',String(!document.body.classList.contains('nav-collapsed')));});
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&active)persist().catch(()=>{});});
 return {ready,create,open,casePath,notify,deactivate(){closeSource(false);},render,renderList,get active(){return active;},get records(){return records;},showTab,addFinding(id){if(active)addContext({type:'finding',id,versionId:active.analysisVersionId});},saveReview(){if(active){markArtifactsOutdated(active);persist().catch(()=>{});renderArtifacts();renderChat();}},saveResultTab(tab){if(active){active.resultTab=tab;saveSoon();}},locale(){renderList();if(active){render();if(active.source&&$('chat-source').open){$('chat-source-title').textContent=resolveRef(active,active.source).doc.name;$('chat-source-body').innerHTML=sourceMarkup(active.source);}}}};
}
