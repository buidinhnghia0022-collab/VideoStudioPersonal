import json, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime

BASE=Path.home()/'VideoStudioPersonal'

def bundled(name):
    candidates=[]
    if getattr(sys,'frozen',False):
        root=Path(sys.executable).parent
        candidates += [root/(name+'.exe'), root/'_internal'/(name+'.exe')]
    candidates += [BASE/'tools'/(name+'.exe')]
    for p in candidates:
        if p.exists(): return str(p)
    return shutil.which(name)

def run(cmd,timeout=None):
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,creationflags=flags)
    return p.returncode,p.stdout.strip(),p.stderr.strip()

def probe(path):
    fp=bundled('ffprobe')
    if not fp: return {'error':'Không tìm thấy ffprobe'}
    rc,out,err=run([fp,'-v','quiet','-print_format','json','-show_format','-show_streams',str(path)],30)
    if rc: return {'error':err or 'Không đọc được video'}
    d=json.loads(out); v=next((s for s in d.get('streams',[]) if s.get('codec_type')=='video'),{}); a=next((s for s in d.get('streams',[]) if s.get('codec_type')=='audio'),{})
    dur=float(d.get('format',{}).get('duration',0) or 0); fps=v.get('avg_frame_rate','0/1')
    try:
        x,y=fps.split('/'); fps=round(float(x)/float(y),2) if float(y) else 0
    except: pass
    return {'duration':dur,'width':v.get('width',0),'height':v.get('height',0),'resolution':f"{v.get('width','?')}×{v.get('height','?')}",'fps':fps,'video_codec':v.get('codec_name','?'),'audio_codec':a.get('codec_name','?')}

def download_video(url,dest,progress=None):
    from yt_dlp import YoutubeDL
    dest=Path(dest); dest.mkdir(parents=True,exist_ok=True)
    def hook(d):
        if progress and d.get('status')=='downloading':
            total=d.get('total_bytes') or d.get('total_bytes_estimate') or 0; got=d.get('downloaded_bytes') or 0
            if total: progress(min(99,int(got*100/total)),d.get('_speed_str',''))
    opts={'outtmpl':str(dest/'%(title).120s [%(id)s].%(ext)s'),'format':'bv*+ba/b','merge_output_format':'mp4','noplaylist':True,'quiet':True,'no_warnings':True,'progress_hooks':[hook]}
    ff=bundled('ffmpeg')
    if ff: opts['ffmpeg_location']=str(Path(ff).parent)
    with YoutubeDL(opts) as ydl:
        info=ydl.extract_info(url,download=True); path=Path(ydl.prepare_filename(info))
        if path.suffix.lower()!='.mp4':
            mp4=path.with_suffix('.mp4')
            if mp4.exists(): path=mp4
    if progress: progress(100,'Xong')
    return str(path)

def extract_audio(video,wav):
    ff=bundled('ffmpeg'); Path(wav).parent.mkdir(parents=True,exist_ok=True)
    rc,out,err=run([ff,'-y','-i',str(video),'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(wav)])
    if rc: raise RuntimeError(err[-1500:])
    return str(wav)

def srt_time(sec):
    ms=int(round(float(sec)*1000)); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def write_srt(segments,path,text_key='text_vi'):
    lines=[]
    for i,s in enumerate(segments,1):
        text=(s.get(text_key) or s.get('text') or '').strip(); lines += [str(i),f"{srt_time(s['start'])} --> {srt_time(s['end'])}",text,'']
    Path(path).write_text('\n'.join(lines),encoding='utf-8-sig'); return str(path)

def render_subtitles(video,srt,out,original_volume=0.65):
    ff=bundled('ffmpeg'); Path(out).parent.mkdir(parents=True,exist_ok=True)
    esc=str(Path(srt).resolve()).replace('\\','/').replace(':','\\:').replace("'","\\'")
    vf=f"subtitles='{esc}':force_style='FontName=Arial,FontSize=18,Outline=2,Shadow=1,Alignment=2,MarginV=36'"
    base=[ff,'-y','-i',str(video),'-vf',vf,'-af',f'volume={float(original_volume):.3f}']
    nv=run([ff,'-hide_banner','-encoders'],20)[1:]
    enc='h264_nvenc' if 'h264_nvenc' in ''.join(nv) else 'libx264'
    args=['-c:v',enc]
    args += ['-preset','p4','-cq','24','-b:v','0'] if enc=='h264_nvenc' else ['-preset','medium','-crf','20']
    args += ['-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)]
    rc,stdout,err=run(base+args)
    if rc: raise RuntimeError(err[-2500:])
    return str(out)

def make_project(source):
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f'); folder=BASE/'projects'/stamp; folder.mkdir(parents=True,exist_ok=True)
    meta={'created':datetime.now().isoformat(),'source':str(source),'status':'created'}
    (folder/'project.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    return folder
