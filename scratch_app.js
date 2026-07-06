
const $=id=>document.getElementById(id);
const esc=x=>String(x).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const api=()=>pywebview.api;
async function copyText(t){
  try{const r=await api().copy_text(t);if(r&&r.ok)return true;}catch(_){/* fall through */}
  try{await navigator.clipboard.writeText(t);return true;}catch(_){return false;}}
let info={}, divRate=0, eco=null, ecoCat=null, ecoSort="ex", running=false, regenTimer=null;

function toast(m){const t=$("toast");t.textContent=m;t.classList.add("on");
  clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove("on"),2200);}
function logLine(m,c){const l=$("log"),d=document.createElement("div");
  if(c)d.className=c;d.textContent=m;l.appendChild(d);l.scrollTop=l.scrollHeight;}

/* ── nav + theme ── */
document.querySelectorAll(".nav-btn").forEach(b=>b.onclick=()=>{
  document.querySelectorAll(".nav-btn").forEach(x=>x.classList.remove("on"));
  document.querySelectorAll(".page").forEach(x=>x.classList.remove("on"));
  b.classList.add("on");$("p-"+b.dataset.p).classList.add("on");
  if(b.dataset.p==="eco"&&!eco)loadEco();
  if(b.dataset.p==="chance")loadChance();
  if(b.dataset.p==="craft")loadCraft();
  if(b.dataset.p==="exc")loadExc();
  if(b.dataset.p==="prev")loadPreview();
  if(b.dataset.p==="hist")loadHistory();
});
document.addEventListener("keydown",e=>{
  if(e.ctrlKey&&e.key.toLowerCase()==="g"){e.preventDefault();doGenerate();}});
function setTheme(t){document.documentElement.dataset.theme=t;
  $("thDark").classList.toggle("on",t==="dark");$("thLight").classList.toggle("on",t==="light");
  api().set_setting("theme",t);}
$("thDark").onclick=()=>setTheme("dark");$("thLight").onclick=()=>setTheme("light");

/* ── floors ── */
function subCalc(a,u,s,noun){const v=parseFloat($(a).value)||0,unit=$(u).value;
  const ex=unit==="Divine"&&divRate>1?v*divRate:
           unit==="Chaos"&&chaosEx>0?v*chaosEx:v;
  const parts=[];
  if(ex>0){parts.push(ex.toFixed(0)+" ex");
    if(chaosEx>0&&unit!=="Chaos")parts.push("~"+Math.round(ex/chaosEx)+" chaos");
    if(divRate>1&&unit!=="Divine")parts.push((ex/divRate).toFixed(2)+" div");}
  $(s).textContent=ex<=0?`Picking up ${noun}.`:"≈ "+parts.join(" · ");
  return ex;}
const uEx=()=>subCalc("uAmt","uUnit","uSub","every unique");
const gEx=()=>subCalc("gAmt","gUnit","gSub","everything");
let _floorT=null;
function _saveFloors(){clearTimeout(_floorT);
  _floorT=setTimeout(()=>{api().set_setting("min_exalt_unique",uEx());
    api().set_setting("min_exalt_gear",gEx());},400);}
["uAmt","uUnit"].forEach(i=>$(i).addEventListener("input",()=>{uEx();_saveFloors();}));
["gAmt","gUnit"].forEach(i=>$(i).addEventListener("input",()=>{gEx();_saveFloors();}));

$("autoBtn").onclick=async()=>{
  $("autoBtn").disabled=true;$("autoHint").textContent="Analysing league prices…";
  const r=await api().suggest_floors($("league").value,$("keepPct").value);
  $("autoBtn").disabled=false;
  if(r.error){$("autoHint").textContent="✗ "+r.error;return;}
  $("uUnit").value="Exalt";$("gUnit").value="Exalt";
  $("uAmt").value=r.unique;$("gAmt").value=r.gear;
  api().set_setting("min_exalt_unique",uEx());api().set_setting("min_exalt_gear",gEx());
  $("autoHint").textContent=`Set from live data: uniques ≥ ${r.unique} ex (keeps ${r.kept_unique}/${r.total_unique}), rest ≥ ${r.gear} ex (keeps ${r.kept_gear}/${r.total_gear}).`;
  toast("✨ Floors set from live league data");};
/* ── generate ── */
async function poll(){
  const st=await api().status();
  for(const m of st.log)logLine(m,m.startsWith("✓")?"ok":m.startsWith("✗")?"err":"");
  if(st.running)return setTimeout(poll,400);
  running=false;$("go").disabled=false;$("bar").classList.remove("on");
  const d=st.done||{};
  if(d.ok){divRate=d.divine_rate||divRate;
    $("sActive").textContent=d.active.toLocaleString();
    $("sCats").textContent=d.cats_ok+(d.cats_fail?` (+${d.cats_fail}✗)`:"");
    $("sDiv").textContent=d.divine_rate;$("sSecs").textContent=d.secs;
    const fmtTop=ex=>{const dr=d.divine_rate||divRate;
      return dr>1&&ex>=dr?(ex/dr>=100?Math.round(ex/dr).toLocaleString():(ex/dr).toFixed(1))+" div":ex.toLocaleString()+" ex";};
    $("sTop").innerHTML=d.top&&d.top.length?
      "Top: "+d.top.map(t=>`<b>${esc(t.name)}</b> ${fmtTop(t.ex)}`).join(" · "):"";
    $("sVal").textContent=d.val_errors?`⚠ Validation: ${d.val_errors} errors, ${d.val_warnings} warnings`:
      (d.val_warnings?`⚠ Validation: ${d.val_warnings} warnings`:"✓ Validation passed")+
      (d.copied?"  ·  ✓ deployed to bot folder":"");
    $("sum").style.display="block";
    const ob=$("offBanner");
    if(d.stale){ob.textContent=`⚠ poe.ninja was partly unreachable — ${d.stale} categories used cached prices. Prices may be out of date.`;ob.classList.add("on");}
    else ob.classList.remove("on");
    $("sDiff").textContent=(d.added&&d.added.length)||(d.removed&&d.removed.length)?
      `Changes: +${d.added.length} added (${d.added.slice(0,3).join(", ")})`+
      (d.removed.length?` · -${d.removed.length} removed (${d.removed.slice(0,3).join(", ")})`:""):
      "Changes: none since last pickit";
    $("sMoves").textContent=(d.alerts&&d.alerts.length)?"Price moves: "+d.alerts.slice(0,5).join("  ·  "):"";
    if(d.safety){const ob=$("offBanner");
      ob.textContent="🛑 SAFETY: "+d.safety+" — auto-copy was blocked. Check the Preview tab before using this pickit.";
      ob.classList.add("on");}
    logLine(`Done in ${d.secs}s → ${d.path}`,"ok");uEx();gEx();
  } else if(d.error)logLine("✗ "+d.error,"err");}
