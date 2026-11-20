// موقع «الباحث» — النسخة المستقلة. لا يعتمد على أي خدمة خارجية.
// الإعلانات تأتي من events.js، واختيارات الزائر والإعلانات التي يضيفها تُحفظ في متصفحه.
(function () {
const FIELDS=["فلسفة","دراسات إسلامية","لغة عربية وأدب","لسانيات وحوسبة لغوية","ترجمة","تاريخ","علم اجتماع","أنثروبولوجيا","دراسات الشرق الأوسط","مكتبات ومعلومات","اقتصاد وإدارة","تربية","فيزياء","كيمياء","أحياء","طب وعلوم صحية","هندسة","رياضيات وحاسوب"];
const KINDS=["مؤتمر","جائزة","مسابقة","منحة","مدرسة صيفية/شتوية"];
const STAGES=[["announced","الإعلان","--grey"],["abstract","تسليم الملخصات","--lapis"],["paper","تسليم البحث","--verm"],["notify","القبول / النتائج","--gold"],["start","بدء الانعقاد","--evt"],["end","نهاية الانعقاد","--evt"]];
const MONTHS=["يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"];
const WD=["س","ح","ن","ث","ر","خ","ج"];
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeUrl=u=>/^https?:\/\//i.test(u||"")?u:"";
const today=new Date();today.setHours(0,0,0,0);
const key=d=>d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
const todayKey=key(today);
const parse=s=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(s||""))return null;const[y,m,d]=s.split("-").map(Number);return new Date(y,m-1,d)};
const days=s=>{const d=parse(s);return d?Math.round((d-today)/864e5):null};
const fmt=s=>{const d=parse(s);return d?d.getDate()+" "+MONTHS[d.getMonth()]+" "+d.getFullYear():""};
const stageLabel=(ev,k)=>k==="paper"&&ev.kind!=="مؤتمر"?"آخر موعد للتقديم":k==="start"&&ev.kind==="جائزة"?"إعلان الفائزين / الحفل":STAGES.find(s=>s[0]===k)[1];

const LS_PREFS="albahith-prefs",LS_LOCAL="albahith-local-events";
const load=(k,d)=>{try{const v=JSON.parse(localStorage.getItem(k)||"null");return v??d}catch(e){return d}};
const store=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
let prefs={fields:[],watch:[],lead:7,...load(LS_PREFS,{})};
let localEvents=load(LS_LOCAL,[]);
const baseEvents=Array.isArray(window.EVENTS)?window.EVENTS:[];
let events=[];
function rebuild(){events=[...baseEvents,...localEvents.map(e=>({...e,local:true}))]}
rebuild();
let year=today.getFullYear(),selDay=null,soundOn=false,actx=null;const notified=new Set();

function evDates(ev){return STAGES.filter(s=>ev.dates&&parse(ev.dates[s[0]])).map(s=>({k:s[0],v:ev.dates[s[0]],c:s[2]}))}
function nextDate(ev){const f=evDates(ev).filter(x=>days(x.v)>=0).sort((a,b)=>a.v<b.v?-1:1);return f[0]||null}
function lastDate(ev){const a=evDates(ev).map(x=>x.v).sort();return a[a.length-1]||""}
function isPast(ev){const l=lastDate(ev);return l?days(l)<0:false}
function visible(){
  const q=$("q").value.trim(),k=$("kindF").value,past=$("showPast").checked;
  return events.filter(ev=>(!prefs.fields.length||(ev.fields||[]).some(f=>prefs.fields.includes(f)))
    &&(!k||ev.kind===k)&&(past||!isPast(ev))
    &&(!q||[ev.title,ev.org,ev.place].join(" ").includes(q)))
   .sort((a,b)=>{const na=nextDate(a),nb=nextDate(b);if(na&&nb)return na.v<nb.v?-1:1;if(na)return -1;if(nb)return 1;return lastDate(a)<lastDate(b)?1:-1});
}
function plusDay(s){const n=parse(s);n.setDate(n.getDate()+1);return key(n).replace(/-/g,"")}
function gcal(ev,x){return "https://calendar.google.com/calendar/render?action=TEMPLATE&text="+encodeURIComponent(stageLabel(ev,x.k)+": "+ev.title)+"&dates="+x.v.replace(/-/g,"")+"/"+plusDay(x.v)+"&details="+encodeURIComponent((ev.org||"")+"\n"+(safeUrl(ev.url)||""))}

