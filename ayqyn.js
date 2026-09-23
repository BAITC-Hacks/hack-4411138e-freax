// Native presentation only: no simulated analysis, artificial waits, or third-party runtime.
export function initPresentation({start,example}){
 document.getElementById('hero-start').addEventListener('click',start);
 document.getElementById('hero-example').addEventListener('click',example);
 const preview=document.getElementById('preview-toggle'),source=document.getElementById('preview-source');
 preview.addEventListener('click',()=>{source.hidden=!source.hidden;preview.setAttribute('aria-expanded',String(!source.hidden));});
 const hero=document.getElementById('hero'),scene=document.getElementById('hero-scene');
 const reduced=matchMedia('(prefers-reduced-motion: reduce)'),pointer=matchMedia('(hover: hover) and (pointer: fine)');
 let visible=false,frame=0,x=0,y=0;
 const paint=()=>{
  frame=0;if(!visible||document.hidden||reduced.matches)return;
  scene.style.setProperty('--px',`${x*10}px`);scene.style.setProperty('--py',`${y*8}px`);
  scene.style.setProperty('--rx',`${-y*2.5}deg`);scene.style.setProperty('--ry',`${x*3}deg`);
  const progress=Math.min(1,Math.max(0,-hero.getBoundingClientRect().top/hero.offsetHeight));
  scene.style.setProperty('--scroll-y',`${-progress*18}px`);scene.style.setProperty('--scene-opacity',String(1-progress*.2));
 };
 const request=()=>{if(!frame&&visible&&!document.hidden&&!reduced.matches)frame=requestAnimationFrame(paint);};
 const lifecycle=()=>{document.documentElement.classList.toggle('page-hidden',document.hidden);hero.classList.toggle('motion-paused',!visible||document.hidden||reduced.matches);if(frame){cancelAnimationFrame(frame);frame=0;}if(reduced.matches){scene.removeAttribute('style');}else request();};
 new IntersectionObserver(([entry])=>{visible=entry.isIntersecting;lifecycle();},{threshold:0}).observe(hero);
 hero.addEventListener('pointermove',event=>{if(!pointer.matches||reduced.matches)return;const r=hero.getBoundingClientRect();x=(event.clientX-r.left)/r.width*2-1;y=(event.clientY-r.top)/r.height*2-1;request();});
 hero.addEventListener('pointerleave',()=>{x=y=0;request();});
 window.addEventListener('scroll',request,{passive:true});document.addEventListener('visibilitychange',lifecycle);reduced.addEventListener('change',lifecycle);
 const observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){entry.target.classList.add('reveal');observer.unobserve(entry.target);}},{threshold:.12});
 document.querySelectorAll('.comparison-preview,.ayqyn-timeline li,.packet-card').forEach(el=>observer.observe(el));
}
