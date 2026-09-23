// The same report builder is used by the download action and fixture checks.
export function buildReport(result,{t,date,reportLines,method,scopeText}){
 const lines=['# '+t('reportTitle'),result.mode==='demo'?t('staticExample'):date(result.timestamp),'',...reportLines(),t('advisory'),...(result.warnings||[]).map(w=>t('warning')+': '+w)];
 for(const doc of result.documents||[])lines.push(`${doc.id} · ${doc.name} · ${t(doc.side+'Short')} · SHA-256 ${doc.sha256}`);
 for(const f of result.findings){
  lines.push('',`## ${f.title}`,`${t('typeFilter')}: ${t(f.type)}; ${t('status')}: ${f.reviewed?t(f.status):t('notReviewed')}; ${t('method')}: ${method(f)}`,f.explanation);
  if(f.type==='function_loss')lines.push(scopeText(f));
  if(f.note)lines.push(t('note')+': '+f.note);
  for(const side of ['before','after']){
   if(!f[side+'_ids'].length)lines.push(t(side+'Short')+': '+t('noSource'));
   for(const id of f[side+'_ids']){const p=result[side].paragraphs.find(p=>p.id===id);if(p)lines.push(`${t('sources')}: ${p.document_name||result[side].name} · ${t(side+'Short')} · ${t('paragraph',{section:p.section||t('noNumber'),id})} · ${p.page?t('pageNumber',{page:p.page}):t('pageUnavailable')}`,p.text.split('\n').map(line=>'> '+line).join('\n'));}
  }
 }
 lines.push('',t('recommendations'),t('recommendationText'));return lines.join('\n\n');
}