function renderChips(){
  $("fieldChips").innerHTML=FIELDS.map(f=>`<button type="button" class="chip" aria-pressed="${prefs.fields.includes(f)}" data-f="${esc(f)}">${esc(f)}</button>`).join("")+
   `<button type="button" class="chip" id="clearF">${prefs.fields.length?"إلغاء التحديد":"كل المجالات"}</button>`;
}
function renderYear(){
  $("yLabel").textContent=year;
  const vis=visible(),map={};
  vis.forEach(ev=>evDates(ev).forEach(x=>{(map[x.v]=map[x.v]||[]).push({ev,x})}));
  vis.forEach(ev=>{const s=parse(ev.dates&&ev.dates.start),e=parse(ev.dates&&ev.dates.end);if(s&&e&&e>s){for(let d=new Date(s);d<=e;d.setDate(d.getDate()+1)){const k=key(d);map[k]=map[k]||[];if(!map[k].some(o=>o.ev===ev))map[k].push({ev,x:{k:"start",v:k,c:"--evt"}})}}});
  let h="";
  for(let m=0;m<12;m++){
    const first=new Date(year,m,1),n=new Date(year,m+1,0).getDate(),off=(first.getDay()+1)%7;
    let cnt=0,cells=WD.map(w=>`<span class="wd">${w}</span>`).join("");
    for(let i=0;i<off;i++)cells+=`<span class="d off"></span>`;
    for(let d=1;d<=n;d++){
      const k=key(new Date(year,m,d)),it=map[k]||[];
      if(it.length)cnt++;
      const evt=it.some(o=>o.x.c==="--evt"),cols=[...new Set(it.filter(o=>o.x.c!=="--evt").map(o=>o.x.c))];
      const cls=["d",it.length?"has":"",evt?"evt":"",k===todayKey?"today":"",k===selDay?"sel":""].join(" ");
      cells+=it.length?`<button type="button" class="${cls}" data-day="${k}" aria-label="${d} ${MONTHS[m]}: ${it.length} موعد">${d}<span class="dots">${cols.map(c=>`<i style="background:var(${c})"></i>`).join("")}</span></button>`
        :`<span class="${cls}">${d}</span>`;
    }
    h+=`<div class="month"><h3>${MONTHS[m]}<small>${cnt?cnt+" يوم فيه مواعيد":""}</small></h3><div class="grid">${cells}</div></div>`;
  }
  $("months").innerHTML=h;
  if(selDay){const it=map[selDay]||[];$("dayinfo").innerHTML=`<strong>${fmt(selDay)}</strong>`+(it.length?`<ul>${it.map(o=>`<li><b>${esc(stageLabel(o.ev,o.x.k))}</b>: ${safeUrl(o.ev.url)?`<a href="${esc(safeUrl(o.ev.url))}" target="_blank" rel="noopener">${esc(o.ev.title)}</a>`:esc(o.ev.title)}</li>`).join("")}</ul>`:`<p class="note">لا مواعيد في هذا اليوم ضمن اختياراتك.</p>`)}
}
function renderCards(){
  const vis=visible();
  $("cards").innerHTML=vis.map(ev=>{
    const nd=nextDate(ev),w=prefs.watch.includes(ev.id),u=safeUrl(ev.url);
    return `<article class="card ${isPast(ev)?"past":""}">
      <header><div><h3>${esc(ev.title)}</h3><p class="org">${esc(ev.org||"")}${ev.place?" · "+esc(ev.place):""}</p></div><span class="kind">${esc(ev.kind||"")}</span></header>
      <ul class="tl">${evDates(ev).map(x=>{const dd=days(x.v);return `<li class="${dd<0?"done":""}"><i style="background:var(${x.c})"></i><span>${esc(stageLabel(ev,x.k))} <time>${fmt(x.v)}</time></span>${dd>=0?`<a class="cal" href="${esc(gcal(ev,x))}" target="_blank" rel="noopener">أضف للتقويم</a>`:"<span></span>"}</li>`}).join("")||`<li><span></span><span class="note">لم تُعلن المواعيد بعد</span><span></span></li>`}</ul>
      ${nd?`<p class="note"><b style="color:var(--ink)">القادم: ${esc(stageLabel(ev,nd.k))} ${days(nd.v)===0?"اليوم":"بعد "+days(nd.v)+" يومًا"}</b></p>`:""}
      ${ev.note?`<p class="note">${esc(ev.note)}</p>`:""}
      <div class="tags">${(ev.fields||[]).map(f=>`<span>${esc(f)}</span>`).join("")}${ev.local?`<span>أضفتِه في هذا المتصفح</span>`:""}</div>
      <div class="acts">${u?`<a class="go" href="${esc(u)}" target="_blank" rel="noopener">صفحة الإعلان ↖</a>`:""}
        <button type="button" class="watch" data-w="${esc(ev.id)}" aria-pressed="${w}">${w?"المنبّه مفعّل":"ذكّرني"}</button>
        ${ev.local?`<button type="button" data-del="${esc(ev.id)}">حذف</button>`:""}</div>
    </article>`}).join("");
  const e=$("empty");
  if(!events.length){e.hidden=false;e.textContent="لا إعلانات بعد. تأكدي أن ملف events.js موجود بجانب index.html."}
  else if(!vis.length){e.hidden=false;e.textContent="لا إعلانات تطابق اختياراتك. جرّبي توسيع المجالات أو إظهار ما انتهى."}
  else e.hidden=true;
  $("status").textContent=events.length+" إعلانًا"+(localEvents.length?" (منها "+localEvents.length+" أضفتِها في هذا المتصفح)":"");
}
function pool(){return prefs.watch.length?events.filter(ev=>prefs.watch.includes(ev.id)):visible()}
function alarmItems(){
  const out=[];pool().forEach(ev=>evDates(ev).forEach(x=>{const d=days(x.v);if(d>=0&&d<=prefs.lead&&x.k!=="end")out.push({ev,x,d})}));
  return out.sort((a,b)=>a.d-b.d);
}
// في المنبّه: «بدء + اسم المؤتمر» بدل «بدء الانعقاد: الاسم»
function alarmText(ev,k){return k==="start"&&ev.kind!=="جائزة"?"بدء "+ev.title:stageLabel(ev,k)+": "+ev.title}
function renderAlarm(){
  const it=alarmItems();
  $("alarmTitle").textContent=prefs.watch.length?"المنبّه: الإعلانات التي اخترتِ متابعتها":"المنبّه: مواعيد مجالاتك القريبة";
  $("alarmList").innerHTML=it.length?it.slice(0,8).map(o=>`<li><b>${o.d===0?"اليوم":"بعد "+o.d+" يوم"}</b> · ${esc(alarmText(o.ev,o.x.k))}</li>`).join(""):`<li>لا مواعيد خلال ${prefs.lead===1?"يوم":prefs.lead+" أيام"}.</li>`;
  $("lead").value=String(prefs.lead);
}
function renderAll(){renderChips();renderYear();renderCards();renderAlarm()}

