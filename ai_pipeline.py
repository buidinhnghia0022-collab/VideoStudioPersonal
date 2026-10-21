import json, urllib.request
from pathlib import Path

class AIError(RuntimeError): pass

def transcribe_whisper(audio_path,model_name='large-v3',device='cuda',compute_type='float16',progress=None):
    try:
        from faster_whisper import WhisperModel
    except Exception as e: raise AIError('Faster-Whisper chưa sẵn sàng: '+str(e))
    try:
        model=WhisperModel(model_name,device=device,compute_type=compute_type)
    except Exception:
        model=WhisperModel(model_name,device='cpu',compute_type='int8')
    segments,info=model.transcribe(str(audio_path),language='zh',vad_filter=True,beam_size=5)
    out=[]
    for i,s in enumerate(segments):
        out.append({'start':float(s.start),'end':float(s.end),'text':s.text.strip()})
        if progress and i%10==0: progress(i)
    return out

def ollama_available(base='http://127.0.0.1:11434'):
    try:
        with urllib.request.urlopen(base+'/api/tags',timeout=2) as r: return r.status==200
    except: return False

def translate_ollama(text,model='qwen2.5:7b',base='http://127.0.0.1:11434'):
    prompt=('Dịch lời thoại tiếng Trung sau sang tiếng Việt tự nhiên để lồng tiếng phim. Giữ nguyên ý, tên riêng và sắc thái. '
            'Không giải thích, chỉ trả về bản dịch tiếng Việt. Câu dịch nên gọn để khớp thời lượng.\n\n'+text)
    data=json.dumps({'model':model,'prompt':prompt,'stream':False,'options':{'temperature':0.2}},ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(base+'/api/generate',data=data,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=180) as r: return json.loads(r.read().decode('utf-8')).get('response','').strip()
    except Exception as e: raise AIError('Không gọi được AI dịch local: '+str(e))

def translate_segments(segments,model='qwen2.5:7b',progress=None):
    total=len(segments); out=[]
    for i,s in enumerate(segments):
        x=dict(s); x['text_vi']=translate_ollama(s['text'],model=model); out.append(x)
        if progress: progress(int((i+1)*100/max(1,total)))
    return out

def save_segments(segments,path):
    Path(path).write_text(json.dumps(segments,ensure_ascii=False,indent=2),encoding='utf-8')

def load_segments(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
