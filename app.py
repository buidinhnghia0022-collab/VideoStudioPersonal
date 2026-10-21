import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QListWidget, QProgressBar, QMessageBox

APP_NAME = "Video Studio Personal"
VERSION = "0.1.0"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1100, 720)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        title = QLabel("VIDEO STUDIO PERSONAL")
        title.setStyleSheet("font-size: 28px; font-weight: 700; padding: 12px;")
        subtitle = QLabel("Bản V1 • xử lý video Trung → Việt • local-first")
        subtitle.setStyleSheet("font-size: 15px; padding: 0 12px 12px 12px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        row = QHBoxLayout()
        add_btn = QPushButton("+ Thêm video")
        add_btn.clicked.connect(self.add_video)
        start_btn = QPushButton("▶ Bắt đầu xử lý")
        start_btn.clicked.connect(self.not_ready)
        row.addWidget(add_btn)
        row.addWidget(start_btn)
        layout.addLayout(row)
        self.queue = QListWidget()
        layout.addWidget(QLabel("Hàng đợi (tối đa 3 video):"))
        layout.addWidget(self.queue)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        status = QLabel("✓ Giao diện V1 đã sẵn sàng. Các engine Whisper / dịch / TTS / FFmpeg sẽ được ghép ở các build tiếp theo.")
        status.setStyleSheet("padding: 10px;")
        layout.addWidget(status)

    def add_video(self):
        if self.queue.count() >= 3:
            QMessageBox.information(self, APP_NAME, "Hàng đợi hiện giới hạn 3 video.")
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Chọn video", str(Path.home()), "Video (*.mp4 *.mkv *.mov *.avi *.webm)")
        for file in files:
            if self.queue.count() >= 3:
                break
            self.queue.addItem(file)

    def not_ready(self):
        QMessageBox.information(self, APP_NAME, "Bản build đầu tiên dùng để kiểm tra cài đặt Windows và giao diện. Pipeline AI sẽ được bổ sung tiếp.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
