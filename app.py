import os,re,time,wave,queue,sqlite3,threading,subprocess,collections
from pathlib import Path
from datetime import datetime,timezone
import numpy as np, sounddevice as sd, yaml, webrtcvad
from fastapi import FastAPI,UploadFile,File,HTTPException
from fastapi.responses import HTMLResponse,FileResponse
CFG=Path(os.getenv("SANKET_CONFIG","/etc/sanket-offline/config.yaml"))
def load(): 
 with CFG.open() as f:return yaml.safe_load(f)
cfg=load(); DATA=Path(cfg["storage"]["data_dir"]); REC=DATA/"recordings"; REC.mkdir(parents=True,exist_ok=True); DB=DATA/"events.sqlite3"
app=FastAPI(title="Sanket Offline V2"); frames=queue.Queue(maxsize=250); jobs=queue.Queue(); stop=threading.Event()
state={"audio":"starting","level":0.0,"recording":False,"model":"checking","relay_simulation":[False]*4,"last_error":""}
lock=threading.Lock()
def log(kind,msg,transcript="",recording=""):
 with sqlite3.connect(DB,timeout=15) as c:
  c.execute("CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts TEXT,kind TEXT,message TEXT,transcript TEXT,recording TEXT)")
  c.execute("INSERT INTO events(ts,kind,message,transcript,recording) VALUES(?,?,?,?,?)",(datetime.now(timezone.utc).isoformat(),kind,msg,transcript,recording))
def ready():
 t=cfg["transcription"];return Path(t["cli"]).is_file() and Path(t["model"]).is_file()
def transcribe(path):
 t=cfg["transcription"]; txt=Path(str(path)+".txt")
 try:
  p=subprocess.run([t["cli"],"-m",t["model"],"-f",str(path),"-l","en","-t",str(t.get("threads",4)),"--no-timestamps","-otxt"],capture_output=True,text=True,timeout=300)
  out=txt.read_text(errors="replace").strip() if txt.exists() else p.stdout.strip()
  if p.returncode:raise RuntimeError((p.stderr or p.stdout)[-1200:])
  return out
 finally:txt.unlink(missing_ok=True)
def match_rules(text,path):
 for r in cfg.get("keyword_rules",[]):
  phrase=str(r.get("phrase","")).strip(); ch=int(r.get("channel",0)); action=str(r.get("action","")).upper()
  if not r.get("enabled",True) or not phrase or ch not in (1,2,3,4) or action not in ("ON","OFF","TOGGLE"):continue
  if re.search(r"(?<!\\w)"+re.escape(phrase)+r"(?!\\w)",text,re.I):
   with lock:
    old=state["relay_simulation"][ch-1]; new=True if action=="ON" else False if action=="OFF" else not old
    state["relay_simulation"][ch-1]=new
   log("SIMULATED_RELAY_ACTION",f"Matched '{phrase}' → simulated channel {ch} {action}; state={'ON' if new else 'OFF'}",text,path.name)
def transcriber():
 while not stop.is_set():
  try:p=jobs.get(timeout=.5)
  except queue.Empty:continue
  try:
   log("TRANSCRIPTION_STARTED",f"Transcribing {p.name}",recording=p.name); text=transcribe(p)
   log("TRANSCRIPTION_COMPLETED","Local Whisper transcription completed",text,p.name); match_rules(text,p)
  except Exception as e:state["last_error"]=str(e);log("TRANSCRIPTION_FAILED",str(e),recording=p.name)
  finally:jobs.task_done()
def save(frames_in):
 if not frames_in:return
 p=REC/("rx-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f")+".wav")
 with wave.open(str(p),"wb") as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b"".join(frames_in))
 log("RECORDING_SAVED",f"Saved {p.name}",recording=p.name);jobs.put(p)