async function doGenerate(){
  if(running)return;running=true;$("go").disabled=true;$("bar").classList.add("on");
  await api().generate($("league").value,gEx(),uEx());poll();}
$("go").onclick=doGenerate;
$("force").onclick=async()=>{await api().clear_cache();eco=null;toast("Cache cleared — fetching fresh prices");doGenerate();};
$("open").onclick=()=>api().open_output();
$("openIpd").onclick=async()=>{const r=await api().open_file("ipd");if(r.error)toast(r.error);};
$("openFlt").onclick=async()=>{const r=await api().open_file("filter");if(r.error)toast(r.error);};

/* ── profiles ── */
async function loadProfiles(){
  const p=await api().profiles();const sel=$("profSel");
  sel.innerHTML='<option value="">— no profile —</option>';
  for(const n of p.names){const o=document.createElement("option");o.value=o.textContent=n;sel.appendChild(o);}
  sel.value=p.active||"";
  $("profHint").textContent=p.active?`Active: ${p.active}`:"";}
$("profSel").onchange=async()=>{const n=$("profSel").value;if(!n)return;
  const r=await api().profile_load(n);
  if(r.ok){info=r.info;$("uAmt").value=info.min_unique;$("gAmt").value=info.min_gear;
    $("outBase").value=info.output_base;uEx();gEx();eco=null;
    $("profHint").textContent="Active: "+n;toast("Profile loaded: "+n);}};
$("profSave").onclick=async()=>{const n=prompt("Profile name (existing name = overwrite):",$("profSel").value||"");
  if(!n)return;await api().profile_save(n);await loadProfiles();toast("Profile saved: "+n);};
$("profDel").onclick=async()=>{const n=$("profSel").value;if(!n)return toast("Pick a profile first");
  if(!confirm(`Delete profile "${n}"? Your current settings stay.`))return;
  await api().profile_delete(n);await loadProfiles();toast("Deleted "+n);};
$("profCmp").onclick=async()=>{
  const p=await api().profiles();
  if(p.names.length<2){toast("Save at least two profiles to compare");return;}
  const box=$("cmpBox");
  if(box.style.display==="block"){box.style.display="none";return;}
  renderCompare(p.names,p.names[0],p.names[1]);};
async function renderCompare(names,a,b){
  const box=$("cmpBox");
  const A=await api().profile_get(a),B=await api().profile_get(b);
  const rows=[["Unique floor",A.min_unique+" ex",B.min_unique+" ex"],
    ["Other floor",A.min_gear+" ex",B.min_gear+" ex"],
    ["Output",A.output_base,B.output_base],
    ["Gear bases",A.include_bases?"on":"off",B.include_bases?"on":"off"],
    ["Base quality",A.base_quality+"%",B.base_quality+"%"],
    ["Base ilvl",A.base_min_level,B.base_min_level]];
  const cats=new Set([...Object.keys(A.disabled_counts||{}),...Object.keys(B.disabled_counts||{})]);
  for(const c of cats)rows.push(["Excluded in "+c,(A.disabled_counts[c]||0)+" items",(B.disabled_counts[c]||0)+" items"]);
  const opts=n=>names.map(x=>`<option${x===n?" selected":""}>${esc(x)}</option>`).join("");
  box.innerHTML=`<div style="display:flex;gap:8px;margin-bottom:8px">
      <select id="cmpA">${opts(a)}</select><span style="color:var(--dim)">vs</span>
      <select id="cmpB">${opts(b)}</select></div>
    <table><thead><tr><th></th><th>${esc(a)}</th><th>${esc(b)}</th></tr></thead><tbody>`+
    rows.map(r=>`<tr${String(r[1])!==String(r[2])?' style="color:var(--warn)"':''}>
      <td>${esc(r[0])}</td><td>${esc(r[1])}</td><td>${esc(r[2])}</td></tr>`).join("")+"</tbody></table>";
  box.style.display="block";
  $("cmpA").onchange=()=>renderCompare(names,$("cmpA").value,$("cmpB").value);
  $("cmpB").onchange=()=>renderCompare(names,$("cmpA").value,$("cmpB").value);}

/* ── economy ── */
let ecoUnit="ex",chaosEx=0;
async function loadEco(){
  $("ecoInfo").textContent="Loading prices…";
  eco=await api().economy($("league").value);
  if(eco.error){$("ecoInfo").textContent="✗ "+eco.error;eco=null;return;}
  divRate=eco.divine_rate||divRate;
  api().chaos_ex($("league").value).then(r=>chaosEx=r.ex||0);
  const st=$("ecoStale");
  if(eco.stale&&eco.stale.length){st.textContent=`⚠ Offline: ${eco.stale.length} categories are showing cached prices (poe.ninja unreachable).`;st.classList.add("on");}
  else st.classList.remove("on");
  if(!ecoCat)ecoCat=eco.cats[0].key;
  renderChips();renderEco();
  $("ecoInfo").textContent=`1 div = ${eco.divine_rate} ex`;}
