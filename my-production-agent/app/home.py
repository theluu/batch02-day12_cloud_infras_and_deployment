"""Trang chủ — mission control của Legal Multi-Agent System.

Hiển thị live: trạng thái gateway (/health), bản đồ mạng agent (/agents —
proxy registry), và console gửi câu hỏi vào entry point (Customer Agent).
"""

HOME_HTML = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>legal multi-agent — mission control</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;700&family=IBM+Plex+Mono:wght@400;600&display=swap"
      rel="stylesheet">
<style>
:root{
  --bg:#070b0a; --panel:#0d1412; --line:#1c2a26; --txt:#c9d6d1; --dim:#5d716a;
  --ok:#2bd97c; --warn:#ffb454; --err:#ff5d5d; --accent:#54e6c1; --law:#9d8cff;
}
*{box-sizing:border-box;margin:0}
body{
  background:var(--bg); color:var(--txt); min-height:100vh; padding:44px 20px;
  font-family:"IBM Plex Mono",monospace; font-size:14px; line-height:1.6;
  background-image:
    linear-gradient(var(--line) 1px, transparent 1px),
    linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size:42px 42px; background-position:center;
}
main{max-width:960px;margin:0 auto}
.crt{position:fixed;inset:0;pointer-events:none;opacity:.5;
  background:repeating-linear-gradient(0deg,transparent 0 2px,rgba(0,0,0,.25) 2px 4px)}
