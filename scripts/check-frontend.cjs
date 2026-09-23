const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
(async()=>{
 const saved=new Map();
 global.document={documentElement:{lang:'ru'},querySelectorAll:()=>[],title:''};
 global.localStorage={setItem:(key,value)=>saved.set(key,value)};
 const i18n=await import('data:text/javascript;charset=utf-8,'+encodeURIComponent(fs.readFileSync('i18n.js','utf8')));
 const keys=Object.keys(i18n.dictionaries.ru);
 for(const lang of ['ru','kk','en']){
  assert.deepEqual(Object.keys(i18n.dictionaries[lang]),keys);
  for(const key of keys){assert(i18n.dictionaries[lang][key].trim(),`${lang}:${key}`);assert.deepEqual([...i18n.dictionaries[lang][key].matchAll(/\{(\w+)\}/g)].map(m=>m[1]).sort(),[...i18n.dictionaries.ru[key].matchAll(/\{(\w+)\}/g)].map(m=>m[1]).sort());}
  i18n.setLanguage(lang);assert.equal(document.documentElement.lang,lang);assert.equal(saved.get('osnovanie.language'),lang);
  assert(!i18n.t('shown',{count:1,total:7}).includes('{'));
 }
 i18n.setLanguage('invalid');assert.equal(i18n.language,'en');
 const html=fs.readFileSync('analyze.html','utf8'),js=['analysis.js','report.js','workspace.js'].map(file=>fs.readFileSync(file,'utf8')).join('\n');
 for(const match of html.matchAll(/data-i18n(?:-placeholder|-aria-label|-title)?="([^"]+)"/g))assert(keys.includes(match[1]),`Missing label: ${match[1]}`);
 for(const match of js.matchAll(/\b(?:t|tx)\('([^']+)'/g))if(!match[1].endsWith('_'))assert(keys.includes(match[1]),`Missing message: ${match[1]}`);
 for(const suffix of ['filename','manual','version','unresolved','model'])assert(keys.includes('class_'+suffix));
 const boot=fs.readFileSync('preferences.js','utf8');
 for(const [preference,systemDark,expected] of [['system',true,'dark'],['system',false,'light'],['light',true,'light'],['dark',false,'dark'],['garbage',false,'light']]){
  const root={dataset:{}};
  vm.runInNewContext(boot,{document:{documentElement:root},localStorage:{getItem:key=>key.endsWith('theme')?preference:'kk'},matchMedia:()=>({matches:systemDark})});
  assert.equal(root.dataset.theme,expected);assert.equal(root.lang,'kk');
 }
 const blockedRoot={dataset:{}};vm.runInNewContext(boot,{document:{documentElement:blockedRoot},localStorage:{getItem:()=>{throw Error('blocked');}},matchMedia:()=>({matches:false})});assert.equal(blockedRoot.dataset.theme,'light');
 const luminance=hex=>{const c=hex.match(/\w\w/g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return c[0]*.2126+c[1]*.7152+c[2]*.0722;};
 for(const [fg,bg] of [['102a43','ffffff'],['53657b','f4f7fb'],['ffffff','006eab'],['e6eef9','131f30'],['a7b7cd','17263a'],['0b2339','68c5fa'],['8a5311','fff5e5'],['b23740','fff0f0'],['176c4b','eaf7f0'],['f0c884','352c20'],['ffaab0','38252f'],['86dfba','17362e']]){const l=[luminance(fg),luminance(bg)].sort((a,b)=>b-a);assert((l[0]+.05)/(l[1]+.05)>=4.5,`Contrast ${fg}/${bg}`);}
 const moduleFrom=file=>import('data:text/javascript;charset=utf-8,'+encodeURIComponent(fs.readFileSync(file,'utf8')));
 const {adaptDemo}=await moduleFrom('demo.js'),{buildReport}=await moduleFrom('report.js');
 const fixture=JSON.parse(fs.readFileSync('assets/c010/demo.json','utf8')),demo=adaptDemo(fixture);
 assert.equal(demo.mode,'demo');assert.equal(demo.documents.length,4);assert.equal(demo.findings.length,6);
 assert(demo.findings.every(f=>!f.reviewed&&f.status==='unknown'),'Reference annotations are not human review');
 for(const f of demo.findings)for(const side of ['before','after'])for(const id of f[side+'_ids'])assert(demo[side].paragraphs.some(p=>p.id===id));
 const crypto=require('node:crypto');for(const doc of demo.documents)assert.equal(doc.sha256,crypto.createHash('sha256').update(fs.readFileSync(doc.original_url)).digest('hex'));
 i18n.setLanguage('ru');demo.findings[4].reviewed=true;demo.findings[4].status='confirmed';demo.findings[4].note='Проверка по пункту 2.5';
 const md=buildReport(demo,{t:i18n.t,date:i18n.date,reportLines:()=>[i18n.t('demoDisclosure')],method:()=>i18n.t('demoMethod'),scopeText:f=>f.search_scope.join(', ')});
 assert(md.split('\n').length>50,'Markdown uses actual newlines');assert(md.includes('Синтетические документы'));assert(md.includes('Подтверждено аналитиком'));assert(md.includes('Проверка по пункту 2.5'));assert(md.includes('Страница 1'));assert(md.includes('C010_after_functions'));assert(!md.includes('undefined'));assert(md.includes('> Отдел закупок выбирает поставщиков'));
 console.log('PASS: synthetic fixture adapter, no implicit human review, all source IDs, 4 PDF hashes, Markdown export labels/decisions/pages/quotes.');
 console.log(`PASS: ${keys.length} translation keys Г— 3 languages; placeholders; used labels; preference persistence/fallback; 12 text contrast pairs.`);
})().catch(error=>{console.error(error);process.exitCode=1;});
