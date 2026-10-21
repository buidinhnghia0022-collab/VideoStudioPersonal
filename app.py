import sys, json, logging, traceback
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt,QThread,Signal
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QTreeWidget,QTreeWidgetItem,QProgressBar,QMessageBox,QTextEdit,QGroupBox,QHeaderView,QLineEdit,QComboBox,QDoubleSpinBox)
from engine import BASE,probe,download_video,extract_audio,write_srt,render_subtitles,make_project,bundled,run
from ai_pipeline import transcribe_whisper,translate_segments,save_segments,ollama_available

APP_NAME='Video Studio Personal'; VERSION='0.4.0'
for d in ('projects','output','logs','cache','models','tools','downloads'):(BASE/d).mkdir(parents=True,exist_ok=True)
LOG=BASE/'logs'/f"studio-{datetime.now():%Y%m%d}.log"
logging.basicConfig(filename=LOG,level=logging.INFO,encoding='utf-8',format='%(asctime)s | %(levelname)s | %(message)s')

def dt(sec):
    sec=int(sec or 0); return f'{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}'

class Worker(QThread):
    message=Signal(str); progress=Signal(int); done=Signal(str); failed=Signal(str)
    def __init__(self,mode,payload): super().__init__(); self.mode=mode; self.payload=payload
    def run(self):
        try:
            if self.mode=='download':
                p=download_video(self.payload,BASE/'downloads',lambda n,s:self.progress.emit(n)); self.done.emit(p); return
            src=self.payload; folder=make_project(src); self.message.emit('Project: '+str(folder)); self.progress.emit(5)
            wav=folder/'source.wav'; self.message.emit('1/4 Tách âm thanh...'); extract_audio(src,wav); self.progress.emit(15)
            self.message.emit('2/4 Whisper nhận dạng tiếng Trung (lần đầu sẽ tải model)...')
            seg=transcribe_whisper(wav,model_name='large-v3'); save_segments(seg,folder/'zh.json'); self.progress.emit(48)
            if not ollama_available():
                write_srt(seg,folder/'zh.srt',text_key='text'); self.done.emit('NEED_OLLAMA|'+str(folder)); return
            self.message.emit('3/4 Dịch Trung → Việt bằng AI local...'); seg=translate_segments(seg,progress=lambda n:self.progress.emit(48+int(n*.32))); save_segments(seg,folder/'vi.json')
            srt=write_srt(seg,folder/'vi.srt'); self.progress.emit(82)
            self.message.emit('4/4 Render phụ đề Việt bằng NVENC...'); out=BASE/'output'/(Path(src).stem+'_VI.mp4'); render_subtitles(src,srt,out); self.progress.emit(100); self.done.emit(str(out))
        except Exception as e: self.failed.emit(str(e)+'\n'+traceback.format_exc()[-2500:])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.worker=None; self.setWindowTitle(f'{APP_NAME} v{VERSION}'); self.resize(1220,800)
        root=QWidget(); self.setCentralWidget(root); L=QVBoxLayout(root)
        t=QLabel('VIDEO STUDIO PERSONAL'); t.setStyleSheet('font-size:28px;font-weight:700;padding:8px'); L.addWidget(t)
        L.addWidget(QLabel('V0.4 • Douyin/local • Whisper tiếng Trung • dịch local • phụ đề Việt • NVENC'))
        urlrow=QHBoxLayout(); self.url=QLineEdit(); self.url.setPlaceholderText('Dán link video Douyin / nguồn được yt-dlp hỗ trợ...'); dl=QPushButton('⬇ Tải video'); dl.clicked.connect(self.download); urlrow.addWidget(self.url); urlrow.addWidget(dl); L.addLayout(urlrow)
        row=QHBoxLayout();
        for text,fn in [('+ Thêm video',self.add_video),('− Xóa',self.remove_video),('⚙ Kiểm tra hệ thống',self.system_check),('▶ Xử lý Trung → Việt',self.process)]:
            b=QPushButton(text); b.clicked.connect(fn); row.addWidget(b)
        L.addLayout(row)
        settings=QHBoxLayout(); settings.addWidget(QLabel('Model dịch local:')); self.model=QComboBox(); self.model.addItems(['qwen2.5:7b']); settings.addWidget(self.model); settings.addWidget(QLabel('Âm lượng gốc:')); self.vol=QDoubleSpinBox(); self.vol.setRange(0,1); self.vol.setSingleStep(.05); self.vol.setValue(.65); settings.addWidget(self.vol); settings.addStretch(); L.addLayout(settings)
        self.queue=QTreeWidget(); self.queue.setHeaderLabels(['Video','Thời lượng','Độ phân giải','FPS','Codec','Trạng thái']); self.queue.header().setSectionResizeMode(0,QHeaderView.Stretch); L.addWidget(self.queue)
        self.progress=QProgressBar(); L.addWidget(self.progress)
        box=QGroupBox('Logs Console'); bl=QVBoxLayout(box); self.logs=QTextEdit(); self.logs.setReadOnly(True); self.logs.setMaximumHeight(210); bl.addWidget(self.logs); L.addWidget(box)
        self.status=QLabel('Dữ liệu: '+str(BASE)); L.addWidget(self.status); self.log('Ứng dụng đã khởi động.')
    def log(self,s): self.logs.append(f'[{datetime.now():%H:%M:%S}] {s}'); logging.info(s)
    def add_path(self,f):
        if self.queue.topLevelItemCount()>=3:return
        info=probe(f); name=Path(f).name
        if 'error' in info: vals=[name,'—','—','—','—','Lỗi đọc video']; self.log(info['error'])
        else: vals=[name,dt(info['duration']),info['resolution'],str(info['fps']),info['video_codec'],'Sẵn sàng']
        it=QTreeWidgetItem(vals); it.setData(0,Qt.UserRole,f); self.queue.addTopLevelItem(it)
    def add_video(self):
        files,_=QFileDialog.getOpenFileNames(self,'Chọn video',str(Path.home()),'Video (*.mp4 *.mkv *.mov *.avi *.webm *.m4v)')
        for f in files:
            if self.queue.topLevelItemCount()>=3:break
            self.add_path(f)
    def remove_video(self):
        for x in self.queue.selectedItems():self.queue.takeTopLevelItem(self.queue.indexOfTopLevelItem(x))
    def start_worker(self,mode,payload):
        if self.worker and self.worker.isRunning(): QMessageBox.information(self,APP_NAME,'Đang có tác vụ chạy.'); return
        self.progress.setValue(0); self.worker=Worker(mode,payload); self.worker.message.connect(self.log); self.worker.progress.connect(self.progress.setValue); self.worker.failed.connect(self.fail); self.worker.done.connect(self.finish); self.worker.start()
    def download(self):
        u=self.url.text().strip()
        if not u:return
        self.log('Bắt đầu tải video...'); self.start_worker('download',u)
    def process(self):
        items=self.queue.selectedItems(); it=items[0] if items else (self.queue.topLevelItem(0) if self.queue.topLevelItemCount() else None)
        if not it: QMessageBox.information(self,APP_NAME,'Hãy thêm video trước.'); return
        self.start_worker('process',it.data(0,Qt.UserRole))
    def finish(self,result):
        if result.startswith('NEED_OLLAMA|'):
            folder=result.split('|',1)[1]; self.log('Whisper đã xong. Chưa có dịch local vì Ollama chưa chạy.'); QMessageBox.warning(self,APP_NAME,'Đã nhận dạng tiếng Trung nhưng chưa phát hiện bộ dịch local Ollama.\nProject: '+folder); return
        if Path(result).suffix.lower() in ('.mp4','.mkv','.mov','.webm') and Path(result).parent==BASE/'downloads': self.add_path(result); self.log('Tải xong: '+result)
        else:self.log('Hoàn tất: '+result)
        QMessageBox.information(self,APP_NAME,'Hoàn tất:\n'+result)
    def fail(self,e): self.log('LỖI: '+e); QMessageBox.critical(self,APP_NAME,e[-1800:])
    def system_check(self):
        ff=bundled('ffmpeg'); fp=bundled('ffprobe'); self.log('FFmpeg: '+('✓' if ff else '✕')); self.log('ffprobe: '+('✓' if fp else '✕'))
        import shutil; nv=shutil.which('nvidia-smi')
        if nv:
            rc,out,err=run([nv,'--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],10); self.log('NVIDIA: '+(out if rc==0 else err))
        if ff:
            rc,out,err=run([ff,'-hide_banner','-encoders'],15); self.log('NVENC: '+('✓' if 'h264_nvenc' in out+err else '✕'))
        self.log('Ollama dịch local: '+('✓' if ollama_available() else '✕ chưa chạy/cài'))

if __name__=='__main__':
    app=QApplication(sys.argv); app.setStyle('Fusion'); w=MainWindow(); w.show(); sys.exit(app.exec())
