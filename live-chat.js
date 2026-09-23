import {t} from './i18n.js';
import {api} from './research-client.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const activeStates=new Set(['queued','preparing','answering']);
export function createLiveChat(root,getConfig,openSettings=()=>{}){
 let snapshot=null,history=null,timer=null,generation=0,loading=false,sending=false,findingIds=[],draft='',error='',pending=null;
 let sourceOpener=null;
 const draftKey=()=>snapshot?.analysis_id?'ayqyn.chatDraft.'+snapshot.analysis_id:null;
 function saveDraft(){try{if(draftKey())sessionStorage.setItem(draftKey(),draft);}catch{}}
 const dialog=document.createElement('dialog');dialog.className='settings-dialog live-source';dialog.setAttribute('aria-label',t('sources'));document.body.append(dialog);
 const endpoint=()=>`/api/analyses/${encodeURIComponent(snapshot.analysis_id)}`;
 const tx=k=>esc(t(k));
 const canSend=()=>snapshot?.analysis_id&&history&&!history.active_turn&&!sending&&!loading&&!pending;
 function messageMarkup(message){
  if(message.role==='user')return `<article class="live-message user-message"><strong>${tx('you')}</strong><p>${esc(message.text||'')}</p></article>`;
  if(message.role==='error'||message.error)return `<article class="live-message"><p class="file-error">${esc(message.error?.message||message.text||'')}</p></article>`;
  return `<article class="live-message"><strong>${tx('chatAnswer')}</strong><p class="helper">${esc(t('chatOutcome_'+message.outcome))}</p>${(message.blocks||[]).map(b=>`<div class="live-block"><span class="quiet-badge">${esc(t('chatBasis_'+b.basis))}</span><p>${esc(b.text)}</p>${(b.citation_ids||[]).map(id=>{const c=(message.citations||[]).find(c=>c.id===id);return c?`<button type="button" class="citation-card" data-live-source="${esc(c.fragment_id)}"><span>${esc(c.document_name)} · ${esc(t(c.side+'Short'))} · ${esc(c.page?t('pageNumber',{page:c.page}):t('pageUnavailable'))} · § ${esc(c.section||c.fragment_id)}</span><blockquote>${esc(c.quote)}</blockquote></button>`:'';}).join('')}</div>`).join('')}${(message.limitations||[]).map(l=>`<p class="message-notice">${esc(l)}</p>`).join('')}</article>`;
 }
 function render(){
  if(!snapshot||snapshot.mode==='demo'){root.hidden=true;return;}
  root.hidden=false;
  root.setAttribute('aria-label',t('chatTitle'));
  const active=history?.active_turn;
  root.innerHTML=`<div class="live-chat-heading"><h2>${tx('chatTitle')}</h2><button type="button" class="text-button" data-live-settings>${tx('settings')}</button><button type="button" class="text-button" data-live-refresh>${tx('chatRefresh')}</button></div><p class="helper">${tx('chatSnapshotNote')}</p>${!snapshot.analysis_id?`<p class="notice">${tx('chatNoSnapshot')}</p>`:`<div class="live-history">${(history?.messages||[]).map(messageMarkup).join('')}</div><p role="status" aria-live="polite">${loading?tx('chatLoading'):active?esc(t('chatStatus_'+active.status)):''}</p>${error?`<p class="file-error" role="alert">${esc(error)}</p>`:''}<form data-live-form><div class="live-context">${findingIds.map(id=>`<span class="context-chip">${esc(snapshot.findings.find(f=>f.id===id)?.title||id)}<button type="button" class="text-button" data-live-remove="${esc(id)}" aria-label="${tx('removeContext')}">×</button></span>`).join('')}</div><label for="live-chat-input">${tx('chatQuestion')}</label><textarea id="live-chat-input" rows="3" maxlength="4000" ${sending?'disabled':''}>${esc(draft)}</textarea><div class="live-chat-actions"><button class="primary" type="submit" ${!canSend()||!draft.trim()?'disabled':''}>${tx('chatSend')}</button>${pending?`<button type="button" class="secondary" data-live-retry>${tx('chatRetryRequest')}</button>`:''}</div><p class="helper">${tx('chatProviderNote')}</p></form>`}`;
 }
 async function refresh(){
  if(!snapshot?.analysis_id||snapshot.mode==='demo')return;
  const token=generation,path=endpoint();clearTimeout(timer);loading=true;render();
  try{const data=await api(path+'/chat');if(token!==generation)return;history=data;error='';
   if(pending&&data.messages.some(m=>m.client_message_id===pending.client_message_id||m.id===pending.client_message_id)){pending=null;draft='';}
  }catch(e){if(token===generation)error=e.status===404?t('chatMissing'):e.message;}
  finally{if(token===generation){loading=false;render();if(history?.active_turn)timer=setTimeout(poll,1500);}}
 }
 async function poll(){
  const token=generation,id=history?.active_turn?.turn_id;if(!id)return;
  try{const turn=await api(endpoint()+'/chat/turns/'+encodeURIComponent(id));if(token!==generation)return;
   if(activeStates.has(turn.status)){history.active_turn=turn;render();timer=setTimeout(poll,1500);}else await refresh();
  }catch(e){if(token===generation){error=t('chatDisconnected');render();}}
 }
 async function send(retry=false){
  if(sending||(!retry&&!canSend()))return;
  const token=generation,path=endpoint();
  // Keep this exact request in memory for a safe retry after an uncertain response.
  if(!retry)pending={client_message_id:crypto.randomUUID(),expected_version:history.conversation_version,text:draft.trim(),finding_ids:[...findingIds],config:{...getConfig(),reasoning_effort:'none'}};
  if(!pending)return;
  sending=true;error='';render();
  try{await api(path+'/chat/messages',pending,45000);if(token!==generation)return;pending=null;draft='';saveDraft();findingIds=[];await refresh();}
  catch(e){if(token!==generation)return;if(e.status){pending=null;error=e.message;if(e.status===409){await refresh();error=t('chatConflict');}}else error=t('chatDisconnected');}
  finally{if(token===generation){sending=false;render();}}
 }
 root.addEventListener('input',e=>{if(e.target.id==='live-chat-input'){draft=e.target.value;saveDraft();const button=root.querySelector('button[type=submit]');button.disabled=!canSend()||!draft.trim();}});
 root.addEventListener('submit',e=>{e.preventDefault();send();});
 root.addEventListener('keydown',e=>{if(e.target.id==='live-chat-input'&&e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();if(draft.trim())send();}});
 root.addEventListener('click',async e=>{
  const button=e.target.closest('button');if(!button)return;
  if(button.hasAttribute('data-live-settings')){openSettings(button);return;}
  if(button.hasAttribute('data-live-refresh')){await refresh();return;}
  if(button.hasAttribute('data-live-retry')){send(true);return;}
  if(button.dataset.liveRemove){findingIds=findingIds.filter(id=>id!==button.dataset.liveRemove);render();return;}
  if(button.dataset.liveSource){
   const token=generation;sourceOpener=button;dialog.innerHTML=`<button class="secondary" data-live-close>${tx('close')}</button><p>${tx('chatLoading')}</p>`;dialog.showModal();
   try{const data=await api(endpoint()+'/source?fragment_id='+encodeURIComponent(button.dataset.liveSource));if(token!==generation||!dialog.open)return;
    const fragment=data.fragment;dialog.innerHTML=`<button class="secondary" data-live-close>${tx('close')}</button><h2>${esc(data.document.name)}</h2><p>${esc(fragment.page?t('pageNumber',{page:fragment.page}):t('pageUnavailable'))} · § ${esc(fragment.section||fragment.id)}</p><blockquote>${esc(fragment.text)}</blockquote><p class="helper">SHA-256 ${esc(data.document.sha256)}</p><details><summary>${tx('surroundingContext')}</summary><pre>${esc((data.context?.fragments||[]).map(p=>p.text).join('\n\n'))}</pre>${data.context?.truncated?`<p class="notice">${tx('chatContextPartial')}</p>`:''}</details>`;
    dialog.querySelector('[data-live-close]')?.focus();
   }catch(err){dialog.innerHTML=`<button class="secondary" data-live-close>${tx('close')}</button><p role="alert">${esc(err.message)}</p>`;}
  }
 });
 dialog.addEventListener('click',e=>{if(e.target.closest('[data-live-close]'))dialog.close();});dialog.addEventListener('close',()=>sourceOpener?.isConnected&&sourceOpener.focus());
 return {set(value){if(snapshot?.analysis_id===value?.analysis_id&&snapshot===value){render();return;}saveDraft();generation++;clearTimeout(timer);if(dialog.open)dialog.close();snapshot=value;history=null;loading=false;sending=false;findingIds=[];draft='';try{draft=sessionStorage.getItem(draftKey())||'';}catch{}error='';pending=null;render();refresh();},locale:render,
  discuss(id){if(!snapshot||!snapshot.findings.some(f=>f.id===id))return;if(!findingIds.includes(id))findingIds=[...findingIds,id].slice(-5);render();root.scrollIntoView({behavior:'smooth',block:'start'});root.querySelector('textarea')?.focus({preventScroll:true});},
  askFragment(doc,fragment){draft=t('chatAskFragment',{name:doc.name,quote:fragment.text}).slice(0,4000);saveDraft();render();root.scrollIntoView({block:'start'});root.querySelector('textarea')?.focus({preventScroll:true});},
  deactivate(){generation++;clearTimeout(timer);if(dialog.open)dialog.close();}}
}
