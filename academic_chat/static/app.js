const $ = (s) => document.querySelector(s);
let user = null;
let version = 0;
let busy = false;

async function api(url, body) {
  const options = body === undefined ? {credentials:"same-origin",cache:"no-store"} : {method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)};
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "요청에 실패했습니다.");
  return data;
}
function entry() {
  version++; $("#chat").hidden = true; $("#compose-wrap").hidden = true; $("#entry").hidden = false;
  $("#mode").textContent = "시작 방식 선택"; $("#account").replaceChildren(); clear();
}
function clear() {
  version++;
  const welcome = $(".welcome");
  $("#messages").replaceChildren(welcome);
  welcome.hidden = false;
  $("#question").value = "";
}
function showChat() {
  $("#entry").hidden = true; $("#chat").hidden = false; $("#compose-wrap").hidden = false;
  $("#mode").textContent = user ? "학생 로그인 · 개인 맞춤 안내" : "일반 사용자 · 공개 학사 안내";
  const box = $("#account"); box.replaceChildren();
  if (user) {
    const name = document.createElement("span"); name.className="account-name"; name.textContent=`${user.name}님`;
    const button = document.createElement("button"); button.className="account-button"; button.textContent="로그아웃";
    button.onclick = async () => {try {await api("/api/logout",{}); user=null; entry();} catch(e) {alert(e.message);}};
    box.append(name,button);
  } else {
    const button = document.createElement("button"); button.className="account-button"; button.textContent="로그인"; button.onclick=()=>$("#dialog").showModal(); box.append(button);
  }
  $("#question").focus();
}
function addMessage(role, text, data={}) {
  $(".welcome").hidden = true;
  const row=document.createElement("article"); row.className=`message ${role}`;
  const icon=document.createElement("div"); icon.className="avatar"; icon.textContent=role==="assistant"?"✳":"나";
  const body=document.createElement("div"); body.className="message-body";
  const who=document.createElement("strong"); who.textContent=role==="assistant"?"캠퍼스톡":"나";
  const content=document.createElement("p"); content.textContent=text; body.append(who,content);
  if (data.sources?.length) {
    const list=document.createElement("div"); list.className="sources";
    for (const source of data.sources) {
      try {const url=new URL(source.url,location.origin); if (url.protocol!=="https:" && url.origin!==location.origin) continue; const link=document.createElement("a"); link.href=url.href; link.target="_blank"; link.rel="noopener noreferrer"; link.textContent=`↗ ${source.title}`; list.append(link);} catch {}
    }
    body.append(list);
  }
  if(data.login_required){const button=document.createElement("button"); button.className="inline"; button.textContent="로그인하기 →"; button.onclick=()=>$("#dialog").showModal(); body.append(button);}
  row.append(icon,body); $("#messages").append(row); row.scrollIntoView({block:"nearest",behavior:"smooth"});
}
async function send(message) {
  if (busy || !message.trim() || $("#chat").hidden) return;
  busy=true; $("#send").disabled=true; const start=version;
  try {
    const current=await api("/api/session"); if(start!==version)return;
    if(JSON.stringify(current.user)!==JSON.stringify(user)){user=current.user; clear(); showChat(); addMessage("assistant","로그인 상태가 변경되어 새 대화를 시작합니다.");}
    const active=version; addMessage("user",message.trim()); $("#question").value="";
    const result=await api("/api/chat",{message:message.trim()}); if(active!==version)return;
    if(JSON.stringify(result.user)!==JSON.stringify(user)){user=result.user;clear();showChat();addMessage("assistant","로그인 상태가 변경되었습니다. 질문을 다시 입력해 주세요.");return;}
    addMessage("assistant",result.answer,result);
  } catch(e) {if(start===version)addMessage("assistant",`요청을 처리하지 못했어요. ${e.message}`);}
  finally {busy=false;$("#send").disabled=false;if(!$("#chat").hidden)$("#question").focus();}
}
$("#guest").onclick=()=>{clear();showChat();};
$("#signin").onclick=()=>$("#dialog").showModal();
$("#close").onclick=()=>$("#dialog").close();
$("#reset").onclick=()=>{if(!$("#chat").hidden)clear();};
$("#form").onsubmit=(event)=>{event.preventDefault();send($("#question").value);};
$("#question").onkeydown=(event)=>{if(event.key==="Enter"&&!event.shiftKey&&!event.isComposing){event.preventDefault();send(event.target.value);}};
document.querySelectorAll("[data-q]").forEach(b=>b.onclick=()=>send(b.dataset.q));
$("#login").onsubmit=async event=>{event.preventDefault();$("#error").textContent="";try{const data=await api("/api/login",{username:$("#username").value,password:$("#password").value});user=data.user;$("#dialog").close();clear();showChat();}catch(e){$("#error").textContent=e.message;}};
async function checkSession(){try{const data=await api("/api/session");user=data.user;if(user){clear();showChat();}else entry();}catch{entry();addMessage("assistant","서버에 연결할 수 없습니다. 서버를 확인해 주세요.");}}
window.addEventListener("pageshow",e=>{if(e.persisted)checkSession();});
checkSession();
