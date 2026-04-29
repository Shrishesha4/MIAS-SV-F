import"../chunks/DsnmJJEf.js";import{o as z}from"../chunks/C6gFBCFp.js";import{p as I,a as T,m as F,$ as R,c as U,s as G,r as J}from"../chunks/D-QsM6b3.js";import{a as O,f as j}from"../chunks/Bp9FROz4.js";import{s as K}from"../chunks/YP0piy-L.js";import{h as Q}from"../chunks/BAWiU30r.js";import{g as X}from"../chunks/BLzuuJx3.js";import"../chunks/C05SAPfP.js";import{a as q}from"../chunks/VwpLTBfh.js";import{a as Y}from"../chunks/2X5HCAmc.js";import{i as Z}from"../chunks/B8AcLy13.js";function tt(S,E){I(E,!1);const u=new WeakMap;let h=null,f=null,v=null,p=null;function A(){p&&document.head.contains(p)||(p=document.createElement("style"),p.id="mias-select-enhancer-styles",p.textContent=`
			.mias-native-hidden {
				position: absolute !important;
				width: 1px !important;
				height: 1px !important;
				padding: 0 !important;
				margin: -1px !important;
				overflow: hidden !important;
				clip: rect(0,0,0,0) !important;
				white-space: nowrap !important;
				border: 0 !important;
				opacity: 0 !important;
				pointer-events: none !important;
			}
			.mias-select-trigger {
				display: flex !important;
				align-items: center !important;
				justify-content: space-between !important;
				gap: 8px !important;
				width: 100% !important;
				text-align: left !important;
				cursor: pointer !important;
				background: rgba(255,255,255,0.96) !important;
				border: 1px solid #e2e8f0 !important;
				border-radius: 12px !important;
				padding: 10px 12px !important;
				font-size: 0.875rem !important;
				color: #1e293b !important;
				box-shadow: inset 0 1px 2px rgba(15,23,42,0.04) !important;
				transition: border-color 0.15s, box-shadow 0.15s !important;
				box-sizing: border-box !important;
				min-height: 42px !important;
				outline: none !important;
			}
			.mias-select-trigger:hover:not(:disabled) {
				border-color: #93c5fd !important;
			}
			.mias-select-trigger:focus {
				border-color: #60a5fa !important;
				box-shadow: inset 0 1px 2px rgba(15,23,42,0.04), 0 0 0 2px rgba(96,165,250,0.2) !important;
			}
			.mias-select-trigger:disabled {
				cursor: not-allowed !important;
				opacity: 0.5 !important;
			}
			.mias-select-trigger-label {
				flex: 1 !important;
				overflow: hidden !important;
				text-overflow: ellipsis !important;
				white-space: nowrap !important;
			}
			.mias-select-trigger-label.placeholder {
				color: #94a3b8 !important;
			}
			.mias-select-chevron {
				flex-shrink: 0 !important;
				width: 16px !important;
				height: 16px !important;
				color: #94a3b8 !important;
				transition: transform 0.15s !important;
			}
			.mias-select-chevron.open {
				transform: rotate(180deg) !important;
			}
			.mias-select-dropdown {
				position: fixed !important;
				z-index: 10050 !important;
				background: white !important;
				border: 1px solid rgba(148,163,184,0.24) !important;
				border-radius: 16px !important;
				box-shadow: 0 8px 32px rgba(15,23,42,0.14), 0 2px 8px rgba(15,23,42,0.06) !important;
				overflow: hidden !important;
				display: flex !important;
				flex-direction: column !important;
				max-height: 300px !important;
			}
			.mias-select-search-wrap {
				display: flex !important;
				align-items: center !important;
				gap: 8px !important;
				padding: 8px 12px !important;
				border-bottom: 1px solid rgba(148,163,184,0.16) !important;
				background: rgba(248,250,252,0.9) !important;
				flex-shrink: 0 !important;
			}
			.mias-select-search-wrap svg {
				width: 14px !important;
				height: 14px !important;
				color: #94a3b8 !important;
				flex-shrink: 0 !important;
			}
			.mias-select-search {
				flex: 1 !important;
				border: none !important;
				background: transparent !important;
				outline: none !important;
				font-size: 0.875rem !important;
				color: #1e293b !important;
			}
			.mias-select-search::placeholder {
				color: #94a3b8 !important;
			}
			.mias-select-options {
				overflow-y: auto !important;
				flex: 1 !important;
				min-height: 0 !important;
			}
			.mias-select-option {
				display: block !important;
				width: 100% !important;
				text-align: left !important;
				padding: 9px 14px !important;
				font-size: 0.875rem !important;
				color: #1e293b !important;
				background: transparent !important;
				border: none !important;
				cursor: pointer !important;
				transition: background 0.1s !important;
			}
			.mias-select-option:hover,
			.mias-select-option.highlighted {
				background: rgba(59,130,246,0.06) !important;
				color: #1d4ed8 !important;
			}
			.mias-select-option.selected {
				background: rgba(59,130,246,0.1) !important;
				color: #1d4ed8 !important;
				font-weight: 500 !important;
			}
			.mias-select-empty {
				padding: 12px 14px !important;
				font-size: 0.875rem !important;
				color: #94a3b8 !important;
				text-align: center !important;
			}
		`,document.head.appendChild(p))}function P(t){return Array.from(t.options).filter(e=>!(e.value===""&&e.disabled)).map(e=>({value:e.value,label:e.text||e.value}))}function _(t){const e=t.options[t.selectedIndex];return e?e.text:""}function k(t,e){const c=e.querySelector(".mias-select-trigger-label");if(!c)return;const o=_(t),s=t.options[0];!t.value||s&&s.value===""&&t.selectedIndex===0||!o?(c.textContent=s?.text||"Select...",c.classList.add("placeholder")):(c.textContent=o,c.classList.remove("placeholder")),e.disabled=t.disabled}function b(){if(h&&(h.remove(),h=null),f){const t=u.get(f);t&&t.trigger.querySelector(".mias-select-chevron")?.classList.remove("open"),f=null}}function $(t,e){b(),f=t,e.querySelector(".mias-select-chevron")?.classList.add("open");const o=P(t),s=t.value,a=document.createElement("div");a.className="mias-select-dropdown",h=a;const l=document.createElement("div");l.className="mias-select-search-wrap",l.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>';const n=document.createElement("input");n.type="text",n.placeholder="Search...",n.className="mias-select-search",l.appendChild(n),a.appendChild(l);const d=document.createElement("div");d.className="mias-select-options",a.appendChild(d);let r=-1,g=o.filter(i=>i.value!=="");function L(i){if(d.innerHTML="",i.length===0){const m=document.createElement("div");m.className="mias-select-empty",m.textContent="No results",d.appendChild(m);return}i.forEach((m,w)=>{const x=document.createElement("button");x.type="button",x.className="mias-select-option",x.textContent=m.label,m.value===s&&x.classList.add("selected"),w===r&&x.classList.add("highlighted"),x.addEventListener("mousedown",V=>{V.preventDefault(),M(m.value)}),d.appendChild(x)})}function M(i){t.value=i,t.dispatchEvent(new Event("change",{bubbles:!0})),t.dispatchEvent(new Event("input",{bubbles:!0})),k(t,e),b(),e.focus()}function H(i){const m=i.trim().toLowerCase();m?g=o.filter(w=>w.value!==""&&(w.label.toLowerCase().includes(m)||w.value.toLowerCase().includes(m))):g=o.filter(w=>w.value!==""),r=-1,L(g)}n.addEventListener("input",i=>{H(i.target.value)}),n.addEventListener("keydown",i=>{switch(i.key){case"ArrowDown":i.preventDefault(),r=Math.min(r+1,g.length-1),L(g),d.querySelectorAll(".mias-select-option")[r]?.scrollIntoView({block:"nearest"});break;case"ArrowUp":i.preventDefault(),r=Math.max(r-1,-1),L(g),r>=0&&d.querySelectorAll(".mias-select-option")[r]?.scrollIntoView({block:"nearest"});break;case"Enter":i.preventDefault(),r>=0&&g[r]&&M(g[r].value);break;case"Escape":i.preventDefault(),b(),e.focus();break;case"Tab":b();break}});const y=e.getBoundingClientRect(),N=300,D=Math.max(Math.round(y.width),180);window.innerHeight-y.bottom<N&&y.top>N?(a.style.bottom=`${Math.round(window.innerHeight-y.top+4)}px`,a.style.top="auto"):a.style.top=`${Math.round(y.bottom+4)}px`;const W=Math.min(Math.round(y.left),window.innerWidth-D-8);a.style.left=`${Math.max(W,8)}px`,a.style.width=`${D}px`,document.body.appendChild(a),L(g),requestAnimationFrame(()=>n.focus())}function B(t){if(u.has(t)||t.dataset.searchableEnhanced==="skip"||t.closest(".mias-select-dropdown")||t.options.length<=1)return;A(),t.classList.add("mias-native-hidden");const e=document.createElement("button");e.type="button",e.className="mias-select-trigger";const c=document.createElement("span");c.className="mias-select-trigger-label",e.appendChild(c);const o=document.createElementNS("http://www.w3.org/2000/svg","svg");o.setAttribute("viewBox","0 0 24 24"),o.setAttribute("fill","none"),o.setAttribute("stroke","currentColor"),o.setAttribute("stroke-width","2"),o.setAttribute("stroke-linecap","round"),o.setAttribute("stroke-linejoin","round"),o.classList.add("mias-select-chevron");const s=document.createElementNS("http://www.w3.org/2000/svg","polyline");s.setAttribute("points","6 9 12 15 18 9"),o.appendChild(s),e.appendChild(o),k(t,e),e.addEventListener("click",r=>{if(r.preventDefault(),r.stopPropagation(),f===t){b();return}$(t,e)});const a=Object.getPrototypeOf(t),l=Object.getOwnPropertyDescriptor(a,"value");l&&l.set&&Object.defineProperty(t,"value",{get(){return l.get.call(this)},set(r){l.set.call(this,r),k(t,e)},configurable:!0});const n=new MutationObserver(()=>{k(t,e)});n.observe(t,{childList:!0,subtree:!0,attributes:!0,attributeFilter:["selected"]}),t.insertAdjacentElement("afterend",e);const d=window.getComputedStyle(t.parentElement??t);(d.display==="flex"||d.display==="grid")&&(e.style.flex="1 1 0%",e.style.minWidth="0"),u.set(t,{trigger:e,cleanup:()=>{n.disconnect(),e.remove(),t.classList.remove("mias-native-hidden"),delete t.value}})}function C(){document.querySelectorAll("select").forEach(B)}z(()=>{A(),C(),v=new MutationObserver(o=>{let s=!1;for(const a of o){for(const l of Array.from(a.addedNodes)){if(l.nodeType!==1)continue;const n=l;(n.tagName==="SELECT"||n.querySelectorAll&&n.querySelectorAll("select").length>0)&&(s=!0)}for(const l of Array.from(a.removedNodes)){if(l.nodeType!==1)continue;const n=l;n.tagName==="SELECT"&&u.get(n)?.cleanup()}}s&&requestAnimationFrame(C)}),v.observe(document.body,{childList:!0,subtree:!0});const t=()=>b(),e=()=>b();window.addEventListener("scroll",t,!0),window.addEventListener("resize",e);const c=o=>{if(!h)return;const s=o.target;h.contains(s)||f&&u.get(f)?.trigger.contains(s)||b()};return document.addEventListener("mousedown",c),()=>{v?.disconnect(),b(),window.removeEventListener("scroll",t,!0),window.removeEventListener("resize",e),document.removeEventListener("mousedown",c),p?.remove()}}),Z(),T()}var et=j('<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>'),ot=j('<div class="app-background min-h-screen"><!> <!></div>');function ft(S,E){I(E,!0),z(async()=>{const v=X(q);if(!v.isAuthenticated&&v.userId)try{const p=await Y.refresh();q.setTokens(p.access_token,p.user_id,p.role)}catch{}});var u=ot();Q("12qhfyh",v=>{var p=et();F(()=>{R.title="MIAS - Medical Information Application System"}),O(v,p)});var h=U(u);tt(h,{});var f=G(h,2);K(f,()=>E.children),J(u),O(S,u),T()}export{ft as component};
