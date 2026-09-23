const assert=require('node:assert/strict');
const fs=require('node:fs');
const moduleUrl=code=>'data:text/javascript;charset=utf-8,'+encodeURIComponent(code);
(async()=>{
 const requests=[];
 global.fetch=async(path,options={})=>{requests.push({path,body:options.body&&JSON.parse(options.body)});return {ok:true,json:async()=>({})};};
 const researchCode=fs.readFileSync('research-client.js','utf8');
 const research=await import(moduleUrl(researchCode));
 const value=research.researchWorkspace({research:{id:'r-'+'a'.repeat(32),budget:{elapsed_seconds:12}},documents:[{id:'d1',name:'a.pdf',synthetic:true}],mode:'agent'});
 assert(value.synthetic);assert.equal(value.seconds,12);assert(value.documents[0].original_url.includes('document=d1'));
 await assert.rejects(()=>research.loadResearch('../secret'));
 assert.equal(requests.length,0);
 global.document={createElement:()=>({className:'',setAttribute(){},addEventListener(){},open:false}),body:{append(){}}};
 const events={},root={hidden:true,innerHTML:'',setAttribute(){},addEventListener(k,fn){events[k]=fn;},querySelector(){return {disabled:false};}};
 const code=fs.readFileSync('live-chat.js','utf8').replace("import {t} from './i18n.js';","const t=key=>key;").replace("import {api} from './research-client.js';",`import {api} from ${JSON.stringify(moduleUrl(researchCode))};`);
 const {createLiveChat}=await import(moduleUrl(code));
 const chat=createLiveChat(root,()=>({key:'in-memory-key',model:'test'}));
 chat.set({mode:'demo'});assert.equal(root.hidden,true);assert.equal(requests.length,0);
 chat.set({mode:'rules',findings:[]});assert(root.innerHTML.includes('chatNoSnapshot'));assert.equal(requests.length,0);
 let postCount=0,posted=[];
 global.fetch=async(path,options={})=>{
  requests.push({path});
  if(options.method==='POST'){postCount++;posted.push(JSON.parse(options.body));if(postCount===1)throw new TypeError('network');return {ok:true,json:async()=>({status:'queued'})};}
  return {ok:true,json:async()=>({messages:[],active_turn:null,conversation_version:2})};
 };
 chat.set({mode:'rules',analysis_id:'a-test',findings:[]});await new Promise(r=>setTimeout(r,0));
 events.input({target:{id:'live-chat-input',value:'<script>question</script>'}});
 events.submit({preventDefault(){}});await new Promise(r=>setTimeout(r,0));
 assert.equal(postCount,1);assert(root.innerHTML.includes('chatRetryRequest'));assert(!root.innerHTML.includes('<script>'));
 await events.click({target:{closest:()=>({hasAttribute:key=>key==='data-live-retry'})}});await new Promise(r=>setTimeout(r,0));
 assert.equal(postCount,2);assert.deepEqual(posted[0],posted[1]);assert.equal(posted[0].expected_version,2);
 assert.equal(posted[0].config.key,'in-memory-key');assert(!root.innerHTML.includes('in-memory-key'));
 chat.deactivate();
 console.log('PASS: research projection, invalid ID rejection, demo isolation, unavailable snapshots, escaped text, identical idempotent delivery retry, conversation version, credentials absent from rendered content.');
})().catch(error=>{console.error(error);process.exit(1);});
