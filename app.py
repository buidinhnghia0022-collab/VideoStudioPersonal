import sys, json, shutil, subprocess, logging
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QTreeWidget,QTreeWidgetItem,QProgressBar,QMessageBox,QTextEdit,QGroupBox,QHeaderView)

APP_NAME='Video Studio Personal'
VERSION='0.2.0'
BASE=Path.home()/'VideoStudioPersonal'
for d in ('projects','output','logs','cache','models','tools'):
    (BASE/d).mkdir(parents=True,exist_ok=True)
LOG=BASE/'logs'/f"studio-{datetime.now():%Y%m%d}.log"
logging.basicConfig(filename=LOG,level=logging.INFO,encoding='utf-8',format='%(asctime)s | %(levelname)s | %(message)s')

def run(cmd,timeout=15):
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return p.returncode,p.stdout.strip(),p.stderr.strip()
    except Exception as e: return -1,'',str(e)

def find_tool(name):
    local=BASE/'tools'/(name+'.exe')
    return str(local) if local.exists() else shutil.which(name)

def probe(path):
    ffprobe=find_tool('ffprobe')
    if not ffprobe: return {'error':'Chưa tìm thấy ffprobe. FFmpeg sẽ được tích hợp ở build tiếp theo.'}
    rc,out,err=run([ffprobe,'-v','quiet','-print_format','json','-show_format','-show_streams',path],30)
    if rc: return {'error':err or 'Không đọc được video'}
    try:
        data=json.loads(out); v=next((s for s in data.get('streams',[]) if s.get('codec_type')=='video'),{})
        dur=float(data.get('format',{}).get('duration',0) or 0); fps=v.get('avg_frame_rate','0/1')
        try:
            a,b=fps.split('/'); fps=f'{float(a)/float(b):.2f}' if float(b) else '0'
        except: pass
        return {'duration':dur,'resolution':f"{v.get('width','?')}×{v.get('height','?')}",'fps':fps,'codec':v.get('codec_name','?')}
    except Exception as e: return {'error':str(e)}

def duration_text(sec):
    sec=int(sec or 0); return f'{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(f'{APP_NAME} v{VERSION}'); self.resize(1180,760)
        root=QWidget(); self.setCentralWidget(root); layout=QVBoxLayout(root)
        title=QLabel('VIDEO STUDIO PERSONAL'); title.setStyleSheet('font-size:28px;font-weight:700;padding:10px')
        layout.addWidget(title); layout.addWidget(QLabel('V0.2 • kiểm tra video • project • hệ thống GPU/NVENC • local-first'))
        row=QHBoxLayout(); add=QPushButton('+ Thêm video'); add.clicked.connect(self.add_video); remove=QPushButton('− Xóa'); remove.clicked.connect(self.remove_video); check=QPushButton('⚙ Kiểm tra hệ thống'); check.clicked.connect(self.system_check); start=QPushButton('▶ Tạo project'); start.clicked.connect(self.create_project)
        for b in (add,remove,check,start): row.addWidget(b)
        layout.addLayout(row)
        self.queue=QTreeWidget(); self.queue.setHeaderLabels(['Video','Thời lượng','Độ phân giải','FPS','Codec','Trạng thái']); self.queue.header().setSectionResizeMode(0,QHeaderView.Stretch); layout.addWidget(self.queue)
        self.progress=QProgressBar(); layout.addWidget(self.progress)
        box=QGroupBox('Logs Console'); bl=QVBoxLayout(box); self.logs=QTextEdit(); self.logs.setReadOnly(True); self.logs.setMaximumHeight(190); bl.addWidget(self.logs); layout.addWidget(box)
        self.status=QLabel(f'Dữ liệu riêng: {BASE}'); layout.addWidget(self.status); self.log('V0.2 đã khởi động.')
    def log(self,text):
        line=f'[{datetime.now():%H:%M:%S}] {text}'; self.logs.append(line); logging.info(text)
    def add_video(self):
        if self.queue.topLevelItemCount()>=3: QMessageBox.information(self,APP_NAME,'Hàng đợi tối đa 3 video.'); return
        files,_=QFileDialog.getOpenFileNames(self,'Chọn video',str(Path.home()),'Video (*.mp4 *.mkv *.mov *.avi *.webm *.m4v)')
        for f in files:
            if self.queue.topLevelItemCount()>=3: break
            if any(self.queue.topLevelItem(i).data(0,Qt.UserRole)==f for i in range(self.queue.topLevelItemCount())): continue
            info=probe(f); name=Path(f).name
            if 'error' in info:
                item=QTreeWidgetItem([name,'—','—','—','—','Cần FFmpeg']); self.log(f'{name}: {info["error"]}')
            else:
                item=QTreeWidgetItem([name,duration_text(info['duration']),info['resolution'],str(info['fps']),info['codec'],'Sẵn sàng']); self.log(f"Đã đọc {name}: {info['resolution']} | {duration_text(info['duration'])} | {info['fps']} fps")
            item.setData(0,Qt.UserRole,f); self.queue.addTopLevelItem(item)
    def remove_video(self):
        for item in self.queue.selectedItems(): self.queue.takeTopLevelItem(self.queue.indexOfTopLevelItem(item))
    def system_check(self):
        self.log('--- Kiểm tra hệ thống ---'); ff=find_tool('ffmpeg'); fp=find_tool('ffprobe')
        self.log('FFmpeg: '+('✓ '+ff if ff else '✕ chưa tìm thấy')); self.log('ffprobe: '+('✓ '+fp if fp else '✕ chưa tìm thấy'))
        nv=shutil.which('nvidia-smi')
        if nv:
            rc,out,err=run([nv,'--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],10); self.log('NVIDIA: '+(('✓ '+out) if rc==0 else '✕ '+err))
        else: self.log('NVIDIA: ✕ không tìm thấy nvidia-smi')
        if ff:
            rc,out,err=run([ff,'-hide_banner','-encoders'],15); self.log('NVENC: '+('✓ h264_nvenc sẵn sàng' if 'h264_nvenc' in out+err else '✕ chưa phát hiện h264_nvenc'))
        self.log('Thư mục output: '+str(BASE/'output')); self.log('--- Hoàn tất ---')
    def create_project(self):
        n=self.queue.topLevelItemCount()
        if not n: QMessageBox.information(self,APP_NAME,'Hãy thêm ít nhất 1 video.'); return
        stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); folder=BASE/'projects'/stamp; folder.mkdir(parents=True,exist_ok=True)
        videos=[]
        for i in range(n):
            it=self.queue.topLevelItem(i); videos.append({'source':it.data(0,Qt.UserRole),'duration':it.text(1),'resolution':it.text(2),'fps':it.text(3),'codec':it.text(4)})
        (folder/'project.json').write_text(json.dumps({'version':VERSION,'created':datetime.now().isoformat(),'videos':videos},ensure_ascii=False,indent=2),encoding='utf-8')
        self.progress.setValue(100); self.log(f'Đã tạo project: {folder}'); QMessageBox.information(self,APP_NAME,f'Đã tạo project V0.2\n{folder}\n\nBước AI/render sẽ được ghép ở bản tiếp theo.')

if __name__=='__main__':
    app=QApplication(sys.argv); app.setStyle('Fusion'); w=MainWindow(); w.show(); sys.exit(app.exec())