def segmenter():
 vad=webrtcvad.Vad(int(cfg["audio"].get("vad_aggressiveness",2))); pre=collections.deque(maxlen=50); hist=collections.deque(maxlen=3)
 active=[]; started=False; silence=0
 while not stop.is_set():
  try:f=frames.get(timeout=.5)
  except queue.Empty:continue
  voice=vad.is_speech(f,16000); hist.append(voice); state["level"]=round(float(np.sqrt(np.mean(np.frombuffer(f,dtype="<i2").astype(np.float32)**2)))/32768,4)
  if not started:
   pre.append(f)
   if sum(hist)>=2:started=True;active=list(pre);silence=0;state["recording"]=True;log("RECORDING_STARTED","VAD speech detected; 1-second pre-roll included")
  else:
   active.append(f)
   if voice:silence=0
   else:silence+=1
   if silence>=100:
    save(active[:-85] if len(active)>85 else active);active=[];pre.clear();hist.clear();silence=0;started=False;state["recording"]=False
  frames.task_done()
def capture():
 try:
  # CS202 USB interface runs natively at 48 kHz stereo. Convert to the
  # 16 kHz mono PCM format required by WebRTC VAD and Whisper.
  hardware_rate=int(cfg["audio"].get("hardware_sample_rate",48000))
  hardware_channels=int(cfg["audio"].get("hardware_channels",2))
  target_rate=int(cfg["audio"].get("sample_rate",16000))
  frame_ms=int(cfg["audio"].get("vad_frame_ms",20))
  input_block=int(hardware_rate*frame_ms/1000)
  output_block=int(target_rate*frame_ms/1000)
  if hardware_rate % target_rate:
   raise ValueError("Hardware sample rate must be an integer multiple of pipeline sample rate")
  from scipy.signal import resample_poly
  with sd.RawInputStream(device=cfg["audio"].get("device"),samplerate=hardware_rate,
                         channels=hardware_channels,dtype="int16",blocksize=input_block) as s:
   state["audio"]="connected"
   log("AUDIO_CONNECTED",f"USB audio input opened: {hardware_rate} Hz, {hardware_channels} channel(s); converted to {target_rate} Hz mono")
   while not stop.is_set():
    data,overflow=s.read(input_block)
    if overflow:log("AUDIO_OVERFLOW","Input overflow")
    samples=np.frombuffer(data,dtype="<i2")
    if samples.size != input_block*hardware_channels:
     log("AUDIO_BAD_BLOCK",f"Expected {input_block*hardware_channels} samples, received {samples.size}")
     continue
    if hardware_channels > 1:
     samples=samples.reshape(-1,hardware_channels).astype(np.int32).mean(axis=1)
    else:
     samples=samples.astype(np.int32)
    mono=np.clip(np.rint(samples),-32768,32767).astype(np.int16)
    converted=resample_poly(mono.astype(np.float32),target_rate,hardware_rate)
    converted=np.clip(np.rint(converted),-32768,32767).astype("<i2")
    if converted.size != output_block:
     log("AUDIO_BAD_BLOCK",f"Resampler produced {converted.size}; expected {output_block}")
     continue
    try:frames.put(converted.tobytes(),timeout=.2)
    except queue.Full:log("AUDIO_QUEUE_FULL","Frame queue full; frame dropped")
 except Exception as e:
  state["audio"]="error";state["last_error"]=str(e);log("AUDIO_ERROR",str(e))
@app.on_event("startup")
def startup():
 state["model"]="READY" if ready() else "NOT READY";log("BOOT","Sanket Offline V2 started")
 for fn in (segmenter,transcriber,capture):threading.Thread(target=fn,daemon=True).start()
@app.on_event("shutdown")
def shutdown():stop.set()
@app.get("/api/status")
def status():
 with lock: relays=list(state["relay_simulation"])
 return {**state,"relay_simulation":relays,"model_ready":ready()}
@app.get("/api/events")
def events(limit:int=100):
 with sqlite3.connect(DB) as c:
  c.row_factory=sqlite3.Row
  return [dict(x) for x in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(min(max(limit,1),500),))]
