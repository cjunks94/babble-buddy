(function(l,d){typeof exports=="object"&&typeof module<"u"?d(exports):typeof define=="function"&&define.amd?define(["exports"],d):(l=typeof globalThis<"u"?globalThis:l||self,d(l.BabbleBuddy={}))})(this,function(l){"use strict";var C=Object.defineProperty;var B=(l,d,h)=>d in l?C(l,d,{enumerable:!0,configurable:!0,writable:!0,value:h}):l[d]=h;var c=(l,d,h)=>B(l,typeof d!="symbol"?d+"":d,h);class d{constructor(e,s){c(this,"apiUrl");c(this,"appToken");this.apiUrl=e.replace(/\/$/,""),this.appToken=s}async sendMessage(e){const s=await fetch(`${this.apiUrl}/api/v1/chat`,{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${this.appToken}`},body:JSON.stringify(e)});if(!s.ok)throw new Error(`API error: ${s.status}`);return s.json()}async*streamMessage(e){var n;const s=await fetch(`${this.apiUrl}/api/v1/chat/stream`,{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${this.appToken}`},body:JSON.stringify(e)});if(!s.ok)throw new Error(`API error: ${s.status}`);const o=(n=s.body)==null?void 0:n.getReader();if(!o)throw new Error("No response body");const t=new TextDecoder;let a="";for(;;){const{done:b,value:p}=await o.read();if(b)break;a+=t.decode(p,{stream:!0});const g=a.split(`
`);a=g.pop()||"";for(const m of g)if(!m.startsWith("event: ")&&m.startsWith("data: ")){const v=m.slice(6),f=v.trim();if(f==="")continue;f.startsWith("bb_")||/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(f)?yield{type:"done",data:f}:yield{type:"chunk",data:v}}}}}function h(r){let e=r;const s=new Set;return{getState:()=>e,setState:o=>{e={...e,...o},s.forEach(t=>t())},subscribe:o=>(s.add(o),()=>s.delete(o)),addMessage:o=>{e={...e,messages:[...e.messages,o]},s.forEach(t=>t())},updateLastMessage:o=>{const t=[...e.messages];t.length>0&&(t[t.length-1]={...t[t.length-1],content:o},e={...e,messages:t},s.forEach(a=>a()))},finishStreaming:()=>{const o=[...e.messages];o.length>0&&(o[o.length-1]={...o[o.length-1],isStreaming:!1},e={...e,messages:o,isLoading:!1},s.forEach(t=>t()))}}}const k={primaryColor:"#0f172a",backgroundColor:"#ffffff",textColor:"#1e293b",fontFamily:"system-ui, -apple-system, sans-serif",borderRadius:"12px"};function S(r){const e=r.replace("#",""),s=parseInt(e.substr(0,2),16),o=parseInt(e.substr(2,2),16),t=parseInt(e.substr(4,2),16);return(.299*s+.587*o+.114*t)/255<.5}function E(r,e){var g;const s="babble-buddy-styles";(g=document.getElementById(s))==null||g.remove();const o=$(e),t=S(r.backgroundColor),a=r.assistantBubbleColor||(t?"#3f3f46":"#f3f4f6"),n=r.inputBorderColor||(t?"#52525b":"#e5e7eb"),b=`
    .bb-widget {
      --bb-primary: ${r.primaryColor};
      --bb-bg: ${r.backgroundColor};
      --bb-text: ${r.textColor};
      --bb-font: ${r.fontFamily};
      --bb-radius: ${r.borderRadius};
      --bb-assistant-bubble: ${a};
      --bb-input-border: ${n};

      position: fixed;
      ${o}
      z-index: 9999;
      font-family: var(--bb-font);
    }

    .bb-toggle {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: var(--bb-primary);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .bb-toggle:hover {
      transform: scale(1.05);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
    }

    .bb-toggle svg {
      width: 28px;
      height: 28px;
      fill: white;
    }

    .bb-chat {
      position: absolute;
      bottom: 70px;
      right: 0;
      width: 380px;
      max-width: calc(100vw - 32px);
      height: 500px;
      max-height: calc(100vh - 100px);
      background: var(--bb-bg);
      border-radius: var(--bb-radius);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      opacity: 0;
      transform: translateY(10px) scale(0.95);
      pointer-events: none;
      transition: opacity 0.2s, transform 0.2s;
    }

    .bb-chat.bb-open {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: auto;
    }

    .bb-header {
      padding: 16px;
      background: var(--bb-primary);
      color: white;
      font-weight: 600;
      font-size: 15px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .bb-header svg {
      width: 20px;
      height: 20px;
      fill: white;
    }

    .bb-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .bb-message {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 16px;
      font-size: 14px;
      line-height: 1.5;
      overflow-wrap: break-word;
      word-break: normal;
    }

    .bb-message.bb-user {
      align-self: flex-end;
      background: var(--bb-primary);
      color: white;
      border-bottom-right-radius: 4px;
    }

    .bb-message.bb-assistant {
      align-self: flex-start;
      background: var(--bb-assistant-bubble);
      color: var(--bb-text);
      border-bottom-left-radius: 4px;
    }

    .bb-message.bb-streaming::after {
      content: '▋';
      animation: bb-blink 1s infinite;
    }

    @keyframes bb-blink {
      0%, 50% { opacity: 1; }
      51%, 100% { opacity: 0; }
    }

    .bb-input-area {
      padding: 12px;
      border-top: 1px solid var(--bb-input-border);
      display: flex;
      gap: 8px;
    }

    .bb-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid var(--bb-input-border);
      border-radius: 20px;
      font-size: 14px;
      font-family: var(--bb-font);
      outline: none;
      transition: border-color 0.2s;
      background: var(--bb-bg);
      color: var(--bb-text);
    }

    .bb-input:focus {
      border-color: var(--bb-primary);
    }

    .bb-input:disabled {
      opacity: 0.6;
    }

    .bb-input::placeholder {
      color: var(--bb-text);
      opacity: 0.5;
    }

    .bb-send {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--bb-primary);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.2s;
    }

    .bb-send:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .bb-send svg {
      width: 18px;
      height: 18px;
      fill: white;
    }

    .bb-error {
      padding: 8px 12px;
      margin: 8px 16px;
      background: #fef2f2;
      color: #dc2626;
      border-radius: 8px;
      font-size: 13px;
    }

    /* Markdown styles */
    .bb-message p {
      margin: 0 0 8px 0;
    }

    .bb-message p:last-child {
      margin-bottom: 0;
    }

    .bb-message .bb-code-lang {
      background: #374151;
      color: #9ca3af;
      font-size: 11px;
      padding: 4px 12px;
      border-radius: 8px 8px 0 0;
      margin: 8px 0 0 0;
      font-family: var(--bb-font);
      text-transform: lowercase;
    }

    .bb-message .bb-code-lang + .bb-code-block {
      margin-top: 0;
      border-radius: 0 0 8px 8px;
    }

    .bb-message .bb-code-block {
      background: #1f2937;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
      font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
      font-size: 12px;
      line-height: 1.5;
      margin: 8px 0;
      white-space: pre-wrap;
      word-break: break-word;
      max-width: 100%;
    }

    .bb-message .bb-code-block code {
      background: none;
      padding: 0;
      color: inherit;
      white-space: pre-wrap;
    }

    .bb-message .bb-inline-code {
      background: rgba(128, 128, 128, 0.2);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
      font-size: 12px;
    }

    .bb-message.bb-user .bb-inline-code {
      background: rgba(255, 255, 255, 0.25);
    }

    .bb-message .bb-h1,
    .bb-message .bb-h2,
    .bb-message .bb-h3 {
      display: block;
      margin: 12px 0 6px 0;
      font-weight: 600;
    }

    .bb-message .bb-h1:first-child,
    .bb-message .bb-h2:first-child,
    .bb-message .bb-h3:first-child {
      margin-top: 0;
    }

    .bb-message .bb-h1 { font-size: 16px; }
    .bb-message .bb-h2 { font-size: 15px; }
    .bb-message .bb-h3 { font-size: 14px; }

    .bb-message a {
      color: inherit;
      text-decoration: underline;
    }

    .bb-message strong {
      font-weight: 600;
    }

    .bb-message em {
      font-style: italic;
    }
  `,p=document.createElement("style");p.id=s,p.textContent=b,document.head.appendChild(p)}function $(r){switch(r){case"bottom-left":return"bottom: 20px; left: 20px;";case"top-right":return"top: 20px; right: 20px;";case"top-left":return"top: 20px; left: 20px;";default:return"bottom: 20px; right: 20px;"}}const u={chat:`<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
    <path d="M7 9h10v2H7zm0-3h10v2H7z"/>
  </svg>`,close:`<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
  </svg>`,send:`<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
  </svg>`,bot:`<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1H2a1 1 0 01-1-1v-3a1 1 0 011-1h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2zM7.5 13A1.5 1.5 0 006 14.5 1.5 1.5 0 007.5 16 1.5 1.5 0 009 14.5 1.5 1.5 0 007.5 13zm9 0a1.5 1.5 0 00-1.5 1.5 1.5 1.5 0 001.5 1.5 1.5 1.5 0 001.5-1.5 1.5 1.5 0 00-1.5-1.5z"/>
  </svg>`};function M(r){let e=r.replace(/`\s*`\s*`/g,"```").replace(/`{3,}/g,"```");const s=[];let o=e.replace(/```(\w*)\n?([\s\S]*?)```/g,(a,n,b)=>{const p=s.length,g=n?`<div class="bb-code-lang">${n}</div>`:"";return s.push(`${g}<pre class="bb-code-block"><code>${x(b.trim())}</code></pre>`),`__CODE_BLOCK_${p}__`}),t=x(o);return s.forEach((a,n)=>{t=t.replace(`__CODE_BLOCK_${n}__`,a)}),t=t.replace(/^### (.+)$/gm,'<strong class="bb-h3">$1</strong>'),t=t.replace(/^## (.+)$/gm,'<strong class="bb-h2">$1</strong>'),t=t.replace(/^# (.+)$/gm,'<strong class="bb-h1">$1</strong>'),t=t.replace(/`([^`]+)`/g,'<code class="bb-inline-code">$1</code>'),t=t.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>"),t=t.replace(new RegExp("(?<!\\*)\\*([^*]+)\\*(?!\\*)","g"),"<em>$1</em>"),t=t.replace(new RegExp("(?<!_)_([^_]+)_(?!_)","g"),"<em>$1</em>"),t=t.replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>'),t=t.replace(/\n\n/g,"</p><p>"),t=t.replace(/\n/g,"<br>"),t.includes("</p><p>")&&(t="<p>"+t+"</p>"),t}function x(r){const e={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"};return r.replace(/[&<>"']/g,s=>e[s])}class y{constructor(e){c(this,"config");c(this,"api");c(this,"store");c(this,"container",null);c(this,"messagesEl",null);c(this,"inputEl",null);this.config={position:"bottom-right",context:{},theme:{},greeting:"Hi! How can I help you today?",...e},this.api=new d(e.apiUrl,e.appToken),this.store=h({isOpen:!1,isLoading:!1,messages:[],sessionId:null,error:null}),this.init()}init(){const e={...k,...this.config.theme};E(e,this.config.position),this.render(),this.store.subscribe(()=>this.update()),this.config.greeting&&this.store.addMessage({id:"greeting",role:"assistant",content:this.config.greeting,timestamp:new Date})}render(){this.container=document.createElement("div"),this.container.className="bb-widget",this.container.innerHTML=this.getHTML(),document.body.appendChild(this.container),this.bindEvents(),this.messagesEl=this.container.querySelector(".bb-messages"),this.inputEl=this.container.querySelector(".bb-input")}getHTML(){return`
      <div class="bb-chat">
        <div class="bb-header">
          ${u.bot}
          <span>Chat Assistant</span>
        </div>
        <div class="bb-messages"></div>
        <div class="bb-input-area">
          <input
            type="text"
            class="bb-input"
            placeholder="Type a message..."
            autocomplete="off"
          />
          <button class="bb-send" aria-label="Send message">
            ${u.send}
          </button>
        </div>
      </div>
      <button class="bb-toggle" aria-label="Toggle chat">
        ${u.chat}
      </button>
    `}bindEvents(){var t,a,n;const e=(t=this.container)==null?void 0:t.querySelector(".bb-toggle"),s=(a=this.container)==null?void 0:a.querySelector(".bb-send"),o=(n=this.container)==null?void 0:n.querySelector(".bb-input");e==null||e.addEventListener("click",()=>this.toggle()),s==null||s.addEventListener("click",()=>this.sendMessage()),o==null||o.addEventListener("keydown",b=>{b.key==="Enter"&&!b.shiftKey&&(b.preventDefault(),this.sendMessage())})}toggle(){const{isOpen:e}=this.store.getState();this.store.setState({isOpen:!e})}update(){var a,n,b;const e=this.store.getState(),s=(a=this.container)==null?void 0:a.querySelector(".bb-chat");s==null||s.classList.toggle("bb-open",e.isOpen);const o=(n=this.container)==null?void 0:n.querySelector(".bb-toggle");o&&(o.innerHTML=e.isOpen?u.close:u.chat),this.renderMessages(e.messages),this.inputEl&&(this.inputEl.disabled=e.isLoading);const t=(b=this.container)==null?void 0:b.querySelector(".bb-send");t&&(t.disabled=e.isLoading),this.renderError(e.error)}renderMessages(e){this.messagesEl&&(this.messagesEl.innerHTML=e.map(s=>`
        <div class="bb-message bb-${s.role}${s.isStreaming?" bb-streaming":""}">
          ${s.role==="assistant"&&!s.isStreaming?M(s.content):this.escapeHtml(s.content)}
        </div>
      `).join(""),this.messagesEl.scrollTop=this.messagesEl.scrollHeight)}renderError(e){var o,t;const s=(o=this.container)==null?void 0:o.querySelector(".bb-error");if(s==null||s.remove(),e&&this.messagesEl){const a=document.createElement("div");a.className="bb-error",a.textContent=e,(t=this.messagesEl.parentElement)==null||t.insertBefore(a,this.messagesEl.nextSibling)}}async sendMessage(){const e=this.inputEl;if(!e)return;const s=e.value.trim();if(!s||this.store.getState().isLoading)return;e.value="",this.store.setState({error:null,isLoading:!0});const o={id:crypto.randomUUID(),role:"user",content:s,timestamp:new Date};this.store.addMessage(o);const t={id:crypto.randomUUID(),role:"assistant",content:"",timestamp:new Date,isStreaming:!0};this.store.addMessage(t);try{const{sessionId:a}=this.store.getState();let n="";for await(const b of this.api.streamMessage({message:s,session_id:a||void 0,context:this.config.context}))b.type==="chunk"?(n+=b.data,this.store.updateLastMessage(n)):b.type==="done"&&this.store.setState({sessionId:b.data});this.store.finishStreaming()}catch(a){this.store.setState({error:a instanceof Error?a.message:"Failed to send message",isLoading:!1});const n=this.store.getState().messages.slice(0,-1);this.store.setState({messages:n})}}escapeHtml(e){const s=document.createElement("div");return s.textContent=e,s.innerHTML}open(){this.store.setState({isOpen:!0})}close(){this.store.setState({isOpen:!1})}destroy(){var e;(e=this.container)==null||e.remove()}setContext(e){this.config.context={...this.config.context,...e}}}let i=null;const w={init(r){if(i)return console.warn("BabbleBuddy is already initialized. Call destroy() first."),i;if(!r.appToken)throw new Error("BabbleBuddy: appToken is required");if(!r.apiUrl)throw new Error("BabbleBuddy: apiUrl is required");return i=new y(r),i},getInstance(){return i},destroy(){i==null||i.destroy(),i=null},open(){i==null||i.open()},close(){i==null||i.close()},setContext(r){i==null||i.setContext(r)}};typeof window<"u"&&(window.BabbleBuddy=w),l.BabbleBuddy=w,l.Widget=y,Object.defineProperty(l,Symbol.toStringTag,{value:"Module"})});
