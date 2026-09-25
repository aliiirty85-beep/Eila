const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

test('dashboard receives unsolicited messages, retries ACK, and recovers after disconnect',async()=>{
  const nodes=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',checked:false,addEventListener(){}});return nodes.get(id)};
  const storage=new Map();let offline=true,ackFails=true,deliveries=0,acks=0;
  const sandbox={document:{getElementById:node},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
    crypto:{randomUUID:()=> 'test'},setInterval(){},window:{},
    fetch:async(path)=>{
      if(path==='/api/state')return {ok:true,json:async()=>({})};
      if(offline)throw new Error('offline');
      if(path.endsWith('/ack')){acks++;return {ok:!ackFails,status:503,json:async()=>({ok:true})}}
      deliveries++;return {ok:true,json:async()=>({commands:[{id:1,kind:'notify',payload:{text:'Eila initiated this'}}]})};
    }};
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync('app/static/app.js','utf8'),sandbox);
  await new Promise(setImmediate);
  assert.equal(node('notice').textContent,'');
  offline=false;
  await sandbox.pollCommands();
  assert.equal(node('notice').textContent,'Eila initiated this');
  assert.equal(acks,1);
  node('notice').textContent='Already read';ackFails=false;
  await sandbox.pollCommands();
  assert.equal(acks,2);assert.equal(deliveries,2);
  assert.equal(node('notice').textContent,'Already read');
  assert.equal(storage.get('eila.dashboardId'),'dashboard-test');
});