@app.get("/api/recordings")
def recordings():return [{"name":p.name,"bytes":p.stat().st_size} for p in sorted(REC.glob("*.wav"),reverse=True)[:200]]
@app.get("/api/recordings/{name}")
def recording(name:str):
 p=(REC/name).resolve()
 if p.parent!=REC.resolve() or not p.is_file():raise HTTPException(404)
 return FileResponse(p,media_type="audio/wav",filename=p.name)
@app.get("/api/config")
def get_config():return {"keyword_rules":cfg.get("keyword_rules",[])}
@app.put("/api/config")
def put_config(payload:dict):
 rules=payload.get("keyword_rules")
 if not isinstance(rules,list) or len(rules)>100:raise HTTPException(400,"Provide up to 100 rules")
 clean=[]
 for r in rules:
  phrase=str(r.get("phrase","")).strip();ch=int(r.get("channel",0));action=str(r.get("action","")).upper()
  if not phrase or len(phrase)>100 or ch not in (1,2,3,4) or action not in ("ON","OFF","TOGGLE"):raise HTTPException(400,"Each rule needs phrase, channel 1-4 and ON/OFF/TOGGLE")
  clean.append({"phrase":phrase,"channel":ch,"action":action,"enabled":bool(r.get("enabled",True))})
 cfg["keyword_rules"]=clean; tmp=CFG.with_suffix(".tmp");tmp.write_text(yaml.safe_dump(cfg,sort_keys=False));os.replace(tmp,CFG)
 log("CONFIG_UPDATED",f"Saved {len(clean)} keyword rules");return {"ok":True,"keyword_rules":clean}
@app.post("/api/test-model")
def test_model():
 if not ready():raise HTTPException(503,"Whisper executable/model missing")
 return {"ok":True,"message":"Whisper files found"}
@app.post("/api/transcribe")
async def upload(file:UploadFile=File(...)):
 if not file.filename.lower().endswith(".wav"):raise HTTPException(400,"Upload WAV")
 p=REC/("test-"+str(time.time_ns())+".wav");p.write_bytes(await file.read())
 try:
  text=transcribe(p);log("MANUAL_TEST_TRANSCRIPTION","Uploaded WAV transcription",text,p.name);return {"recording":p.name,"transcript":text}
 except Exception as e:raise HTTPException(500,str(e))
