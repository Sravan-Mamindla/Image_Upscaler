import os
import tempfile
from PySide6.QtCore import QThread, Slot
from processor import UpscaleWorker
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QProgressBar
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QSize

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Image Upscaler")
        self.setMinimumSize(QSize(800, 600))
        
        # Central widget setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Image preview areas
        image_layout = QHBoxLayout()
        self.input_label = self.create_image_label("Drop input image here")
        self.output_label = self.create_image_label("Upscaled output")
        image_layout.addWidget(self.input_label)
        image_layout.addWidget(self.output_label)
        main_layout.addLayout(image_layout)
        
        # Control panel
        control_layout = QHBoxLayout()
        self.open_button = QPushButton("Open Image")
        self.open_button.clicked.connect(self.open_image)
        self.upscale_button = QPushButton("Upscale")
        self.upscale_button.setEnabled(False)
        control_layout.addWidget(self.open_button)
        control_layout.addWidget(self.upscale_button)
        main_layout.addLayout(control_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        #Creating temp directory
        import os
        os.makedirs("temp", exist_ok=True)

        # Image state
        self.input_path = None

        #upscalling button
        self.upscale_button.clicked.connect(self.start_upscaling)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        control_layout.addWidget(self.cancel_button)
        self.cancel_button.clicked.connect(self.cancel_processing)
        
        # Processing state
        self.worker_thread = None
        self.worker = None
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)

        #save button
        self.save_button = QPushButton("Save Output")
        self.save_button.setEnabled(False)
        control_layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.save_output)

    def create_image_label(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                background-color: #222;
                color: #fff;
            }
        """)
        label.setMinimumSize(300, 300)
        return label

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", 
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.input_path = path
            self.display_image(path, self.input_label)
            self.upscale_button.setEnabled(True)

    def display_image(self, path, label):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                label.width(), label.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            label.setPixmap(pixmap)

    @Slot()
    def start_upscaling(self):
        if not self.input_path:
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.upscale_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.output_label.clear()
        self.output_label.setText("Processing...")
        
        # Create worker thread
        self.worker_thread = QThread()
        self.worker = UpscaleWorker()
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.finished.connect(self.handle_finished)
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.handle_error)
        self.worker_thread.started.connect(
            lambda: self.worker.run(
                input_path=self.input_path,
                model_name="realesrgan-x4plus-anime",
                temp_dir=self.temp_dir
            )
        )
        
        # Cleanup when done
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        # Start thread
        self.worker_thread.start()
    
    @Slot(int)
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    @Slot(str)
    def handle_finished(self, output_path):
        self.display_image(output_path, self.output_label)
        self.progress_bar.setVisible(False)
        self.upscale_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.output_path = output_path
        self.save_button.setEnabled(True)
    
    @Slot(str)
    def handle_error(self, message):
        self.output_label.setText(f"Error: {message}")
        self.progress_bar.setVisible(False)
        self.upscale_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
    
    @Slot()
    def cancel_processing(self):
        if self.worker:
            self.worker.cancel()
        self.handle_error("Processing cancelled")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.input_path = file_path
                self.display_image(file_path, self.input_label)
                self.upscale_button.setEnabled(True)
                self.output_label.clear()
                break    
    
    def save_output(self):
        if not hasattr(self, 'output_path') or not self.output_path:
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Upscaled Image", "",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)"
        )
        if path:
            # Use Pillow for format conversion
            from PIL import Image
            img = Image.open(self.output_path)
            img.save(path)