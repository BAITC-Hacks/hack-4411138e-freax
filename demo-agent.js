import {resolveRef,commonSuffix} from './agent-model.js';
// This adapter is deliberately limited to C010. It never handles real uploaded files.
// Tool cards describe local fixture operations, not server/model execution.
export async function executeDemo(record,run,{emit,signal,buildMarkdown,load=()=>fetch('assets/c010/demo.json',{signal}).then(r=>{if(!r.ok)throw Error('demoConnection');return r.json();})}){
 if(record.kind!=='demo'||record.snapshot.case_id!=='C010')throw Error('agentUnavailable');
 const check=()=>{if(signal.aborted)throw new DOMException('Aborted','AbortError');};
 let activeTool;
 async function tool(name,operation,scope=record.snapshot.documents.map(d=>d.id)){activeTool=run.id+':'+name;await emit('tool',{id:activeTool,name,status:'running',scope});check();const output=await operation();check();await emit('tool',{id:activeTool,name,status:'completed',count:Array.isArray(output)?output.length:output.documents?output.documents.length:output?1:0});activeTool=null;return output;}
 try{
  await emit('run-status',{status:'running'});check();
  const fixture=await tool('readFixture',load);
  // Re-read the fixture, and verify every quoted fragment against the immutable case version.
  const quote=ref=>{const {doc,fragment}=resolveRef(record,ref),original=fixture.documents.find(d=>d.id===doc.id)?.chunks.find(p=>p.id===fragment.id);if(!original||original.text!==fragment.text)throw Error('staleContext');return {type:'citation',ref:{type:'fragment',id:fragment.id,documentId:doc.id,versionId:record.analysisVersionId}};};
  const refs=run.contextRefs;
  if(run.operation==='draft'){
   const artifact=await tool('draftConclusion',async()=>({id:'artifact:'+run.id,version:record.artifacts.length+1,analysisVersionId:record.analysisVersionId,status:'ready',locale:run.locale,content:buildMarkdown(record.snapshot),createdAt:new Date().toISOString()}));
   check();if(!record.artifacts.some(a=>a.id===artifact.id))record.artifacts.push(artifact);
   await emit('part',{type:'artifact',id:artifact.id});
  }else if(run.operation==='recheck'&&refs.some(r=>r.type==='finding')){
   const finding=resolveRef(record,refs.find(r=>r.type==='finding'));
   const citedIds=[...finding.before_ids,...finding.after_ids],scope=record.snapshot.documents.filter(d=>d.paragraphs.some(p=>citedIds.includes(p.id))).map(d=>d.id);
   const citations=await tool('readFragments',async()=>['before','after'].flatMap(side=>finding[side+'_ids'].map(id=>{const doc=record.snapshot.documents.find(d=>d.paragraphs.some(p=>p.id===id));return quote({type:'fragment',id,documentId:doc.id,versionId:record.analysisVersionId});})),scope);
   for(const citation of citations)await emit('part',citation);
   const comparison=await tool('compareFragments',async()=>commonSuffix(citations.map(c=>resolveRef(record,c.ref).fragment.text)),scope);
   await emit('part',{type:'finding',id:finding.id,common:comparison});
   await emit('part',{type:'notice',key:'demoInterpretation'});
  }else if(refs.some(r=>r.type==='fragment')){
   const citations=await tool('readFragments',async()=>refs.filter(r=>r.type==='fragment').map(quote),[...new Set(refs.filter(r=>r.type==='fragment').map(r=>r.documentId))]);for(const citation of citations)await emit('part',citation);
   await emit('part',{type:'notice',key:'demoFragmentRead'});
  }else{
   const words=[...new Set(run.text.toLocaleLowerCase().split(/[^\p{L}\p{N}]+/u).filter(w=>w.length>3))];
   const matches=await tool('searchDocuments',async()=>record.snapshot.documents.flatMap(doc=>doc.paragraphs.map(fragment=>({doc,fragment,score:words.filter(w=>fragment.text.toLocaleLowerCase().includes(w)).length}))).filter(x=>x.score>0).sort((a,b)=>b.score-a.score).slice(0,6));
   await emit('part',{type:'notice',key:matches.length?'demoSearchResults':'demoNoMatches'});
   for(const {doc,fragment} of matches)await emit('part',quote({type:'fragment',id:fragment.id,documentId:doc.id,versionId:record.analysisVersionId}));
  }
  check();await emit('run-status',{status:'completed'});
 }catch(error){
  if(activeTool)await emit('tool',{id:activeTool,status:signal.aborted?'cancelled':'failed',errorKey:signal.aborted?'demoCancelled':'demoConnection'});
  await emit('part',{type:'notice',key:signal.aborted?'demoCancelled':error.message==='staleContext'?'staleContext':'demoConnection'});
  await emit('run-status',{status:signal.aborted?'cancelled':'failed'});
 }
}