function toast(t){const el=$("toast");el.textContent=t;el.classList.add("on");clearTimeout(toast.t);toast.t=setTimeout(()=>el.classList.remove("on"),6000)}
function chime(){if(!actx)return;const o=actx.createOscillator(),g=actx.createGain();o.frequency.value=880;o.connect(g);g.connect(actx.destination);g.gain.setValueAtTime(.001,actx.currentTime);g.gain.exponentialRampToValueAtTime(.3,actx.currentTime+.05);g.gain.exponentialRampToValueAtTime(.001,actx.currentTime+1.2);o.start();o.stop(actx.currentTime+1.3)}
function checkAlarm(){if(!soundOn)return;const it=alarmItems().filter(o=>!notified.has(o.ev.id+o.x.k));if(!it.length)return;
  it.forEach(o=>notified.add(o.ev.id+o.x.k));chime();
  const msg=alarmText(it[0].ev,it[0].x.k)+(it[0].d===0?" اليوم":" بعد "+it[0].d+" يوم")+(it.length>1?" (+"+(it.length-1)+")":"");
  toast("تذكير: "+msg);
  try{if("Notification" in window&&Notification.permission==="granted")new Notification("الباحث: تذكير",{body:msg,icon:"logo.svg",lang:"ar",dir:"rtl"})}catch(e){}}
function savePrefs(){store(LS_PREFS,prefs)}
function download(name,text,type){const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500)}

function ics(){
  const t=s=>String(s).replace(/[\\;,]/g,m=>"\\"+m).replace(/\n/g,"\\n");
  const L=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//albahith//ar","CALSCALE:GREGORIAN","X-WR-CALNAME:الباحث"];
  pool().forEach(ev=>evDates(ev).filter(x=>days(x.v)>=0&&x.k!=="end").forEach(x=>{
    L.push("BEGIN:VEVENT","UID:"+ev.id+"-"+x.k+"@albahith","DTSTAMP:"+todayKey.replace(/-/g,"")+"T000000Z","DTSTART;VALUE=DATE:"+x.v.replace(/-/g,""),"DTEND;VALUE=DATE:"+plusDay(x.v),"SUMMARY:"+t(stageLabel(ev,x.k)+": "+ev.title),"DESCRIPTION:"+t((ev.org||"")+" "+(safeUrl(ev.url)||"")));
    if(safeUrl(ev.url))L.push("URL:"+safeUrl(ev.url));
    L.push("BEGIN:VALARM","ACTION:DISPLAY","DESCRIPTION:"+t(ev.title),"TRIGGER:-P"+prefs.lead+"D","END:VALARM","END:VEVENT")}));
  L.push("END:VCALENDAR");return L.join("\r\n");
}
function eventsFile(){
  const all=events.map(({local,...e})=>e);
  return "// ملف الإعلانات لموقع «الباحث» — صُدّر من الموقع في "+todayKey+"\n// راجعي دليل README.md لطريقة التعديل.\nwindow.EVENTS = [\n"+all.map(e=>"  "+JSON.stringify(e)).join(",\n")+"\n];\n";
}

