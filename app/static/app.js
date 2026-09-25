const $=id=>document.getElementById(id);let current=null;
async function api(path,opt={}){const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opt});if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json()}
async function refresh(){try{const s=await api('/api/state');current=s.microgoal;$('status').textContent=s.session?.session_id?'جلسه فعال':'آماده';$('theme').textContent='Theme: '+(s.theme||'—');$('phase').textContent='Phase: '+(s.phase||'—');$('pulse').textContent='Pulse: '+(s.learning_pulse?.score??'—');$('attention').textContent=Math.round(s.attention_score??0);$('risk').textContent=s.risk?.level||'—';$('flow').textContent=s.flow?'ON':'OFF';$('gaze').textContent=s.gaze?.zone||'—';$('intervention').textContent=s.last_intervention||'';$('future5').textContent='۵ ثانیه: '+(s.future?.now_5s||'—');$('future60').textContent='۱ دقیقه: '+(s.future?.next_60s||'—');$('future10').textContent='۱۰ دقیقه: '+(s.future?.round_10m||'—');$('returnState').textContent=s.return_contract?'قرارداد بازگشت فعال':'—';if(current){$('instruction').textContent=current.display_instruction||current.instruction;$('salience').textContent=current.salience||'';$('question').textContent=current.question||''}else{$('instruction').textContent=s.session?.session_id?'ایلا منتظر سیگنال/ماموریت بعدی است.':'ایلا منتظر شروع جلسه است.';$('salience').textContent='';$('question').textContent=''}}catch(e){$('status').textContent='ارتباط قطع'}}
$('start').onclick=async()=>{await api('/api/session/start',{method:'POST',body:JSON.stringify({goal:$('goal').value,plan:$('plan').value})});refresh()};
$('stop').onclick=async()=>{const x=await api('/api/session/stop',{method:'POST',body:'{}'});$('feedback').textContent=x.summary?.text||'';refresh()};
$('done').onclick=async()=>{const x=await api('/api/micro/feedback',{method:'POST',body:JSON.stringify({answer:$('answer').value,status:'done',confidence:.7})});$('answer').value='';$('feedback').textContent=x.consequence||x.reason||'';refresh()};
$('fail').onclick=async()=>{const x=await api('/api/micro/feedback',{method:'POST',body:JSON.stringify({answer:$('answer').value,status:'stuck',confidence:.5})});$('feedback').textContent=x.consequence||x.reason||'';refresh()};
$('answer').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();$('done').click()}});
$('returnStart').onclick=async()=>{await api('/api/return/start',{method:'POST',body:JSON.stringify({text:$('returnText').value,minutes:Number($('returnMin').value)})});refresh()};
$('returnAck').onclick=async()=>{await api('/api/return/ack',{method:'POST',body:JSON.stringify({})});refresh()};
$('chatSend').onclick=async()=>{const x=await api('/api/chat',{method:'POST',body:JSON.stringify({message:$('chatInput').value})});$('chatOut').textContent=x.text||''};
$('healthBtn').onclick=async()=>{$('health').textContent=JSON.stringify(await api('/api/health'),null,2)};
$('sourceSet').onclick=async()=>{const x=await api('/api/context/current',{method:'POST',body:JSON.stringify({kind:'text',title:$('sourceTitle').value,content:$('sourceText').value,ref:''})});$('sourceState').textContent=x.ok?'منبع فعال شد ✓':'ثبت نشد'};
setInterval(refresh,2000);refresh();

// The dashboard is a command consumer, just like the mobile companion.
const dashboardId=localStorage.getItem('eila.dashboardId')||('dashboard-'+crypto.randomUUID());
localStorage.setItem('eila.dashboardId',dashboardId);
let pollingCommands=false;
const displayedCommands=new Set();
async function pollCommands(){
  if(pollingCommands)return;
  pollingCommands=true;
  try{
    const base='/api/device/'+encodeURIComponent(dashboardId)+'/commands';
    const result=await api(base);
    for(const command of result.commands||[]){
      if(!displayedCommands.has(command.id)){
        const p=command.payload||{};
        if(['notify','vibrate','speak','feedback'].includes(command.kind)&&p.text){
          $('notice').textContent=p.text;
          if($('readNotices').checked&&'speechSynthesis' in window){
            const utterance=new SpeechSynthesisUtterance(p.text);utterance.lang='fa-IR';
            window.speechSynthesis.speak(utterance);
          }
        }
        displayedCommands.add(command.id);
        if(displayedCommands.size>200)displayedCommands.delete(displayedCommands.values().next().value);
      }
      await api(base+'/'+command.id+'/ack',{method:'POST',body:'{}'});
    }
  }catch(e){/* Keep unacknowledged commands for reconnection. */}
  finally{pollingCommands=false}
}
setInterval(pollCommands,2000);pollCommands();
