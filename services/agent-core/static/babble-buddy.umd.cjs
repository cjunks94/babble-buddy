(function(d,l){typeof exports=="object"&&typeof module<"u"?l(exports):typeof define=="function"&&define.amd?define(["exports"],l):(d=typeof globalThis<"u"?globalThis:d||self,l(d.BabbleBuddy={}))})(this,function(d){"use strict";var C=Object.defineProperty;var B=(d,l,h)=>l in d?C(d,l,{enumerable:!0,configurable:!0,writable:!0,value:h}):d[l]=h;var c=(d,l,h)=>B(d,typeof l!="symbol"?l+"":l,h);class l{constructor(e,t){c(this,"apiUrl");c(this,"appToken");this.apiUrl=e.replace(/\/$/,""),this.appToken=t}async sendMessage(e){const t=await fetch(`${this.apiUrl}/api/v1/chat`,{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${this.appToken}`},body:JSON.stringify(e)});if(!t.ok)throw new Error(`API error: ${t.status}`);return t.json()}async*streamMessage(e){var i;const t=await fetch(`${this.apiUrl}/api/v1/chat/stream`,{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${this.appToken}`},body:JSON.stringify(e)});if(!t.ok)throw new Error(`API error: ${t.status}`);const o=(i=t.body)==null?void 0:i.getReader();if(!o)throw new Error("No response body");const s=new TextDecoder;let n="";for(;;){const{done:b,value:p}=await o.read();if(b)break;n+=s.decode(p,{stream:!0});const g=n.split(`
`);n=g.pop()||"";for(const m of g)if(!m.startsWith("event: ")&&m.startsWith("data: ")){const w=m.slice(6),f=w.trim();if(f==="")continue;f.startsWith("bb_")||/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(f)?yield{type:"done",data:f}:yield{type:"chunk",data:w}}}}}function h(r){let e=r;const t=new Set;return{getState:()=>e,setState:o=>{e={...e,...o},t.forEach(s=>s())},subscribe:o=>(t.add(o),()=>t.delete(o)),addMessage:o=>{e={...e,messages:[...e.messages,o]},t.forEach(s=>s())},updateLastMessage:o=>{const s=[...e.messages];s.length>0&&(s[s.length-1]={...s[s.length-1],content:o},e={...e,messages:s},t.forEach(n=>n()))},finishStreaming:()=>{const o=[...e.messages];o.length>0&&(o[o.length-1]={...o[o.length-1],isStreaming:!1},e={...e,messages:o,isLoading:!1},t.forEach(s=>s()))}}}const S={primaryColor:"#0f172a",backgroundColor:"#ffffff",textColor:"#1e293b",fontFamily:"system-ui, -apple-system, sans-serif",borderRadius:"12px"};function k(r){const e=r.replace("#",""),t=parseInt(e.substr(0,2),16),o=parseInt(e.substr(2,2),16),s=parseInt(e.substr(4,2),16);return(.299*t+.587*o+.114*s)/255<.5}function E(r,e){var g;const t="babble-buddy-styles";(g=document.getElementById(t))==null||g.remove();const o=$(e),s=k(r.backgroundColor),n=r.assistantBubbleColor||(s?"#3f3f46":"#f3f4f6"),i=r.inputBorderColor||(s?"#52525b":"#e5e7eb"),b=`
    .bb-widget {
      --bb-primary: ${r.primaryColor};
      --bb-bg: ${r.backgroundColor};
      --bb-text: ${r.textColor};
      --bb-font: ${r.fontFamily};
      --bb-radius: ${r.borderRadius};
      --bb-assistant-bubble: ${n};
      --bb-input-border: ${i};

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

    /* Suggestions */
    .bb-suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 8px 12px;
      border-bottom: 1px solid var(--bb-input-border);
    }

    .bb-suggestions:empty {
      display: none;
    }

    .bb-suggestion {
      padding: 6px 12px;
      background: var(--bb-assistant-bubble);
      border: 1px solid var(--bb-input-border);
      border-radius: 16px;
      font-size: 12px;
      font-family: var(--bb-font);
      color: var(--bb-text);
      cursor: pointer;
      transition: background 0.2s, border-color 0.2s;
    }

    .bb-suggestion:hover {
      border-color: var(--bb-primary);
      background: var(--bb-bg);
    }

    /* Debug panel */
    .bb-debug {
      padding: 8px 12px;
      background: #fef3c7;
      border-bottom: 1px solid #fcd34d;
      font-size: 11px;
    }

    .bb-debug-header {
      font-weight: 600;
      color: #92400e;
      margin-bottom: 4px;
    }

    .bb-debug-content {
      color: #78350f;
      word-break: break-word;
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
  `,p=document.createElement("style");p.id=t,p.textContent=b,document.head.appendChild(p)}function $(r){switch(r){case"bottom-left":return"bottom: 20px; left: 20px;";case"top-right":return"top: 20px; right: 20px;";case"top-left":return"top: 20px; left: 20px;";default:return"bottom: 20px; right: 20px;"}}const u={chat:`<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
    <path d="M7 9h10v2H7zm0-3h10v2H7z"/>
  </svg>`,close:`<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
  </svg>`,send:`<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
  </svg>`,bot:`<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1H2a1 1 0 01-1-1v-3a1 1 0 011-1h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2zM7.5 13A1.5 1.5 0 006 14.5 1.5 1.5 0 007.5 16 1.5 1.5 0 009 14.5 1.5 1.5 0 007.5 13zm9 0a1.5 1.5 0 00-1.5 1.5 1.5 1.5 0 001.5 1.5 1.5 1.5 0 001.5-1.5 1.5 1.5 0 00-1.5-1.5z"/>
  </svg>`};function M(r){let e=r.replace(/`\s*`\s*`/g,"```").replace(/`{3,}/g,"```");const t=[];let o=e.replace(/```(\w*)\n?([\s\S]*?)```/g,(n,i,b)=>{const p=t.length,g=i?`<div class="bb-code-lang">${i}</div>`:"";return t.push(`${g}<pre class="bb-code-block"><code>${x(b.trim())}</code></pre>`),`__CODE_BLOCK_${p}__`}),s=x(o);return t.forEach((n,i)=>{s=s.replace(`__CODE_BLOCK_${i}__`,n)}),s=s.replace(/^### (.+)$/gm,'<strong class="bb-h3">$1</strong>'),s=s.replace(/^## (.+)$/gm,'<strong class="bb-h2">$1</strong>'),s=s.replace(/^# (.+)$/gm,'<strong class="bb-h1">$1</strong>'),s=s.replace(/`([^`]+)`/g,'<code class="bb-inline-code">$1</code>'),s=s.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>"),s=s.replace(new RegExp("(?<!\\*)\\*([^*]+)\\*(?!\\*)","g"),"<em>$1</em>"),s=s.replace(new RegExp("(?<!_)_([^_]+)_(?!_)","g"),"<em>$1</em>"),s=s.replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>'),s=s.replace(/\n\n/g,"</p><p>"),s=s.replace(/\n/g,"<br>"),s.includes("</p><p>")&&(s="<p>"+s+"</p>"),s}function x(r){const e={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"};return r.replace(/[&<>"']/g,t=>e[t])}class y{constructor(e){c(this,"config");c(this,"api");c(this,"store");c(this,"container",null);c(this,"messagesEl",null);c(this,"inputEl",null);c(this,"suggestions",[]);c(this,"contextSummary",null);this.config={position:"bottom-right",context:{},theme:{},greeting:"Hi! How can I help you today?",suggestions:[],debug:!1,...e},this.api=new l(e.apiUrl,e.appToken),this.store=h({isOpen:!1,isLoading:!1,messages:[],sessionId:null,error:null}),this.init()}init(){const e={...S,...this.config.theme};E(e,this.config.position),this.render(),this.store.subscribe(()=>this.update()),this.config.greeting&&this.store.addMessage({id:"greeting",role:"assistant",content:this.config.greeting,timestamp:new Date}),this.loadSuggestions()}async loadSuggestions(){if(this.config.suggestions&&this.config.suggestions.length>0){this.suggestions=this.config.suggestions,this.renderSuggestions();return}try{const e=await fetch(`${this.config.apiUrl}/api/v1/suggestions`,{method:"POST",headers:{Authorization:`Bearer ${this.config.appToken}`,"Content-Type":"application/json"},body:JSON.stringify({context:this.config.context})});if(e.ok){const t=await e.json();this.suggestions=t.suggestions||[],this.contextSummary=t.context_summary,this.renderSuggestions(),this.renderDebugPanel()}}catch(e){console.warn("Failed to load suggestions:",e)}}render(){this.container=document.createElement("div"),this.container.className="bb-widget",this.container.innerHTML=this.getHTML(),document.body.appendChild(this.container),this.bindEvents(),this.messagesEl=this.container.querySelector(".bb-messages"),this.inputEl=this.container.querySelector(".bb-input")}getHTML(){return`
      <div class="bb-chat">
        <div class="bb-header">
          ${u.bot}
          <span>Chat Assistant</span>
        </div>
        <div class="bb-suggestions"></div>
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
    `}bindEvents(){var s,n,i;const e=(s=this.container)==null?void 0:s.querySelector(".bb-toggle"),t=(n=this.container)==null?void 0:n.querySelector(".bb-send"),o=(i=this.container)==null?void 0:i.querySelector(".bb-input");e==null||e.addEventListener("click",()=>this.toggle()),t==null||t.addEventListener("click",()=>this.sendMessage()),o==null||o.addEventListener("keydown",b=>{b.key==="Enter"&&!b.shiftKey&&(b.preventDefault(),this.sendMessage())})}toggle(){const{isOpen:e}=this.store.getState();this.store.setState({isOpen:!e})}update(){var n,i,b;const e=this.store.getState(),t=(n=this.container)==null?void 0:n.querySelector(".bb-chat");t==null||t.classList.toggle("bb-open",e.isOpen);const o=(i=this.container)==null?void 0:i.querySelector(".bb-toggle");o&&(o.innerHTML=e.isOpen?u.close:u.chat),this.renderMessages(e.messages),this.inputEl&&(this.inputEl.disabled=e.isLoading);const s=(b=this.container)==null?void 0:b.querySelector(".bb-send");s&&(s.disabled=e.isLoading),this.renderError(e.error)}renderMessages(e){this.messagesEl&&(this.messagesEl.innerHTML=e.map(t=>`
        <div class="bb-message bb-${t.role}${t.isStreaming?" bb-streaming":""}">
          ${t.role==="assistant"&&!t.isStreaming?M(t.content):this.escapeHtml(t.content)}
        </div>
      `).join(""),this.messagesEl.scrollTop=this.messagesEl.scrollHeight)}renderError(e){var o,s;const t=(o=this.container)==null?void 0:o.querySelector(".bb-error");if(t==null||t.remove(),e&&this.messagesEl){const n=document.createElement("div");n.className="bb-error",n.textContent=e,(s=this.messagesEl.parentElement)==null||s.insertBefore(n,this.messagesEl.nextSibling)}}async sendMessage(){const e=this.inputEl;if(!e)return;const t=e.value.trim();if(!t||this.store.getState().isLoading)return;e.value="",this.store.setState({error:null,isLoading:!0});const o={id:crypto.randomUUID(),role:"user",content:t,timestamp:new Date};this.store.addMessage(o);const s={id:crypto.randomUUID(),role:"assistant",content:"",timestamp:new Date,isStreaming:!0};this.store.addMessage(s);try{const{sessionId:n}=this.store.getState();let i="";for await(const b of this.api.streamMessage({message:t,session_id:n||void 0,context:this.config.context}))b.type==="chunk"?(i+=b.data,this.store.updateLastMessage(i)):b.type==="done"&&this.store.setState({sessionId:b.data});this.store.finishStreaming()}catch(n){this.store.setState({error:n instanceof Error?n.message:"Failed to send message",isLoading:!1});const i=this.store.getState().messages.slice(0,-1);this.store.setState({messages:i})}}escapeHtml(e){const t=document.createElement("div");return t.textContent=e,t.innerHTML}renderSuggestions(){var t;const e=(t=this.container)==null?void 0:t.querySelector(".bb-suggestions");!e||this.suggestions.length===0||(e.innerHTML=this.suggestions.map(o=>`<button class="bb-suggestion" data-prompt="${this.escapeHtml(o.prompt)}">${this.escapeHtml(o.label)}</button>`).join(""),e.querySelectorAll(".bb-suggestion").forEach(o=>{o.addEventListener("click",s=>{const n=s.target.getAttribute("data-prompt");n&&this.inputEl&&(this.inputEl.value=n,this.sendMessage())})}))}renderDebugPanel(){var s,n,i;if(!this.config.debug||!this.contextSummary)return;const e=(s=this.container)==null?void 0:s.querySelector(".bb-debug");e==null||e.remove();const t=document.createElement("div");t.className="bb-debug",t.innerHTML=`
      <div class="bb-debug-header">Context</div>
      <div class="bb-debug-content">${this.escapeHtml(this.contextSummary)}</div>
    `;const o=(n=this.container)==null?void 0:n.querySelector(".bb-messages");(i=o==null?void 0:o.parentElement)==null||i.insertBefore(t,o)}open(){this.store.setState({isOpen:!0})}close(){this.store.setState({isOpen:!1})}destroy(){var e;(e=this.container)==null||e.remove()}setContext(e){this.config.context={...this.config.context,...e}}}let a=null;const v={init(r){if(a)return console.warn("BabbleBuddy is already initialized. Call destroy() first."),a;if(!r.appToken)throw new Error("BabbleBuddy: appToken is required");if(!r.apiUrl)throw new Error("BabbleBuddy: apiUrl is required");return a=new y(r),a},getInstance(){return a},destroy(){a==null||a.destroy(),a=null},open(){a==null||a.open()},close(){a==null||a.close()},setContext(r){a==null||a.setContext(r)}};typeof window<"u"&&(window.BabbleBuddy=v),d.BabbleBuddy=v,d.Widget=y,Object.defineProperty(d,Symbol.toStringTag,{value:"Module"})});
