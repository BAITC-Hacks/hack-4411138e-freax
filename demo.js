// Synthetic fixture adapter. Reference labels are not current analyst decisions.
export function adaptDemo(data){
 const types={reorganized:'reorganization',created:'department_added',potential_loss:'function_loss',potential_duplication:'duplication',transferred:'function_transfer',potential_conflict:'conflict'};
 const documents=data.documents.map(doc=>({id:doc.id,name:doc.title,side:doc.version,classification:'demo',sha256:doc.sha256,original_url:'assets/c010/'+doc.file,paragraphs:doc.chunks.map(p=>({...p,section:p.clause,document_id:doc.id,document_name:doc.title}))}));
 const sides=Object.fromEntries(['before','after'].map(side=>[side,{name:documents.filter(d=>d.side===side).map(d=>d.name).join(' + '),paragraphs:documents.filter(d=>d.side===side).flatMap(d=>d.paragraphs)}]));
 const findings=data.findings.map(f=>({id:f.id,type:types[f.type],title:f.explanation,explanation:f.explanation,before_ids:f.evidence.filter(e=>e.version==='before').map(e=>e.fragment_id),after_ids:f.evidence.filter(e=>e.version==='after').map(e=>e.fragment_id),search_scope:f.search_scope,status:'unknown',reviewed:false,method:'demo'}));
 return {...sides,documents,findings,mode:'demo',synthetic:true,case_id:data.case_id,warnings:[],trace:[]};
}