header{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:6px}
h1{font-family:"Chakra Petch",sans-serif;font-size:clamp(26px,5vw,42px);color:#fff}
h1 .cursor{display:inline-block;width:.55em;height:1em;background:var(--ok);
   vertical-align:-.12em;animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.sub{color:var(--dim);margin-bottom:28px}
.sub b{color:var(--accent);font-weight:600}
.badge{display:inline-flex;align-items:center;gap:8px;padding:4px 12px;
  border:1px solid var(--line);border-radius:999px;background:var(--panel)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--warn)}
.dot.ok{background:var(--ok);box-shadow:0 0 10px var(--ok);animation:pulse 2s infinite}
@keyframes pulse{50%{box-shadow:0 0 2px var(--ok)}}
.statgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  gap:1px;background:var(--line);border:1px solid var(--line);margin-bottom:30px}
.cell{background:var(--panel);padding:13px 16px}
.cell .k{color:var(--dim);font-size:10px;text-transform:uppercase;letter-spacing:.18em}
.cell .v{font-family:"Chakra Petch",sans-serif;font-size:20px;color:#fff;margin-top:3px}
.cell .v.ok{color:var(--ok)}
section{border:1px solid var(--line);background:var(--panel);padding:22px;margin-bottom:24px}
section h2{font-family:"Chakra Petch",sans-serif;font-size:13px;color:var(--accent);
  text-transform:uppercase;letter-spacing:.24em;margin-bottom:16px}
section h2::before{content:"// "}
/* ── agent network ── */
.registry{display:flex;justify-content:space-between;align-items:center;
  border:1px dashed var(--line);padding:9px 14px;margin-bottom:18px;color:var(--dim)}
.registry b{color:var(--txt)}
.net{display:grid;grid-template-columns:1fr 28px 1fr 28px 1fr;gap:12px;align-items:center}
.arrow{color:var(--dim);text-align:center;font-size:18px;user-select:none}
.col{display:flex;flex-direction:column;gap:12px}
.node{border:1px solid var(--line);background:var(--bg);padding:13px 14px;position:relative;
  transition:border-color .3s}
.node.on{border-color:var(--ok)}
.node .nm{font-family:"Chakra Petch",sans-serif;font-size:15px;color:#fff;
  display:flex;align-items:center;gap:8px}
.node .role{color:var(--dim);font-size:11px;margin-top:4px;min-height:30px}
.node .st{position:absolute;top:11px;right:12px;font-size:10px;letter-spacing:.15em;
  color:var(--err)}
.node.on .st{color:var(--ok)}
.node .tasks{font-size:10px;color:var(--accent);margin-top:6px;word-break:break-all}
.node.law{border-left:3px solid var(--law)}
@media(max-width:760px){.net{grid-template-columns:1fr}.arrow{transform:rotate(90deg)}}
/* ── console ── */
label{display:block;color:var(--dim);font-size:12px;margin:13px 0 6px}
input{width:100%;background:var(--bg);border:1px solid var(--line);color:var(--txt);
  padding:11px 13px;font:inherit;outline:none;transition:border-color .15s}
input:focus{border-color:var(--accent)}
button{margin-top:16px;width:100%;padding:13px;font-family:"Chakra Petch",sans-serif;
  font-size:15px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  background:var(--ok);color:#04130b;border:0;cursor:pointer;transition:transform .08s}
button:hover{transform:translateY(-1px);box-shadow:0 0 24px rgba(43,217,124,.35)}
button:disabled{background:var(--dim);cursor:wait}
pre{background:var(--bg);border:1px dashed var(--line);padding:15px;margin-top:16px;
  white-space:pre-wrap;word-break:break-word;color:var(--accent);min-height:50px;
  max-height:420px;overflow:auto}
pre.err{color:var(--err);border-color:var(--err)}
nav{display:flex;gap:20px;flex-wrap:wrap;color:var(--dim);font-size:13px}
nav a{color:var(--txt);text-decoration:none;border-bottom:1px solid var(--line)}
nav a:hover{color:var(--ok);border-color:var(--ok)}
footer{margin-top:26px;color:var(--dim);font-size:12px}
footer b{color:var(--warn)}
</style>
</head>
<body>
<div class="crt"></div>
<main>
  <header>
    <h1>legal-multiagent<span class="cursor"></span></h1>
    <span class="badge"><span id="dot" class="dot"></span><span id="st">checking…</span></span>
  </header>
  <p class="sub"><b>A2A protocol</b> + <b>LangGraph</b> · agents tự đăng ký registry,
     discovery động, delegation song song</p>

  <div class="statgrid">
    <div class="cell"><div class="k">gateway</div><div id="v-st" class="v">—</div></div>
    <div class="cell"><div class="k">version</div><div id="v-ver" class="v">—</div></div>
    <div class="cell"><div class="k">uptime</div><div id="v-up" class="v">—</div></div>
    <div class="cell"><div class="k">agents online</div><div id="v-ag" class="v">—/4</div></div>
  </div>

  <section>
    <h2>agent network — live từ registry</h2>
    <div class="registry">
      <span>⬢ <b>registry</b> :10000 — service discovery</span>
      <span id="reg-st">…</span>
    </div>
    <div class="net">
      <div class="col">
        <div class="node" id="n-customer">
          <span class="st">OFFLINE</span>
          <div class="nm">customer-agent</div>
          <div class="role">entry point · nhận câu hỏi, route sang Law</div>
          <div class="tasks"></div>
        </div>
      </div>
      <div class="arrow">▸</div>
      <div class="col">
        <div class="node law" id="n-law">
          <span class="st">OFFLINE</span>
          <div class="nm">law-agent</div>
          <div class="role">orchestrator · phân tích luật, quyết định delegation</div>
          <div class="tasks"></div>
        </div>
      </div>
      <div class="arrow">▸</div>
      <div class="col">
        <div class="node" id="n-tax">
          <span class="st">OFFLINE</span>
          <div class="nm">tax-agent</div>
          <div class="role">specialist · thuế, IRS, FBAR/FATCA</div>
          <div class="tasks"></div>
        </div>
        <div class="node" id="n-compliance">
          <span class="st">OFFLINE</span>
          <div class="nm">compliance-agent</div>
          <div class="role">specialist · SEC, SOX, FCPA, GDPR, AML</div>
          <div class="tasks"></div>
        </div>
      </div>
    </div>
  </section>

  <section>
    <h2>hỏi mạng agent — qua customer agent</h2>
    <label for="q">question (delegation chạy 30–60s — kiên nhẫn nhé)</label>
    <input id="q" autocomplete="off"
           value="If a company breaks a contract and avoids taxes, what happens?">
    <button id="go">POST /ask ▸</button>
    <pre id="out">// câu hỏi sẽ đi: gateway → customer → law → tax + compliance → tổng hợp</pre>
  </section>

  <nav>
    <a href="/docs">/docs — Swagger UI</a>
    <a href="/agents">/agents</a>
    <a href="/health">/health</a>
    <a href="/ready">/ready</a>
  </nav>
  <footer>không có key? request sẽ trả <b>401</b> — đó là tính năng, không phải bug.</footer>
</main>
<script>
async function health(){
  try{
    const r = await fetch('/health'); const d = await r.json();
    dot.className = 'dot ok'; st.textContent = 'LIVE';
    document.getElementById('v-st').textContent = d.status.toUpperCase();
    document.getElementById('v-st').className = 'v ok';
    document.getElementById('v-ver').textContent = 'v' + d.version;
    const s = Math.round(d.uptime_seconds);
    document.getElementById('v-up').textContent =
      s < 120 ? s + 's' : Math.round(s/60) + 'm';
  }catch(e){ dot.className = 'dot'; st.textContent = 'UNREACHABLE'; }
}
async function network(){
  const ids = {'customer-agent':'n-customer','law-agent':'n-law',
               'tax-agent':'n-tax','compliance-agent':'n-compliance'};
  try{
    const r = await fetch('/agents'); const d = await r.json();
    const seen = {};
    for(const a of (d.agents || [])){ seen[a.agent_name] = a; }
    let online = 0;
    for(const [name, id] of Object.entries(ids)){
      const el = document.getElementById(id);
      const a = seen[name];
      if(a){
        online++; el.classList.add('on');
        el.querySelector('.st').textContent = 'ONLINE';
        el.querySelector('.tasks').textContent =
          (a.tasks && a.tasks.length) ? 'tasks: ' + a.tasks.join(', ') : 'entry point';
      }else{
        el.classList.remove('on');
        el.querySelector('.st').textContent = 'OFFLINE';
      }
    }
    document.getElementById('v-ag').textContent = online + '/4';
    document.getElementById('v-ag').className = online === 4 ? 'v ok' : 'v';
    document.getElementById('reg-st').textContent = 'ONLINE — ' +
      (d.agents || []).length + ' agents registered';
  }catch(e){
    document.getElementById('reg-st').textContent = 'UNREACHABLE';
  }
}
health(); network();
setInterval(health, 5000); setInterval(network, 5000);
const DEMO_KEY = '__DEMO_KEY__';
go.onclick = async () => {
  go.disabled = true; out.className = '';
  out.textContent = '// đang gửi vào mạng agent… (customer → law → specialists)';
  try{
    const headers = {'Content-Type':'application/json'};
    if(DEMO_KEY) headers['X-API-Key'] = DEMO_KEY;
    const r = await fetch('/ask', {method:'POST', headers,
      body: JSON.stringify({question: q.value})});
    const d = await r.json();
    out.className = r.ok ? '' : 'err';
    out.textContent = r.ok ? d.answer
      : 'HTTP ' + r.status + '\\n' + JSON.stringify(d, null, 2);
  }catch(e){ out.className = 'err'; out.textContent = '// ' + e; }
  go.disabled = false;
};
</script>
</body>
</html>"""