function fmtVal(ex){
  if(ecoUnit==="div"&&divRate>1)return (ex/divRate).toFixed(2)+" div";
  if(ecoUnit==="chaos"&&chaosEx>0)return Math.round(ex/chaosEx).toLocaleString()+" c";
  return ex.toLocaleString()+" ex";}
document.querySelectorAll("#unitChips .chip").forEach(c=>c.onclick=()=>{
  document.querySelectorAll("#unitChips .chip").forEach(x=>x.classList.remove("on"));
  c.classList.add("on");ecoUnit=c.dataset.u;eco&&renderEco();});
$("ecoReload").onclick=()=>{eco=null;loadEco();};
function renderChips(){
  const c=$("ecoChips");c.innerHTML="";
  const group=k=>k.startsWith("_ap_")?"ALWAYS PICK":(k.startsWith("unique_")?"UNIQUES":"MARKET");
  let lastG=null;
  for(const cat of eco.cats){
    const g=group(cat.key);
    if(g!==lastG){lastG=g;
      const h=document.createElement("div");
      h.textContent=g;
      h.style.cssText="padding:10px 10px 4px;font-size:10.5px;font-weight:600;letter-spacing:1px;color:var(--dim)";
      c.appendChild(h);}
    const en=eco.cat_enabled[cat.key];
    const b=document.createElement("div");
    b.className="nav-btn"+(cat.key===ecoCat?" on":"");
    b.style.cssText="font-size:12.5px;padding:7px 10px"+(en?"":";opacity:.45");
    const n=cat.items?cat.items.length:0;
    const lbl=cat.key.startsWith("unique_")?cat.label.replace(/^Unique /,""):cat.label;
    b.innerHTML=`${esc(lbl)}<span style="margin-left:auto;font-size:10.5px;color:var(--dim)">${en?n:"off"}</span>`;
    b.title=en?"Click to open · double-click to disable the whole category":"Category is OFF — double-click to enable";
    b.onclick=()=>{ecoCat=cat.key;renderChips();renderEco();};
    b.ondblclick=async()=>{const e2=!eco.cat_enabled[cat.key];eco.cat_enabled[cat.key]=e2;
      await api().set_category(cat.key,e2);renderChips();
      toast((e2?"Enabled ":"Disabled ")+cat.label);};
    c.appendChild(b);}}
