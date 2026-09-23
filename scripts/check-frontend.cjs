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
 const html=fs.readFileSync('analyze.html','utf8'),js=fs.readFileSync('analysis.js','utf8');
 for(const match of html.matchAll(/data-i18n(?:-placeholder|-aria-label|-title)?="([^"]+)"/g))assert(keys.includes(match[1]),`Missing label: ${match[1]}`);
 for(const match of js.matchAll(/\bt\('([^']+)'/g))assert(keys.includes(match[1]),`Missing message: ${match[1]}`);
 const boot=fs.readFileSync('preferences.js','utf8');
 for(const [preference,systemDark,expected] of [['system',true,'dark'],['system',false,'light'],['light',true,'light'],['dark',false,'dark'],['garbage',false,'light']]){
  const root={dataset:{}};
  vm.runInNewContext(boot,{document:{documentElement:root},localStorage:{getItem:key=>key.endsWith('theme')?preference:'kk'},matchMedia:()=>({matches:systemDark})});
  assert.equal(root.dataset.theme,expected);assert.equal(root.lang,'kk');
 }
 const blockedRoot={dataset:{}};vm.runInNewContext(boot,{document:{documentElement:blockedRoot},localStorage:{getItem:()=>{throw Error('blocked');}},matchMedia:()=>({matches:false})});assert.equal(blockedRoot.dataset.theme,'light');
 const luminance=hex=>{const c=hex.match(/\w\w/g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return c[0]*.2126+c[1]*.7152+c[2]*.0722;};
 for(const [fg,bg] of [['102a43','ffffff'],['53657b','f4f7fb'],['ffffff','006eab'],['e6eef9','131f30'],['a7b7cd','17263a'],['0b2339','68c5fa'],['8a5311','fff5e5'],['b23740','fff0f0'],['176c4b','eaf7f0'],['f0c884','352c20'],['ffaab0','38252f'],['86dfba','17362e']]){const l=[luminance(fg),luminance(bg)].sort((a,b)=>b-a);assert((l[0]+.05)/(l[1]+.05)>=4.5,`Contrast ${fg}/${bg}`);}
 console.log(`PASS: ${keys.length} translation keys × 3 languages; placeholders; used labels; preference persistence/fallback; 12 text contrast pairs.`);
})().catch(error=>{console.error(error);process.exitCode=1;});
