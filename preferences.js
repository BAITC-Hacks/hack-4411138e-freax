/* Apply persisted preferences before the stylesheet and first paint. */
(()=>{
 let theme='system',language='ru';
 try{theme=localStorage.getItem('osnovanie.theme')||theme;language=localStorage.getItem('osnovanie.language')||language;}catch{}
 if(!['light','dark','system'].includes(theme))theme='system';
 if(!['ru','kk','en'].includes(language))language='ru';
 document.documentElement.dataset.themePreference=theme;
 document.documentElement.dataset.theme=theme==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):theme;
 document.documentElement.lang=language;
})();
