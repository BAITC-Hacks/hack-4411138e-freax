// Browser-only persistence. No credentials or provider configuration enter this store.
let database;
export async function openCaseStore(){
 if(database)return database;
 database=await new Promise((resolve,reject)=>{const req=indexedDB.open('distingt-cases',1);req.onupgradeneeded=()=>req.result.createObjectStore('cases',{keyPath:'id'});req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
 return database;
}
export async function listCases(){const db=await openCaseStore();return new Promise((resolve,reject)=>{const req=db.transaction('cases').objectStore('cases').getAll();req.onsuccess=()=>resolve(req.result.sort((a,b)=>b.createdAt.localeCompare(a.createdAt)));req.onerror=()=>reject(req.error);});}
export async function getCase(id){const db=await openCaseStore();return new Promise((resolve,reject)=>{const req=db.transaction('cases').objectStore('cases').get(id);req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});}
export async function saveCase(record){
 const db=await openCaseStore();return new Promise((resolve,reject)=>{
  const tx=db.transaction('cases','readwrite'),store=tx.objectStore('cases'),req=store.get(record.id);let next;
  req.onsuccess=()=>{const current=req.result;if((current?.revision||0)!==(record.revision||0)){tx.abort();return;}next=(record.revision||0)+1;store.put({...structuredClone(record),revision:next});};
  tx.oncomplete=()=>{record.revision=next;resolve(record);};tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(new Error('caseConflict'));
 });
}
