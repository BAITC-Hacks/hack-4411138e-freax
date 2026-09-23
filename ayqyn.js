import {t} from './i18n.js';
import {icon} from './icons.js';
const e=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tx=key=>e(t(key));
const actions=()=>`<div class="hero-actions"><a class="primary" href="#/app/new">${tx('start')}${icon('arrow-right')}</a><a class="secondary" href="#/app/demo">${tx('viewExample')}${icon('external-link')}</a></div>`;
export function renderPresentation(){
 document.getElementById('landing-view').innerHTML=`<div class="editorial-container">
 <section class="editorial-hero">
  <p class="eyebrow editorial-kicker"><span class="signal-dot"></span>${tx('editorialKicker')}<span class="mono">FREAX / AYQYN</span></p>
  <h1>${tx('editorialTitle')}<br><span>${tx('editorialTitleAccent')}</span></h1>
  <div class="hero-intro"><p>${tx('editorialIntro')}</p>${actions()}</div>
  <div class="product-preview" id="product-preview">
   <div class="preview-toolbar"><span class="preview-wordmark">${icon('git-compare-arrows')} AYQYN <span>/ C010</span></span><span class="quiet-badge">${tx('demoLabel')}</span></div>
   <div class="preview-documents">
    <article><header><span class="mono">01 / ${tx('beforeShort')}</span>${icon('file-text')}</header><h2>${tx('previewDocument')}</h2><p class="preview-source-id">C010_before_functions · § 2.5 · ${tx('pageOne')}</p><blockquote lang="ru"><span class="quote-owner">Отдел закупок</span> выбирает поставщиков и заключает договоры закупки оборудования.</blockquote><span class="preview-doc-note">${tx('originalQuote')}</span></article>
    <article><header><span class="mono">02 / ${tx('afterShort')}</span>${icon('file-text')}</header><h2>${tx('previewDocument')}</h2><p class="preview-source-id">C010_after_functions · § 2.5 · ${tx('pageOne')}</p><blockquote lang="ru"><span class="quote-owner">Служба внутреннего аудита</span> выбирает поставщиков и заключает договоры закупки оборудования.</blockquote><span class="preview-doc-note">${tx('originalQuote')}</span></article>
   </div>
   <div class="preview-conclusion"><div class="preview-connection">${icon('git-compare-arrows')}</div><div><p class="eyebrow">C010-F05 · ${tx('preliminary')}</p><strong>${tx('previewTransfer')}</strong><p>${tx('previewTransferText')}</p></div><a href="#/app/demo" class="text-button">${tx('reviewExample')}${icon('arrow-right')}</a></div>
  </div><p class="preview-caption">${tx('previewDisclosure')}</p>
 </section>
 <section class="editorial-section change-study"><div><p class="eyebrow">01 / ${tx('evidenceTitle')}</p><h2>${tx('studyTitle')}</h2><p class="section-copy">${tx('studyIntro')}</p><a href="#/app/demo" class="text-button">${tx('reviewExample')}${icon('arrow-right')}</a></div><div class="study-evidence"><div class="study-line"><span class="mono">§ 2.4</span><p lang="ru">Служба внутреннего аудита ежегодно проводит независимую проверку закупок оборудования.</p></div><div class="study-line"><span class="mono">§ 2.5</span><p lang="ru">Служба внутреннего аудита выбирает поставщиков и заключает договоры закупки оборудования.</p></div><div class="study-verdict">${icon('triangle-alert')}<div><strong>${tx('studyVerdict')}</strong><p>${tx('studyVerdictText')}</p><span class="quiet-badge">${tx('notReviewed')}</span></div></div><p class="helper">${tx('studySource')}</p></div></section>
 <section class="editorial-section change-index" id="capabilities"><div><p class="eyebrow">02 / ${tx('capabilities')}</p><h2>${tx('changesTitle')}</h2><p class="section-copy">${tx('changesIntro')}</p></div><div class="change-list">${[['building','departments','changeUnits'],['git-compare-arrows','function_transfer','changeTransfer'],['triangle-alert','risks','changeRisks']].map(([glyph,title,body],i)=>`<article><span class="mono">0${i+1}</span><div><h3>${icon(glyph)}${tx(title)}</h3><p>${tx(body)}</p></div></article>`).join('')}</div></section>
 <section class="editorial-section journey"><p class="eyebrow">03 / ${tx('guide')}</p><h2>${tx('journeyTitle')}</h2><ol class="editorial-timeline">${[['uploadStep','journeyUpload'],['compareStep','journeyCompare'],['reviewStep','journeyReview'],['report','journeyReport']].map(([title,body],i)=>`<li><span class="mono">0${i+1}</span><h3>${tx(title)}</h3><p>${tx(body)}</p></li>`).join('')}</ol><a class="text-button" href="#/app/new">${tx('openWorkspace')}${icon('arrow-right')}</a></section>
 <section class="editorial-section questions-section"><div><p class="eyebrow">04 / ${tx('boundaries')}</p><h2>${tx('faqTitle')}</h2><p class="section-copy">${tx('faqIntro')}</p></div><div class="editorial-faq">${[['faqFiles','faqFilesAnswer'],['faqLoss','faqLossAnswer'],['faqData','faqDataAnswer'],['faqDecision','faqDecisionAnswer']].map(([q,a])=>`<details><summary>${tx(q)}<span aria-hidden="true">+</span></summary><p>${tx(a)}</p></details>`).join('')}<a class="text-button" href="#/data-policy">${tx('dataPolicy')}${icon('arrow-right')}</a></div></section>
 <section class="editorial-section final-invitation"><p class="eyebrow">AYQYN / ${tx('openWorkspace')}</p><h2>${tx('finalTitle')}</h2><p>${tx('finalText')}</p>${actions()}</section>
 </div>`;
}
export function renderInfo(route){
 const page=route==='/guide'?'guide':route==='/about'?'about':'dataPolicy';
 const content=page==='guide'?[['guidePrepare','journeyUpload'],['guideRun','guideRunText'],['reviewStep','journeyReview'],['report','guideExportText']]:page==='about'?[['teamTrack','aboutText'],['boundaries','aboutLimits']]:[['dataUpload','dataUploadText'],['dataProvider','dataProviderText'],['dataStorage','dataStorageText'],['dataReview','dataReviewText'],['demoLabel','demoPolicyText']];
 document.getElementById('info-view').innerHTML=`<div class="editorial-container"><a class="text-button" href="#/">${icon('chevron-left')}${tx('home')}</a><p class="eyebrow">AYQYN / FREAX</p><h1>${tx(page)}</h1><div class="info-sections">${content.map(([title,body],i)=>`<section><span class="mono">0${i+1}</span><div><h2>${tx(title)}</h2><p>${tx(body)}</p></div></section>`).join('')}</div>${actions()}</div>`;
}
// Only a restrained highlight follows a fine pointer; text never moves.
export function initPresentation(){
 document.addEventListener('pointermove',event=>{
  const preview=event.target.closest('#product-preview');
  if(!preview||!matchMedia('(hover: hover) and (pointer: fine)').matches||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  const r=preview.getBoundingClientRect();preview.style.setProperty('--highlight-x',`${(event.clientX-r.left)/r.width*100}%`);
 });
}
