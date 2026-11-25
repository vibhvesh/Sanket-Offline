import os, json, time, wave, queue, sqlite3, threading, subprocess, tempfile, re
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import sounddevice as sd
import yaml
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

CFG = Path(os.getenv("SANKET_CONFIG", "/etc/sanket-offline/config.yaml"))
def load_cfg():
    with CFG.open() as f: return yaml.safe_load(f)
cfg = load_cfg()
DATA = Path(cfg["storage"]["data_dir"]); REC = DATA / "recordings"
DATA.mkdir(parents=True, exist_ok=True); REC.mkdir(parents=True, exist_ok=True)
DB = DATA / "events.sqlite3"
app = FastAPI(title="Sanket Offline")
audio_q = queue.Queue(maxsize=30)
state = {"audio":"starting", "transcription":"checking", "level":0.0, "recording":False, "relay":"SIMULATED / OFF", "last_error":""}
stop_event = threading.Event()

def db():
    c=sqlite3.connect(DB, timeout=10); c.row_factory=sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, message TEXT, transcript TEXT, recording TEXT)""")
    c.commit(); return c
def event(kind, message, transcript="", recording=""):
    with db() as c: c.execute("INSERT INTO events(ts,kind,message,transcript,recording) VALUES(?,?,?,?,?)",(datetime.now(timezone.utc).isoformat(),kind,message,transcript,recording))
def model_ok():
    t=cfg["transcription"]
    return Path(t["cli"]).exists() and Path(t["model"]).exists()
def transcribe(path):
    t=cfg["transcription"]; cmd=[t["cli"],"-m",t["model"],"-f",str(path),"-l","en","-t",str(t.get("threads",4)),"--no-timestamps","-otxt"]
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        txt=Path(str(path)+".txt")
        result=txt.read_text(errors="ignore").strip() if txt.exists() else p.stdout.strip()
        if p.returncode: raise RuntimeError((p.stderr or p.stdout)[-1200:])
        return result
    finally:
        Path(str(path)+".txt").unlink(missing_ok=True)
def process(path):
    event("TRANSCRIPTION_STARTED", f"Transcribing {path.name}", recording=path.name)
    try:
        text=transcribe(path)
        matches=[k for k in cfg["keywords"].get("phrases",[]) if re.search(r"(?<!\\w)"+re.escape(k)+r"(?!\\w)",text,re.I)]
        event("TRANSCRIPTION_COMPLETED", "Transcription complete", text, path.name)
        for k in matches: event("KEYWORD_DETECTED", f"Informational keyword match: {k}", text, path.name)
    except Exception as e:
        state["last_error"]=str(e); event("TRANSCRIPTION_FAILED",str(e),recording=path.name)
def worker():
    sr=int(cfg["audio"]["sample_rate"]); silence=float(cfg["audio"]["silence_seconds"]); threshold=float(cfg["audio"]["speech_threshold"])
    chunks=[]; quiet=0; active=False
    while not stop_event.is_set():
        try: data=audio_q.get(timeout=.5)
        except queue.Empty: continue
        rms=float(np.sqrt(np.mean(np.square(data.astype(np.float32))))); state["level"]=round(rms,4)
        if rms>threshold:
            active=True; quiet=0; chunks.append(data.copy())
        elif active:
            chunks.append(data.copy()); quiet+=len(data)/sr
            if quiet>=silence:
                pcm=np.concatenate(chunks); stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
                path=REC/f"rx-{stamp}.wav"
                with wave.open(str(path),"wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.astype("<i2").tobytes())
                state["recording"]=False; event("RECORDING_SAVED",f"Saved {path.name}",recording=path.name)
                threading.Thread(target=process,args=(path,),daemon=True).start()
                chunks=[]; quiet=0; active=False
        if active: state["recording"]=True
def capture():
    a=cfg["audio"]; sr=int(a["sample_rate"]); block=int(sr)
    try:
        with sd.InputStream(device=a.get("device"),samplerate=sr,channels=1,dtype="int16",blocksize=block) as stream:
            state["audio"]="connected"; event("USB_AUDIO_CONNECTED","Audio input stream opened")
            while not stop_event.is_set():
                data, overflow=stream.read(block)
                if overflow: event("AUDIO_OVERFLOW","Input overflow detected")
                try: audio_q.put_nowait(data[:,0].copy())
                except queue.Full: event("AUDIO_QUEUE_FULL","Audio processing queue full")
    except Exception as e:
        state["audio"]="error"; state["last_error"]=str(e); event("USB_AUDIO_ERROR",str(e))
@app.on_event("startup")
def startup():
    state["transcription"]="ready" if model_ok() else "model or whisper-cli missing"
    event("BOOT","Sanket Offline started")
    threading.Thread(target=worker,daemon=True).start()
    threading.Thread(target=capture,daemon=True).start()
@app.on_event("shutdown")
def shutdown(): stop_event.set()

@app.get("/api/status")
def status():
    return {**state,"model_ready":model_ok(),"model":cfg["transcription"]["model"],"audio_devices":str(sd.query_devices())}
@app.get("/api/events")
def events(limit:int=100):
    with db() as c: return [dict(x) for x in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(min(limit,500),))]
@app.get("/api/recordings")
def recordings():
    return [{"name":p.name,"bytes":p.stat().st_size} for p in sorted(REC.glob("*.wav"),reverse=True)[:100]]
@app.get("/api/recordings/{name}")
def recording(name:str):
    from fastapi.responses import FileResponse
    p=(REC/name).resolve()
    if p.parent!=REC.resolve() or not p.exists(): raise HTTPException(404)
    return FileResponse(p,media_type="audio/wav",filename=p.name)
@app.post("/api/transcribe")
async def upload(file:UploadFile=File(...)):
    if not file.filename.lower().endswith(".wav"): raise HTTPException(400,"Upload a WAV file")
    p=REC/("upload-"+str(int(time.time()))+".wav")
    p.write_bytes(await file.read())
    text=transcribe(p); event("TEST_TRANSCRIPTION",f"Manual test: {p.name}",text,p.name)
    return {"recording":p.name,"transcript":text}
@app.post("/api/test")
def test_model():
    if not model_ok(): raise HTTPException(503,"Whisper model or CLI is not installed")
    return {"ok":True,"message":"Whisper CLI and model files are present"}
@app.get("/",response_class=HTMLResponse)
def home():
    return HTML
HTML = """<!doctype html><html><head><meta name=viewport content='width=device-width,initial-scale=1'><title>Sanket Offline</title><style>
body{margin:0;background:#101820;color:#edf2f4;font:15px system-ui}header{padding:18px 22px;background:#172733;border-bottom:3px solid #ef8b2c}h1{margin:0;font-size:22px}small{color:#aab8c2}.wrap{padding:16px;max-width:1100px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.card{background:#1b2b36;border:1px solid #334854;border-radius:12px;padding:16px}.v{font-size:21px;font-weight:700;margin-top:8px}.warn{color:#ffbf69}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #334854;vertical-align:top}button{background:#ef8b2c;color:#101820;border:0;border-radius:8px;padding:10px 14px;font-weight:700}a{color:#ffb45f}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style></head><body><header><h1>📻 Sanket Offline</h1><small>Local audio · Whisper Base.en · Offline dashboard</small></header><main class=wrap>
<div class=grid><section class=card>Audio input<div class=v id=audio>Loading</div></section><section class=card>Input level<div class=v id=level>0.000</div></section><section class=card>Whisper model<div class=v id=model>Checking</div><small id=modelpath></small></section><section class=card>Recording<div class=v id=rec>No</div></section><section class=card>Relay output<div class=v>SIMULATED / OFF</div><small>Physical relay actuation is not implemented</small></section></div>
<section class=card style="margin-top:12px"><h3>Test Lab</h3><button onclick="test()">Check Whisper model</button> <span id=testmsg></span><p><input type=file id=wav accept=.wav><button onclick="upload()">Transcribe WAV</button></p></section>
<section class=card style="margin-top:12px"><h3>Recent activity and transcripts</h3><div style="overflow:auto"><table><thead><tr><th>Time</th><th>Event</th><th>Details / transcript</th><th>Recording</th></tr></thead><tbody id=rows></tbody></table></div></section>
<p class=warn>Keyword detections are informational only. Verify every transcript; speech recognition can be wrong.</p></main><script>
async function refresh(){try{let s=await(await fetch('/api/status')).json();audio.textContent=s.audio;level.textContent=s.level;model.textContent=s.model_ready?'READY':'NOT READY';modelpath.textContent=s.model;rec.textContent=s.recording?'YES':'No';let e=await(await fetch('/api/events?limit=80')).json();rows.innerHTML=e.map(x=>'<tr><td>'+new Date(x.ts).toLocaleTimeString()+'</td><td>'+x.kind+'</td><td>'+esc(x.message)+'<br>'+esc(x.transcript||'')+'</td><td>'+(x.recording?'<a href="/api/recordings/'+encodeURIComponent(x.recording)+'">'+esc(x.recording)+'</a>':'')+'</td></tr>').join('')}catch(e){audio.textContent='Dashboard API error'}}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
async function test(){let r=await fetch('/api/test',{method:'POST'});testmsg.textContent=(await r.json()).message||'Model check failed'}
async function upload(){let f=wav.files[0];if(!f){testmsg.textContent='Choose a WAV file first';return}let d=new FormData();d.append('file',f);let r=await fetch('/api/transcribe',{method:'POST',body:d});let j=await r.json();testmsg.textContent=j.transcript||j.detail||'Complete'}
refresh();setInterval(refresh,2500)</script></body></html>"""