@app.get("/",response_class=HTMLResponse)
def home():return HTML
HTML="""<!doctype html><html><head><meta name=viewport content='width=device-width,initial-scale=1'><title>Sanket Offline V2</title><style>
body{margin:0;background:#101820;color:#edf2f4;font:15px system-ui}header{padding:18px 22px;background:#172733;border-bottom:3px solid #ef8b2c}.wrap{padding:16px;max-width:1150px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.card{background:#1b2b36;border:1px solid #334854;border-radius:12px;padding:15px;margin:12px 0}.v{font-size:21px;font-weight:700;margin-top:6px}.muted{color:#aab8c2;font-size:13px}button{background:#ef8b2c;color:#101820;border:0;border-radius:7px;padding:9px 12px;font-weight:700}input,select{background:#101820;color:#edf2f4;border:1px solid #526570;border-radius:6px;padding:8px;max-width:100%}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:8px;border-bottom:1px solid #334854}.rule{display:grid;grid-template-columns:2fr 100px 110px 85px;gap:8px;margin:8px 0}.relay{padding:10px;background:#263a45;border-radius:8px}@media(max-width:650px){.rule{grid-template-columns:1fr 1fr}}</style></head><body><header><b>📻 Sanket Offline V2</b><div class=muted>VAD · Local Whisper · Keyword rules · Four simulated outputs</div></header><main class=wrap>
<div class=grid><section class=card>Audio<div class=v id=audio>Starting</div></section><section class=card>Input level<div class=v id=level>0</div></section><section class=card>Whisper<div class=v id=model>Checking</div></section><section class=card>Recording<div class=v id=rec>No</div></section></div>
<section class=card><h3>Four-channel output simulator</h3><div class=grid id=relays></div><p class=muted>Software simulation only. No physical relay hardware is driven.</p></section>
<section class=card><h3>Keyword rules</h3><p class=muted>Map recognized phrases to simulated channel actions.</p><div id=rules></div><button onclick=addRule()>Add rule</button> <button onclick=saveRules()>Save rules</button> <span id=msg class=muted></span></section>
<section class=card><h3>Test Lab</h3><button onclick=testModel()>Check Whisper</button> <span id=testmsg class=muted></span><p><input type=file id=wav accept=.wav><button onclick=uploadWav()>Transcribe WAV</button></p></section>
<section class=card><h3>Recent events and transcripts</h3><div style=overflow:auto><table><thead><tr><th>Time</th><th>Event</th><th>Details / transcript</th><th>Recording</th></tr></thead><tbody id=rows></tbody></table></div></section>
<p class=muted>Keep port 8080 on a trusted private LAN. No login or HTTPS in this prototype. Verify transcripts.</p></main><script>
let rules=[];function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function draw(){document.getElementById('rules').innerHTML=rules.map((r,i)=>'<div class=rule><input placeholder="Phrase" value="'+esc(r.phrase)+'" onchange="rules['+i+'].phrase=this.value"><select onchange="rules['+i+'].channel=+this.value">'+[1,2,3,4].map(n=>'<option value='+n+' '+(r.channel==n?'selected':'')+'>Channel '+n+'</option>').join('')+'</select><select onchange="rules['+i+'].action=this.value">'+['ON','OFF','TOGGLE'].map(a=>'<option '+(r.action==a?'selected':'')+'>'+a+'</option>').join('')+'</select><button onclick="rules.splice('+i+',1);draw()">Remove</button></div>').join('')}
function addRule(){rules.push({phrase:'',channel:1,action:'ON',enabled:true});draw()}
async function saveRules(){let r=await fetch('/api/config',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({keyword_rules:rules})});let j=await r.json();msg.textContent=r.ok?'Saved '+j.keyword_rules.length+' rules':j.detail}
async function refresh(){try{let s=await(await fetch('/api/status')).json();audio.textContent=s.audio;level.textContent=s.level;model.textContent=s.model_ready?'READY':'NOT READY';rec.textContent=s.recording?'YES':'No';relays.innerHTML=s.relay_simulation.map((v,i)=>'<div class=relay>Channel '+(i+1)+'<div class=v>'+(v?'SIMULATED ON':'SIMULATED OFF')+'</div></div>').join('');let e=await(await fetch('/api/events?limit=80')).json();rows.innerHTML=e.map(x=>'<tr><td>'+new Date(x.ts).toLocaleTimeString()+'</td><td>'+esc(x.kind)+'</td><td>'+esc(x.message)+'<br>'+esc(x.transcript||'')+'</td><td>'+(x.recording?'<a href="/api/recordings/'+encodeURIComponent(x.recording)+'">'+esc(x.recording)+'</a>':'')+'</td></tr>').join('')}catch(e){audio.textContent='API error'}}
async function load(){rules=(await(await fetch('/api/config')).json()).keyword_rules||[];draw()}
async function testModel(){let r=await fetch('/api/test-model',{method:'POST'}),j=await r.json();testmsg.textContent=j.message||j.detail}
async function uploadWav(){let f=wav.files[0];if(!f){testmsg.textContent='Select WAV';return}let d=new FormData();d.append('file',f);let r=await fetch('/api/transcribe',{method:'POST',body:d}),j=await r.json();testmsg.textContent=j.transcript||j.detail}
load();refresh();setInterval(refresh,2000)</script></body></html>"""
