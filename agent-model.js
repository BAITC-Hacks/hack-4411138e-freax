// Pure state transitions shared by the clearly labeled demo and a future server adapter.
export const terminal=new Set(['completed','failed','cancelled','interrupted']);
export function makeCase(snapshot,files=[],name='',id=crypto.randomUUID()){
 const versionId=id+':analysis:1';
 return {id,name,kind:snapshot.mode==='demo'?'demo':'analysis',createdAt:new Date().toISOString(),revision:0,analysisVersionId:versionId,analysisVersion:1,snapshot,files,view:'agent',resultTab:'overview',draft:'',contextRefs:[],operation:'search',source:null,artifacts:[],conversation:{id:id+':conversation:1',messages:[{id:id+':summary',role:'assistant',status:'completed',parts:[{type:'summary'}],analysisVersionId:versionId}],runs:[],events:[],sequence:0}};
}
export function resolveRef(record,ref){
 if(ref.versionId!==record.analysisVersionId)throw Error('staleContext');
 if(ref.type==='finding'){const f=record.snapshot.findings.find(f=>f.id===ref.id);if(!f)throw Error('sourceUnavailable');return f;}
 const doc=record.snapshot.documents.find(d=>d.id===ref.documentId);
 const fragment=doc?.paragraphs.find(p=>p.id===ref.id);
 if(!doc||!fragment)throw Error('sourceUnavailable');return {doc,fragment};
}
export function beginRun(record,{clientMessageId,text,contextRefs,operation,locale}){
 const c=record.conversation;
 const old=c.runs.find(r=>r.clientMessageId===clientMessageId);if(old)return {run:old,duplicate:true};
 if(c.runs.some(r=>!terminal.has(r.status)))throw Error('runActive');
 contextRefs.forEach(ref=>resolveRef(record,ref));
 if(!text.trim())throw Error('emptyMessage');
 const run={id:crypto.randomUUID(),clientMessageId,status:'queued',operation,locale,contextRefs:structuredClone(contextRefs),text:text.trim(),analysisVersionId:record.analysisVersionId};
 c.runs.push(run);c.messages.push({id:clientMessageId,role:'user',status:'completed',locale,contextRefs:run.contextRefs,analysisVersionId:record.analysisVersionId,parts:[{type:'text',text:run.text}]},{id:run.id,role:'assistant',status:'in_progress',locale,analysisVersionId:record.analysisVersionId,parts:[]});return {run,duplicate:false};
}
export function applyEvent(record,event){
 const c=record.conversation;
 if(event.conversationId!==c.id||event.analysisVersionId!==record.analysisVersionId)throw Error('staleContext');
 if(c.events.some(e=>e.eventId===event.eventId)||event.sequence<=c.sequence)return false;
 if(event.sequence!==c.sequence+1)throw Error('eventGap');
 const run=c.runs.find(r=>r.id===event.runId),message=c.messages.find(m=>m.id===event.runId);if(!run||!message)throw Error('sourceUnavailable');
 if(terminal.has(run.status))return false;
 const {type,payload}=event;
 if(type==='run-status'){if(terminal.has(run.status))return false;run.status=payload.status;message.status=terminal.has(payload.status)?payload.status:'in_progress';}
 else if(type==='tool'){let part=message.parts.find(p=>p.type==='tool'&&p.id===payload.id);if(part)Object.assign(part,payload);else message.parts.push({type:'tool',...payload});}
 else if(type==='part'){if(payload.type==='citation')resolveRef(record,payload.ref);message.parts.push(payload);}
 else throw Error('unknownEvent');
 c.events.push(event);c.sequence=event.sequence;return true;
}
export function interruptUnfinished(record){
 let changed=false;
 for(const run of record.conversation.runs)if(!terminal.has(run.status)){changed=true;run.status='interrupted';const m=record.conversation.messages.find(m=>m.id===run.id);m.status='interrupted';for(const p of m.parts)if(p.type==='tool'&&!terminal.has(p.status))p.status='cancelled';}
 return changed;
}
export function markArtifactsOutdated(record){for(const a of record.artifacts)a.status='outdated';}
export function commonSuffix(texts){
 if(texts.length!==2)return '';
 const [a,b]=texts.map(s=>s.split(/\s+/));let n=0;while(n<Math.min(a.length,b.length)&&a[a.length-1-n]===b[b.length-1-n])n++;
 return n>=4?a.slice(-n).join(' '):'';
}

export function artifactMarkdown(record,base,words){
 const clarification=record.conversation.messages.filter(m=>m.role==='user'&&record.conversation.runs.find(r=>r.clientMessageId===m.id)?.operation!=='draft').map(m=>m.parts.filter(p=>p.type==='text').map(p=>p.text).join(' '));
 return base+'\n\n## '+words.artifactVersions+' · V'+(record.artifacts.length+1)+'\n\n'+words.analysisVersion.replace('{version}',String(record.analysisVersion))+(clarification.length?'\n\n## '+words.userClarification+'\n\n'+clarification.map(text=>text.split('\n').map(line=>'> '+line).join('\n')).join('\n\n'):'');
}
