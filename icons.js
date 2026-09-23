import createElement from './vendor/lucide/createElement.mjs';
import i0 from './vendor/lucide/icons/plus.mjs';
import i1 from './vendor/lucide/icons/building.mjs';
import i2 from './vendor/lucide/icons/list-checks.mjs';
import i3 from './vendor/lucide/icons/triangle-alert.mjs';
import i4 from './vendor/lucide/icons/file-text.mjs';
import i5 from './vendor/lucide/icons/upload.mjs';
import i6 from './vendor/lucide/icons/arrow-right.mjs';
import i7 from './vendor/lucide/icons/x.mjs';
import i8 from './vendor/lucide/icons/check.mjs';
import i9 from './vendor/lucide/icons/circle-check.mjs';
import i10 from './vendor/lucide/icons/search.mjs';
import i11 from './vendor/lucide/icons/download.mjs';
import i12 from './vendor/lucide/icons/settings.mjs';
import i14 from './vendor/lucide/icons/sun.mjs';
import i15 from './vendor/lucide/icons/moon.mjs';
import i16 from './vendor/lucide/icons/monitor.mjs';
import i17 from './vendor/lucide/icons/menu.mjs';
import i18 from './vendor/lucide/icons/chevron-left.mjs';
import i19 from './vendor/lucide/icons/chevron-right.mjs';
import i21 from './vendor/lucide/icons/external-link.mjs';
import i22 from './vendor/lucide/icons/info.mjs';
import i23 from './vendor/lucide/icons/loader-circle.mjs';
import i24 from './vendor/lucide/icons/files.mjs';
import i25 from './vendor/lucide/icons/git-compare-arrows.mjs';
import i26 from './vendor/lucide/icons/shield-check.mjs';
import i27 from './vendor/lucide/icons/trash.mjs';
const nodes={'plus':i0,'building':i1,'list-checks':i2,'triangle-alert':i3,'file-text':i4,'upload':i5,'arrow-right':i6,'x':i7,'check':i8,'circle-check':i9,'search':i10,'download':i11,'settings':i12,'sun':i14,'moon':i15,'monitor':i16,'menu':i17,'chevron-left':i18,'chevron-right':i19,'external-link':i21,'info':i22,'loader-circle':i23,'files':i24,'git-compare-arrows':i25,'shield-check':i26,'trash':i27};
export function icon(name){
  const node=nodes[name];
  if(!node)return '';
  return createElement(node,{'aria-hidden':'true',focusable:'false',width:20,height:20,'stroke-width':1.8,class:'icon'}).outerHTML;
}
export function hydrateIcons(root=document){
  root.querySelectorAll('[data-icon]').forEach(el=>{el.innerHTML=icon(el.dataset.icon);});
}