function ecoMatch(it,q){
  // every search term must match the START of a word in the name or base
  // ("ring" finds Gold Ring / Breach Ring, not Fracturing / Suffering)
  const words=(it.name+" "+(it.base||"")).toLowerCase().split(/[\s'-]+/);
  return q.split(/\s+/).every(t=>words.some(w=>w.startsWith(t)));}
function ecoRows(){
  const q=($("ecoSearch").value||"").trim().toLowerCase();
  let rows=[];
  if(q){for(const cat of eco.cats)for(const it of cat.items)
      if(ecoMatch(it,q))rows.push([cat,it]);}
  else{const cat=eco.cats.find(c=>c.key===ecoCat);if(cat)rows=cat.items.map(i=>[cat,i]);}
  return rows;}
function renderEco(){
  const q=($("ecoSearch").value||"").toLowerCase();
  const body=$("ecoBody");body.innerHTML="";
  let rows=ecoRows();
  const isStatic=!q&&(ecoCat||"").startsWith("_ap_");
  if(!isStatic)rows.sort((a,b)=>ecoSort==="name"?a[1].name.localeCompare(b[1].name):
    ecoSort==="chg"?(b[1].chg||0)-(a[1].chg||0):b[1].ex-a[1].ex);
  for(const [cat,it] of rows.slice(0,400)){
    const tr=document.createElement("tr");tr.className="item"+(it.enabled?"":" dis");
    const ico=it.icon?`<img class="icn" loading="lazy" src="${esc(it.icon)}" onerror="this.style.display='none'">`
      :(it.emj?`<span class="icn" style="display:inline-flex;align-items:center;justify-content:center;font-size:15px">${it.emj}</span>`:"");
    const nm=ico+esc(it.name)+(q?` <span class="pill" title="${esc(cat.label)}">${esc(cat.label)}</span>`:"")+
      (it.base?` <span class="pill" title="${esc(it.base)}">${esc(it.base)}</span>`:"");
    const chg=it.chg==null?"":`<span class="chg ${it.chg>=0?"up":"dn"}">${it.chg>=0?"▲":"▼"} ${Math.abs(it.chg)}%</span>`;
    tr.innerHTML=`<td>${nm}</td><td class="val">${it.static?'<span class="pill">always picked</span>':fmtVal(it.ex)}</td>
      <td style="text-align:right">${chg}</td>
      <td style="text-align:center"><span class="pill ${it.enabled?"on":""}">${it.enabled?"yes":"no"}</span></td>
      <td><button class="rowbtn">copy</button></td>`;
    tr.querySelector(".rowbtn").onclick=async e=>{e.stopPropagation();
      const rule=await api().rule_for(cat.key,it.name,cat.unique,it.base||"",it.ex);
      const ok=await copyText(rule);
      toast(ok?"Rule copied":"Clipboard blocked");};
    tr.onclick=async()=>{it.enabled=!it.enabled;
      await api().set_item(cat.key,it.name,it.enabled);renderEco();};
    body.appendChild(tr);}}
async function ecoBulk(en){
  if(!eco)return;
  const rows=ecoRows();
  const byCat={};
  for(const [cat,it] of rows){(byCat[cat.key]=byCat[cat.key]||[]).push(it.name);it.enabled=en;}
  for(const k in byCat)await api().set_items_bulk(k,byCat[k],en);
  renderEco();toast((en?"Enabled ":"Disabled ")+rows.length+" items");}
$("ecoAll").onclick=()=>ecoBulk(true);
$("ecoNone").onclick=()=>ecoBulk(false);
$("ecoSearch").addEventListener("input",()=>eco&&renderEco());
document.querySelectorAll("th[data-s]").forEach(th=>th.onclick=()=>{ecoSort=th.dataset.s;eco&&renderEco();});

/* ── chance ── */
let chanceList=[];
function chanceCount(){$("chanceCount").textContent=
  `${chanceList.filter(b=>b.enabled).length} / ${chanceList.length} enabled.`;}
async function loadChance(){
  chanceList=await api().chance_bases();const g=$("chanceGrid");g.innerHTML="";
  let lastCat=null;
  for(const b of chanceList){
    if(b.cat!==lastCat){lastCat=b.cat;
      const h=document.createElement("div");h.className="gsec";h.textContent=b.cat;g.appendChild(h);}
    const d=document.createElement("div");
    d.className="bcard"+(b.enabled?"":" dis");
    const cIco=b.icon?`<img class="icn" loading="lazy" src="${b.icon}" style="width:30px;height:30px;float:right">`:"";
    d.innerHTML=`${cIco}<b>${esc(b.base)}</b><div class="t">→ ${esc(b.target)}</div>`;
    d.onclick=async()=>{b.enabled=!b.enabled;
      await api().set_item("_chance",b.base,b.enabled);
      d.className="bcard"+(b.enabled?"":" dis");chanceCount();};
    g.appendChild(d);}
  chanceCount();}
async function chanceBulk(en){
  for(const b of chanceList)b.enabled=en;
  await api().set_items_bulk("_chance",chanceList.map(b=>b.base),en);
  loadChance();toast((en?"Enabled":"Disabled")+" all chance bases");}
$("chanceAll").onclick=()=>chanceBulk(true);
$("chanceNone").onclick=()=>chanceBulk(false);

/* ── craft ── */
let craftList=[];
function craftCount(){$("craftCount").textContent=
  `${craftList.filter(b=>b.enabled).length} / ${craftList.length} enabled.`;}
async function loadCraft(){
  craftList=await api().craft_bases();const g=$("craftGrid");g.innerHTML="";
  let lastCat=null;
  for(const b of craftList){
    if(b.cat!==lastCat){lastCat=b.cat;
      const h=document.createElement("div");h.className="gsec";h.textContent=b.cat;g.appendChild(h);}
    const d=document.createElement("div");
    d.className="bcard"+(b.enabled?"":" dis");
    const kIco=b.icon?`<img class="icn" loading="lazy" src="${b.icon}" style="width:30px;height:30px;float:right">`:"";
    const kMeta=[b.lvl?`lvl ${b.lvl}`:"",b.stats||""].filter(x=>x).join(" · ");
    d.innerHTML=`${kIco}<b>${esc(b.base)}</b><div class="t">${esc(kMeta)||"&nbsp;"}</div>
      <div class="ilvl">min ilvl <input type="number" min="1" max="82" value="${b.ilvl}"></div>`;
    const inp=d.querySelector("input");
    inp.onclick=e=>e.stopPropagation();
    inp.onchange=()=>api().set_craft(b.base,b.enabled,inp.value);
    d.onclick=async()=>{b.enabled=!b.enabled;
      await api().set_craft(b.base,b.enabled,inp.value);
      d.className="bcard"+(b.enabled?"":" dis");craftCount();};
    g.appendChild(d);}
  craftCount();}
async function craftBulk(en){
  for(const b of craftList)await api().set_craft(b.base,en,b.ilvl);
  loadCraft();toast((en?"Enabled":"Disabled")+" all craft bases");}
$("craftAll").onclick=()=>craftBulk(true);
$("craftNone").onclick=()=>craftBulk(false);

/* ── exceptional ── */
async function loadExc(){
  const cats=await api().exceptional_bases();const g=$("excGrid");g.innerHTML="";
  let total=0,on=0;
  const cnt=()=>{$("excCount").textContent=`${on} / ${total} enabled.`};
  for(const c of cats){
    const h=document.createElement("div");h.className="gsec";h.textContent=c.cat;g.appendChild(h);
    for(const b of c.bases){total++;if(b.enabled)on++;
      const d=document.createElement("div");
      d.className="bcard"+(b.enabled?"":" dis");
      const ico=b.icon?`<img class="icn" loading="lazy" src="${b.icon}" style="width:30px;height:30px;float:right">`:"";
      const meta=[b.lvl?`lvl ${b.lvl}`:"",b.stats||""].filter(x=>x).join(" · ");
      d.innerHTML=`${ico}<b>${esc(b.name)}</b><div class="t">${esc(meta)||"&nbsp;"}</div>`;
      d.title="Click to include/exclude this base (white pickup + its uniques)";
      d.onclick=async()=>{b.enabled=!b.enabled;b.enabled?on++:on--;
        await api().set_item("_excbase",b.name,b.enabled);
        d.className="bcard"+(b.enabled?"":" dis");cnt();};
      g.appendChild(d);}}
  cnt();}

/* ── history ── */
function drawHistChart(h){
  const svg=$("histChart"),tip=$("histTip");
  const W=svg.clientWidth||820,H=180,PL=46,PR=14,PT=14,PB=26;
  const runs=h.slice().reverse();               // oldest → newest
  const vals=runs.map(r=>r.active||0);
  if(vals.length<2){svg.innerHTML=`<text x="${PL}" y="${H/2}" fill="var(--dim)" font-size="12.5">Not enough data yet — generate a couple of times and the trend appears here.</text>`;return;}
  const mn=Math.min(...vals),mx=Math.max(...vals);
  const lo=Math.max(0,mn-(mx-mn||1)*0.15),hi=mx+(mx-mn||1)*0.15,rng=hi-lo||1;
  const X=i=>PL+i*(W-PL-PR)/(vals.length-1);
  const Y=v=>PT+(hi-v)*(H-PT-PB)/rng;
  // recessive grid: 3 horizontal lines with value labels in muted ink
  let g="";
  for(let k=0;k<3;k++){const v=lo+rng*(k+1)/4,y=Y(v);
    g+=`<line x1="${PL}" y1="${y}" x2="${W-PR}" y2="${y}" stroke="var(--border)" stroke-width="1"/>
        <text x="${PL-8}" y="${y+4}" fill="var(--dim)" font-size="10.5" text-anchor="end">${Math.round(v).toLocaleString()}</text>`;}
  const pts=vals.map((v,i)=>[X(i),Y(v)]);
  const line=pts.map(p=>p[0].toFixed(1)+","+p[1].toFixed(1)).join(" ");
  const first=runs[0].ts.split(" ")[0],last=runs[runs.length-1].ts;
  svg.innerHTML=g+
    `<polygon points="${PL},${H-PB} ${line} ${W-PR},${H-PB}" fill="rgba(200,169,110,.12)"/>
     <polyline points="${line}" fill="none" stroke="var(--gold)" stroke-width="2" stroke-linejoin="round"/>`+
    pts.map((p,i)=>`<circle cx="${p[0]}" cy="${p[1]}" r="${i===pts.length-1?4:2.5}" fill="var(--gold)"
       ${i===pts.length-1?'stroke="var(--bg2)" stroke-width="2"':''}/>`).join("")+
    `<text x="${PL}" y="${H-8}" fill="var(--dim)" font-size="10.5">${first}</text>
     <text x="${W-PR}" y="${H-8}" fill="var(--dim)" font-size="10.5" text-anchor="end">${last}</text>
     <circle id="hcHover" r="5" fill="none" stroke="var(--gold)" stroke-width="2" style="display:none"/>`;
  // hover layer: nearest-point crosshair + tooltip
  svg.onmousemove=e=>{
    const r=svg.getBoundingClientRect(),x=e.clientX-r.left;
    let i=Math.round((x-PL)/((W-PL-PR)/(vals.length-1)));
    i=Math.max(0,Math.min(vals.length-1,i));
    const hc=svg.querySelector("#hcHover");
    hc.setAttribute("cx",pts[i][0]);hc.setAttribute("cy",pts[i][1]);hc.style.display="block";
    tip.innerHTML=`<b style="color:var(--gold)">${vals[i].toLocaleString()}</b> active rules<br>
      <span style="color:var(--dim)">${runs[i].ts} · ${runs[i].commented} skipped · top: ${esc(runs[i].top_item||"—")}</span>`;
    tip.style.display="block";
    tip.style.left=Math.min(pts[i][0]+12,W-230)+"px";
    tip.style.top=Math.max(pts[i][1]-52,0)+"px";};
  svg.onmouseleave=()=>{tip.style.display="none";
    const hc=svg.querySelector("#hcHover");if(hc)hc.style.display="none";};}
async function loadHistory(){
  const h=await api().history();
  const vals=h.map(r=>r.active||0);
  $("htRuns").textContent=h.length||"–";
  $("htLast").textContent=h.length?vals[0].toLocaleString():"–";
  $("htAvg").textContent=h.length?Math.round(vals.reduce((a,b)=>a+b,0)/vals.length).toLocaleString():"–";
  $("htPeak").textContent=h.length?Math.max(...vals).toLocaleString():"–";
  drawHistChart(h);
  const tb=$("histRows");
  tb.innerHTML=h.length?h.map(r=>`<tr>
      <td>${r.ts}</td><td class="val">${(r.active||0).toLocaleString()}</td>
      <td style="text-align:right;color:var(--dim)">${r.commented||0}</td>
      <td style="text-align:right;color:var(--dim)">${Number(r.divine_rate||0).toFixed(0)} ex</td>
      <td>${esc(r.top_item||"—")}${r.top_value?` <span class="pill">${(()=>{const dr=Number(r.divine_rate)||0,v=Number(r.top_value);
        return dr>1&&v>=dr?(v/dr>=100?Math.round(v/dr).toLocaleString():(v/dr).toFixed(1))+" div":v.toLocaleString()+" ex";})()}</span>`:""}</td>
      <td style="text-align:right;color:var(--dim)">${r.duration||""}</td></tr>`).join(""):
    '<tr><td colspan="6" class="hint" style="padding:14px">No runs yet.</td></tr>';}
$("histClear").onclick=async()=>{if(!confirm("Clear all run history?"))return;
  await api().clear_history();loadHistory();toast("History cleared");};

/* ── debug ── */
function dbg(t){const o=$("dbgOut");o.textContent=t;o.scrollTop=0;
  o.closest(".page").scrollTop=0;}
$("dbgApi").onclick=async()=>{dbg("Testing all endpoints…");
  const r=await api().api_test($("league").value);
  const ok=r.filter(x=>x.ok).length;
  const o=$("dbgOut");
  o.innerHTML=`<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
      <span class="pill ${ok===r.length?"on":""}" style="font-size:13px;padding:4px 14px">${ok===r.length?"✓ All good":"⚠ "+(r.length-ok)+" failed"}</span>
      <span style="color:var(--dim);font-size:12.5px">${ok} / ${r.length} endpoints answered</span></div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:6px">`+
    r.map(x=>`<div style="display:flex;align-items:center;gap:8px;padding:7px 11px;border:1px solid ${x.ok?"var(--border)":"var(--err)"};border-radius:9px;background:var(--bg3)">
      <span style="color:${x.ok?"var(--ok)":"var(--err)"};font-weight:700">${x.ok?"✓":"✗"}</span>
      <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(x.label)}</span>
      <span style="color:var(--dim);font-size:11.5px;white-space:nowrap">${x.ok?x.rows+" rows":""}</span></div>`
      +(x.ok?"":`<div style="grid-column:1/-1;color:var(--err);font-size:12px;padding:0 4px 4px">${esc(x.label)}: ${esc(x.error||"")}</div>`)).join("")+
    `</div>`;
  o.closest(".page").scrollTop=0;};
$("dbgInfo").onclick=async()=>{const d=await api().debug_info();
  dbg(`Cached payloads : ${d.cache.count} (TTL ${d.cache.ttl_secs}s)\n`+
      `Categories      : ${d.all_cats} total, ${d.unique_cats} unique\n`+
      `Config          : ${d.config_path}\nPrice cache dir : ${d.cache_dir}\n\n— debug.log (last lines) —\n`+
      d.log.join("\n"));};
$("dbgClear").onclick=async()=>{await api().clear_cache();toast("Price cache cleared");};
$("dbgPrune").onclick=async()=>{const r=await api().prune_cache();toast(r.removed?`Pruned ${r.removed} old cache file(s)`:"Cache is already clean — nothing older than 60 days");};
$("dbgCopy").onclick=async()=>{const r=await copyText($("dbgOut").textContent);toast(r?"Copied":"Clipboard blocked");};
$("dbgLog").onclick=async()=>{const r=await api().open_file("log");if(r&&r.error)toast(r.error);};
$("dbgCfg").onclick=async()=>{const r=await api().open_file("config");if(r&&r.error)toast(r.error);};
$("dbgWipe").onclick=()=>dbg("Ready.");
$("cfgOpen").onclick=async()=>{const r=await api().open_file("config");if(r&&r.error)toast(r.error);};
$("resetBtn").onclick=async()=>{
  if(!confirm("Reset all settings to defaults?\nHistory, profiles and item selections are kept."))return;
  const r=await api().reset_defaults();
  if(r.ok){info=r.info;$("uAmt").value=info.min_unique;$("gAmt").value=info.min_gear;
    $("outBase").value=info.output_base;$("bakCount").value=info.backup_count;
    $("baseQ").value=info.base_quality;$("baseL").value=info.base_min_level;
    $("regenSel").value=String(info.auto_regen_hours||0);armRegen();
    $("botFolderLbl").textContent=info.bot_folder||"not set";
    $("fltDirLbl").textContent=info.poe2_filter_dir||"not set";
    uEx();gEx();toast("Settings reset to defaults");}};
$("leagueRefresh").onclick=async()=>{
  const ls=await api().leagues();if(ls.error)return toast("✗ "+ls.error);
  const sel=$("league"),cur=sel.value;sel.innerHTML="";
  for(const l of ls){const o=document.createElement("option");o.value=l.name;o.textContent=l.display;sel.appendChild(o);}
  if(cur)sel.value=cur;toast("League list refreshed");};
document.addEventListener("keydown",e=>{
  if(e.ctrlKey&&e.key.toLowerCase()==="r"){e.preventDefault();$("leagueRefresh").click();}});

/* ── preview ── */
let prevLines=[],pvSections=[],pvSection=null,pvFilter="all",pvValMap={};
function parseSections(){
  pvSections=[];let cur=null;
  const bar=l=>/^\/{10,}$/.test(l.trim());
  const blank=l=>/^\/\/\s+\/\/$/.test(l);
  for(let i=0;i<prevLines.length;i++){
    const l=prevLines[i];
    // a header title line: "//   TITLE   //" directly under a slash border,
    // or under border + spacer line (the big banner style)
    const under=i>0&&(bar(prevLines[i-1])||(blank(prevLines[i-1])&&i>1&&bar(prevLines[i-2])));
    if(l.startsWith("//")&&l.endsWith("//")&&l.length>8&&under){
      const t=l.slice(2,-2).trim();
      if(t&&!/^─/.test(t)){cur={title:t,start:i,active:0,skip:0};pvSections.push(cur);continue;}}
    if(cur&&l.includes("[StashItem]")){l.startsWith("//")?cur.skip++:cur.active++;}}}
function pvLineOK(l){
  const isRule=l.includes("[StashItem]");
  switch(pvFilter){
    case "active":return isRule&&!l.startsWith("//");
    case "skip":return isRule&&l.startsWith("//");
    case "uniq":return isRule&&(l.includes("[UniqueName]")||l.includes('[Rarity] == "Unique"'));
    case "base":return isRule&&(l.includes("[Quality]")||l.includes("[Sockets]")||l.includes('[Rarity] == "Normal"'));
    default:return true;}}
async function loadPreview(){
  prevLines=await api().preview();parseSections();
  const v=await api().validation();
  pvValMap={};
  for(const m of v.errors){const n=parseInt(m.match(/Line (\d+)/)?.[1]);if(n)pvValMap[n]=["err",m];}
  for(const m of v.warnings){const n=parseInt(m.match(/Line (\d+)/)?.[1]);if(n)pvValMap[n]=pvValMap[n]||["warn",m];}
  const b=$("valBanner");
  if(v.errors.length){b.textContent=`⚠ ${v.errors.length} validation errors — marked ⚠ inline below`;b.classList.add("on");}
  else b.classList.remove("on");
  $("pvVal").textContent=v.errors.length?v.errors.length+" ✗":(v.warnings.length?v.warnings.length+" ⚠":"✓");
  renderPvNav();renderPreview();}
function renderPvNav(){
  const n=$("pvNav");
  if(!pvSections.length){n.innerHTML="";return;}
  n.innerHTML=`<div class="nav-btn${pvSection===null?" on":""}" data-s="">All sections</div>`+
    pvSections.map((s,i)=>`<div class="nav-btn${pvSection===i?" on":""}" data-s="${i}"
      style="font-size:12.5px;padding:7px 10px">${s.title.length>20?s.title.slice(0,20)+"…":s.title}
      <span style="margin-left:auto;font-size:10.5px;color:var(--dim)">${s.active}</span></div>`).join("");
  n.querySelectorAll(".nav-btn").forEach(b=>b.onclick=()=>{
    pvSection=b.dataset.s===""?null:parseInt(b.dataset.s);renderPvNav();renderPreview();});}
function pvVisible(){
  const q=($("prevFilter").value||"").toLowerCase();
  let lo=0,hi=prevLines.length;
  if(pvSection!==null&&pvSections[pvSection]){
    lo=pvSections[pvSection].start-2;
    hi=pvSection+1<pvSections.length?pvSections[pvSection+1].start-2:prevLines.length;}
  const shown=[];
  for(let i=Math.max(0,lo);i<hi;i++){
    const l=prevLines[i];
    if(q&&!l.toLowerCase().includes(q))continue;
    if(!pvLineOK(l))continue;
    shown.push([i+1,l]);}
  return shown;}
function renderPreview(){
  let a=0,c=0;
  const shown=pvVisible();
  const html=shown.slice(0,6000).map(([n,l])=>{
    let e=l.replace(/&/g,"&amp;").replace(/</g,"&lt;");
    const vm=pvValMap[n];
    if(vm)e=`<span style="color:${vm[0]==="err"?"var(--err)":"var(--warn)"}" title="${vm[1].replace(/"/g,"&quot;")}">⚠ ${e}</span>`;
    if(l.startsWith("////")||(l.startsWith("//")&&(l.match(/\/\//g)||[]).length>2))return`<span class="l-h">${e}</span>`;
    if(l.startsWith("//")){if(l.includes("[StashItem]"))c++;return vm?e:`<span class="l-c">${e}</span>`;}
    if(l.includes("[StashItem]")){a++;return vm?e:`<span class="l-a">${e}</span>`;}
    return e;}).join("\n");
  $("prevBox").innerHTML=html||"Nothing matches this filter.";
  const tot=prevLines.filter(l=>l.includes("[StashItem]")).length;
  const act=prevLines.filter(l=>l.includes("[StashItem]")&&!l.startsWith("//")).length;
  $("pvTotal").textContent=tot?tot.toLocaleString():"–";
  $("pvActive").textContent=tot?act.toLocaleString():"–";
  $("pvSkip").textContent=tot?(tot-act).toLocaleString():"–";
  $("pvSize").textContent=prevLines.length?Math.round(prevLines.join("\n").length/1024)+" KB":"–";}
document.querySelectorAll("#pvChips .chip").forEach(c=>c.onclick=()=>{
  document.querySelectorAll("#pvChips .chip").forEach(x=>x.classList.remove("on"));
  c.classList.add("on");pvFilter=c.dataset.f;renderPreview();});
$("prevCopy").onclick=async()=>{
  const all=pvSection===null&&pvFilter==="all"&&!($("prevFilter").value||"").trim();
  const lines=all?prevLines:pvVisible().map(([,l])=>l);
  const r=await copyText(lines.join("\n"));
  toast(r?(all?"Whole pickit copied":lines.length+" visible lines copied"):"Clipboard blocked");};
$("prevFilter").addEventListener("input",renderPreview);

/* ── settings ── */
function sw(id,key,cur){const el=$(id);el.classList.toggle("on",cur);
  el.onclick=async()=>{const on=!el.classList.contains("on");
    el.classList.toggle("on",on);await api().set_setting(key,on);toast("Saved");};}
function armRegen(){
  clearInterval(regenTimer);regenTimer=null;
  const h=parseInt($("regenSel").value)||0;
  if(h>0){regenTimer=setInterval(()=>{if(!running)doGenerate();},h*3600*1000);
    $("regenHint").textContent=`Armed — regenerates every ${h}h while this window is open.`;}
  else $("regenHint").textContent="Off — only generates when you click the button.";}
$("regenSel").onchange=async()=>{await api().set_setting("auto_regen_hours",parseInt($("regenSel").value));armRegen();toast("Saved");};
$("botBrowse").onclick=async()=>{const r=await api().browse_folder();
  if(r.path){$("botFolderLbl").textContent=r.path;await api().set_setting("bot_folder",r.path);toast("Saved");}};
$("baseQ").onchange=()=>{api().set_setting("base_quality",parseInt($("baseQ").value)||25);toast("Saved");};
$("baseL").onchange=()=>{api().set_setting("base_min_level",parseInt($("baseL").value)||82);toast("Saved");};
$("outBase").onchange=()=>{api().set_setting("output_base",$("outBase").value.trim()||"poe2_pickit");toast("Saved");};
$("bakCount").onchange=()=>{api().set_setting("backup_count",parseInt($("bakCount").value)||0);toast("Saved");};
$("fltBrowse").onclick=async()=>{const r=await api().browse_folder();
  if(r.path){$("fltDirLbl").textContent=r.path;await api().set_setting("poe2_filter_dir",r.path);toast("Saved");}};
$("updCheck").onclick=async()=>{$("updLbl").textContent="Checking…";
  const u=await api().check_update();
  $("updLbl").textContent=u.update?`⬆ v${u.version} available!`:"✓ You're up to date.";
  if(u.update)showUpdBanner(u);};
function showUpdBanner(u){const b=$("updBanner");
  b.textContent=`⬆ Update available: v${u.version} — click to open the download page`;
  b.classList.add("on");b.onclick=()=>api().open_url(u.url);}

/* ── "What is this?" explainers ── */
const WHATIS={
  gen:"<b>Generate</b> is the main button of the whole app. It downloads current market prices from poe.ninja for your league, keeps every item worth more than your minimum values, and writes the pickit file the bot reads. Run it whenever prices have moved — or let Auto-Regenerate in Settings do it for you.",
  eco:"<b>Economy</b> is your full catalog of what the bot can pick up, with live prices. Everything is ON by default. Click a row to exclude an item you don't want (e.g. cheap essences filling your stash). Double-click a category chip to turn a whole group on/off. The ▲▼ arrows show price movement. The <b>ALWAYS PICK</b> section holds the map-juice groups (tablets, splinters, wombgifts, exotic bases…) grabbed regardless of price — each group and each item can be switched off.",
  chance:"<b>Chance Bases</b> are white (Normal) items worth keeping ONLY to use Orb of Chance on, hoping they turn into a chase unique — e.g. keep white Heavy Belts because one can become a Headhunter. Turn off any target you don't care about.",
  craft:"<b>Craft Bases</b> are the best white items at high item level, kept as blank canvases to craft your own gear on. 'Min ilvl' is how high the item level must be — 82 gives access to the best crafting outcomes. If you never craft, turn this whole tab off.",
  exc:"<b>Exceptional Bases</b> are special versions of gear bases that can roll an <b>extra rune socket</b> — gloves with 2 instead of 1, and the same idea for helmets, weapons and armour. More sockets = more runes = the strongest version of that slot. Two things live here: picking up blank white ones to craft on or sell, and grabbing ANY unique that drops on one (the extra-socket copy of a unique beats the normal copy, whatever its price). The base list updates itself with game patches.",
  prev:"<b>Preview</b> shows the exact file the bot reads, after every Generate. Green lines = the bot picks it up, grey = below your value floor (skipped). Use the section list and filters to check that what you expect is actually in the file.",
  hist:"<b>History</b> logs every Generate run so you can see how your pickit evolves over the league — how many rules were active, what the top item was, and the Divine rate at the time.",
  set:"<b>Settings</b> connects the generator to your bot (folder + auto-copy), keeps the pickit fresh (Auto-Regenerate + tray mode), and controls output, backups and updates. Everything saves instantly.",
  dbg:"<b>Debug</b> is for when something's wrong: test whether poe.ninja is reachable, inspect the cache, and open the log to see what happened. You'll rarely need it."};
document.querySelectorAll(".page > h1").forEach(h=>{
  const key=h.parentElement.id.replace("p-","");
  if(!WHATIS[key])return;
  const btn=document.createElement("span");btn.className="whatis";btn.textContent="i";btn.title="What is this page?";
  const box=document.createElement("div");box.className="whatis-box";box.innerHTML=WHATIS[key];
  h.appendChild(btn);
  const sub=h.nextElementSibling;
  (sub&&sub.classList.contains("sub")?sub:h).insertAdjacentElement("afterend",box);
  btn.onclick=()=>box.classList.toggle("on");});

/* ── init ── */
async function init(){
  info=await api().app_info();
  $("ver").textContent="v"+info.version;
  setTheme(info.theme==="light"?"light":"dark");
  $("uAmt").value=info.min_unique||0;$("gAmt").value=info.min_gear||0;
  $("outBase").value=info.output_base;
  $("botFolderLbl").textContent=info.bot_folder||"not set";
  sw("swCopy","auto_copy",info.auto_copy);
  sw("swBases","include_bases",info.include_bases);
  sw("swUniqExc","unique_exceptional",info.unique_exceptional);
  sw("swFilter","copy_filter_to_game",info.copy_filter_to_game);
  sw("swTray","minimize_to_tray",info.minimize_to_tray);
  $("fltDirLbl").textContent=info.poe2_filter_dir||"not set";
  $("bakCount").value=info.backup_count;
  $("baseQ").value=info.base_quality;$("baseL").value=info.base_min_level;
  $("regenSel").value=String(info.auto_regen_hours||0);armRegen();
  loadProfiles();
  api().check_update().then(u=>{if(u.update)showUpdBanner(u);});
  if(info.config_warning)setTimeout(()=>alert(info.config_warning),600);
  if(info.auto_copy&&!info.bot_folder)toast("⚠ Auto-copy is ON but no bot folder is set");
  const ls=await api().leagues();const sel=$("league");sel.innerHTML="";
  if(ls.error){sel.innerHTML="<option>Could not load leagues</option>";logLine("✗ "+ls.error,"err");}
  else{for(const l of ls){const o=document.createElement("option");o.value=l.name;o.textContent=l.display;sel.appendChild(o);}
    if(info.league)sel.value=info.league;
    logLine("Loaded "+ls.length+" leagues.","ok");}
  const _rates=()=>api().chaos_ex(sel.value).then(r=>{chaosEx=r.ex||0;uEx();gEx();});
  sel.onchange=()=>{api().set_setting("league",sel.value);eco=null;_rates();};
  if(sel.value)_rates();
  uEx();gEx();}
window.addEventListener("pywebviewready",()=>init().catch(e=>{
  const t="STARTUP ERROR: "+(e&&(e.stack||e.message)||e);
  try{api().js_error(t);}catch(_){}
  try{logLine(t,"err");}catch(_){}
  try{toast(t.slice(0,120));}catch(_){}
}));
window.onerror=(m,src,line)=>{try{api().js_error("JS error: "+m+" @"+line);}catch(_){}
  try{toast(("JS error: "+m).slice(0,120));}catch(_){}};
setTimeout(()=>{if(typeof pywebview==="undefined"){document.title="BRIDGE MISSING";}},6000);
