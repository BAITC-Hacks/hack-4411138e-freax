// The server owns research state. Reload/read never launches model work.
export async function api(path, payload, timeout=30000){
 const response=await fetch(path,{...(payload?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}:{}),signal:AbortSignal.timeout(timeout)});
 const data=await response.json();
 if(!response.ok){const error=new Error(data.error?.message||data.error||'Request failed');error.status=response.status;error.serverDetail=error.message;throw error;}
 return data;
}
export function researchWorkspace(data){
 const id=data.research.id;
 return {...data,synthetic:data.documents.some(d=>d.synthetic),timestamp:data.research_timestamp||new Date().toISOString(),seconds:data.research.budget?.elapsed_seconds||0,
  documents:data.documents.map(d=>({...d,original_url:`/api/research/${encodeURIComponent(id)}?view=original&document=${encodeURIComponent(d.id)}`}))};
}
export async function loadResearch(id){
 if(!/^r-[a-f0-9]{32}$/.test(id))throw Error('Invalid research ID');
 return researchWorkspace(await api(`/api/research/${id}?view=workspace`));
}
export async function analyzeResearch(documents,config,task,onProgress){
 if(documents.every(d=>d.name.toLowerCase().endsWith('.docx'))&&documents.some(d=>d.side==='auto')){
  const classified=await api('/api/analyze',{documents,classifyOnly:true,useAI:false});
  if(classified.needs_review)return classified;
  documents=documents.map((d,i)=>({...d,side:classified.documents[i].side}));
 }
 const values=documents.map(d=>({...d,role:d.side==='auto'?'unknown':d.side}));
 const packet=await api('/api/packet/read',{documents:values,mode:'manual'},120000);
 if(!packet.ready){
  const error=new Error(packet.warnings.join('\n')||'Select document versions');error.serverDetail=error.message;throw error;
 }
 onProgress({phase:'prepare'});
 const prepared=await api('/api/research/prepare',{documents:values,mode:'manual',task,config:{...config,reasoning_effort:'none'}},600000);
 const id=prepared.id;
 // Only the opaque ID is stored; no documents, provider settings or credentials.
 try{sessionStorage.setItem('ayqyn.lastResearch',id);}catch{}
 onProgress({phase:'run',id,status:prepared.status});
 if(prepared.status==='ready'){
  let stopped=false,timer;
  const poll=async()=>{try{const p=await api(`/api/research/${id}?view=progress`);if(!stopped)onProgress({phase:'run',id,...p});}catch{}finally{if(!stopped)timer=setTimeout(poll,2000);}};
  poll();
  try{await api('/api/research/run',{id,config:{...config,reasoning_effort:'none'}},660000);}
  catch(error){error.researchId=id;throw error;}
  finally{stopped=true;clearTimeout(timer);}
 }
 return loadResearch(id);
}
