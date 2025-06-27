import sys
from processor import UpscaleWorker
from PySide6.QtCore import QCoreApplication, QTimer

def handle_finished(path):
    print(f"Upscaled image saved to: {path}")
    app.quit()

def handle_progress(percent):
    print(f"Progress: {percent}%")

def handle_error(message):
    print(f"Error: {message}")
    app.quit()

def start_worker():
    worker.run(
        input_path="bin\image.png",
        model_name="realesrgan-x4plus-anime",
        temp_dir="temp"
    )

if __name__ == "__main__":
    app = QCoreApplication(sys.argv)
    worker = UpscaleWorker()
    worker.finished.connect(handle_finished)
    worker.progress.connect(handle_progress)
    worker.error.connect(handle_error)
    QTimer.singleShot(0, start_worker)  # Start worker after event loop starts
    sys.exit(app.exec())