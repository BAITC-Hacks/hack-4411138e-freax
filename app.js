(() => {
  'use strict';
  const cases = window.TRAINING_CASES;
  const labels = {confirmed:'Подтверждено фрагментом',risk:'Возможный риск',unknown:'Недостаточно данных'};
  let current = 0;
  let progress = cases.map(() => ({attempts:[],hint:false,solved:false}));
  const byId = id => document.getElementById(id);
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function sourceButton(index, text='Открыть фрагменты') { return `<button class="source-link" data-source="${index}">${text}</button>`; }
  function openSource(index) {
    const item = cases[index];
    const sources = item.origin === 'real' ? window.DOCUMENT_SOURCES : item.sources;
    byId('source-origin').textContent = item.origin === 'real' ? 'ДОСЛОВНО ИЗ DOCX · ПУНКТ 3.4' : 'СИНТЕТИЧЕСКИЙ УЧЕБНЫЙ ТЕКСТ';
    byId('source-title').textContent = item.title;
    byId('source-content').innerHTML = sources.map((s,i) => `<article class="document"><p class="eyebrow">${i?'СТАЛО':'БЫЛО'}${s.version?' · РЕДАКЦИЯ '+s.version:''}</p><h3>${esc(s.name)}</h3><span class="status confirmed">Пункт ${esc(s.section)}</span><blockquote>${s.paragraphs.map(p=>`<p>${esc(p)}</p>`).join('')}</blockquote>${s.file?`<a href="${encodeURI(s.file)}" download>Скачать исходный DOCX</a><small>SHA-256: ${esc(s.sha256)}</small>`:'<small>Создано для практикума. Не является цитатой из документов организации.</small>'}</article>`).join('');
    byId('source-dialog').showModal();
  }
  function render() {
    byId('rows').innerHTML = cases.map((c,i)=>`<tr><td>${esc(c.title)}<small>${c.origin==='real'?'Реальные документы · п. 3.4':'Синтетический пример'}</small></td><td>${esc(c.before)}</td><td>${esc(c.after)}</td><td><span class="status ${c.status}">${labels[c.status]}</span><small>${esc(c.claim)}</small></td><td>${sourceButton(i,'Пункт '+c.section)}</td></tr>`).join('');
    byId('steps').innerHTML = cases.map((c,i)=>`<button data-step="${i}" class="${i===current?'active ':''}${progress[i].solved?'done':''}" ${i===current?'aria-current="step"':''}>0${i+1} · ${esc(c.title)}</button>`).join('');
    const c = cases[current], p = progress[current], last = p.attempts.at(-1);
    byId('exercise').innerHTML = `<div class="case-meta">КЕЙС ${current+1} / 3 · ${c.origin==='real'?'РЕАЛЬНЫЕ ДОКУМЕНТЫ':'СИНТЕТИЧЕСКИЙ ПРИМЕР'}${current===1?' · ПЕРЕНОС НАВЫКА':''}</div><h2 id="case-title">${esc(c.title)}</h2><div class="claim"><strong>${esc(c.claim)}</strong>${sourceButton(current)}</div><form id="answer-form"><fieldset ${p.solved?'disabled':''}><legend>${esc(c.question)}</legend>${c.options.map((o,i)=>`<label class="option"><input type="radio" name="answer" value="${i}" ${last===i?'checked':''} required><span>${esc(o)}</span></label>`).join('')}</fieldset>${!p.solved?'<button class="primary" type="submit">'+(p.attempts.length?'Проверить ещё раз':'Проверить ответ')+'</button>':''}</form>${p.attempts.length?`<div class="feedback ${p.solved?'success':''}" role="status"><strong>${p.solved?'Верно':'Пока неверно'} · ${esc(c.verdict)}</strong><p>${esc(c.explanation)}</p>${sourceButton(current,'Проверить объяснение по источнику')}</div>`:''}${p.solved?`<div class="actions">${current<2?'<button class="primary" id="next">Следующий кейс</button>':'<span>Все ответы этого кейса сохранены в результате.</span>'}<span class="case-meta">Попыток: ${p.attempts.length}</span></div>`:''}`;
    const first = progress.filter((p,i)=>p.attempts[0]===cases[i].correct).length;
    const corrected = progress.filter(p=>p.solved&&p.hint).length;
    const completed = progress.filter(p=>p.solved).length;
    byId('stats').innerHTML = [['С первой попытки',`${first} / 3`],['Решено после объяснения',`${corrected} / 3`],['Всего попыток',progress.reduce((n,p)=>n+p.attempts.length,0)],['Кейсов решено',`${completed} / 3`]].map(([l,v])=>`<div class="stat"><span>${l}</span><strong>${v}</strong></div>`).join('');
    byId('summary').innerHTML = completed ? '<h3>Проверенные выводы</h3>'+cases.map((c,i)=>progress[i].solved?`<div class="result-item"><strong>${esc(c.title)}</strong><p>${esc(c.takeaway)}</p><span>${progress[i].hint?'После объяснения':'С первой попытки'}</span></div>`:'').join('') : '';
    byId('answer-form').addEventListener('submit', event => {
      event.preventDefault();
      if(p.solved) return;
      const value = new FormData(event.currentTarget).get('answer');
      if(value===null) return;
      const answer = Number(value);
      p.attempts.push(answer);
      p.solved = answer===c.correct;
      if(!p.solved) p.hint=true;
      render();
    });
    byId('next')?.addEventListener('click',()=>{current++;render();});
  }
  document.addEventListener('click', e => {
    const source = e.target.closest('[data-source]');
    if(source) openSource(Number(source.dataset.source));
    const step = e.target.closest('[data-step]');
    if(step) {current=Number(step.dataset.step);render();}
  });
  byId('close-source').addEventListener('click',()=>byId('source-dialog').close());
  byId('reset').addEventListener('click',()=>{if(confirm('Сбросить все ответы и начать заново?')){progress=cases.map(()=>({attempts:[],hint:false,solved:false}));current=0;render();}});
  render();
})();