/* events */
$("fieldChips").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;
  if(b.id==="clearF")prefs.fields=[];else{const f=b.dataset.f;prefs.fields=prefs.fields.includes(f)?prefs.fields.filter(x=>x!==f):[...prefs.fields,f]}
  savePrefs();renderAll()});
["q","kindF","showPast"].forEach(id=>$(id).addEventListener("input",()=>{renderYear();renderCards();renderAlarm()}));
$("prevY").onclick=()=>{year--;renderYear()};$("nextY").onclick=()=>{year++;renderYear()};
$("months").addEventListener("click",e=>{const b=e.target.closest("[data-day]");if(!b)return;selDay=b.dataset.day;renderYear()});
$("cards").addEventListener("click",e=>{const w=e.target.closest("[data-w]");if(w){const id=w.dataset.w;prefs.watch=prefs.watch.includes(id)?prefs.watch.filter(x=>x!==id):[...prefs.watch,id];savePrefs();renderCards();renderAlarm();return}
  const d=e.target.closest("[data-del]");if(d){if(d.dataset.confirm!=="1"){d.dataset.confirm="1";d.textContent="اضغطي مجددًا للتأكيد";return}
    localEvents=localEvents.filter(x=>x.id!==d.dataset.del);store(LS_LOCAL,localEvents);rebuild();renderAll()}});
$("lead").onchange=e=>{prefs.lead=Number(e.target.value);savePrefs();renderAlarm()};
$("sound").onclick=()=>{soundOn=!soundOn;$("sound").setAttribute("aria-pressed",soundOn);$("sound").textContent=soundOn?"التنبيه يعمل":"تشغيل التنبيه";
  if(soundOn){try{actx=actx||new (window.AudioContext||window.webkitAudioContext)();actx.resume&&actx.resume()}catch(e){}
    try{if("Notification" in window&&Notification.permission==="default")Notification.requestPermission()}catch(e){}
    notified.clear();chime();toast("سينبّهك الموقع بصوت وإشعار ما دامت الصفحة مفتوحة.");setTimeout(checkAlarm,1500)}};
setInterval(checkAlarm,60000);
$("dlIcs").onclick=()=>{download("albahith.ics",ics(),"text/calendar");toast("نزل ملف التقويم. افتحيه ليضيف المواعيد إلى تقويمك مع تنبيه قبل كل موعد.")};

KINDS.forEach(k=>{$("kindF").insertAdjacentHTML("beforeend",`<option>${k}</option>`);$("kindSel").insertAdjacentHTML("beforeend",`<option>${k}</option>`)});
$("fieldBoxes").insertAdjacentHTML("beforeend",FIELDS.map(f=>`<label><input type="checkbox" name="fields" value="${esc(f)}">${esc(f)}</label>`).join(""));
$("addForm").addEventListener("submit",e=>{e.preventDefault();const fd=new FormData(e.target);
  const dates={};STAGES.forEach(s=>{const v=fd.get(s[0]);if(v)dates[s[0]]=v});
  const doc={id:"local-"+Date.now().toString(36),title:fd.get("title").trim(),org:fd.get("org").trim(),place:fd.get("place").trim(),kind:fd.get("kind"),url:fd.get("url").trim(),fields:fd.getAll("fields"),dates,note:fd.get("note").trim()};
  if(!safeUrl(doc.url)){$("addMsg").textContent="الرابط يجب أن يبدأ بـ https://";return}
  localEvents=[...localEvents,doc];store(LS_LOCAL,localEvents);rebuild();e.target.reset();renderAll();
  $("addMsg").textContent="حُفظ الإعلان في هذا المتصفح. لينشر لكل الزوار: نزّلي ملف الإعلانات المحدّث وارفعيه مكان القديم."});
$("dlEvents").onclick=()=>download("events.js",eventsFile(),"text/javascript");

renderAll();
})();
