import os
import subprocess
import uuid
from PySide6.QtCore import QObject, Signal
import re

class UpscaleWorker(QObject):
    finished = Signal(str)
    progress = Signal(int)
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.process = None
        self.cancelled = False
        
    def cancel(self):
        self.cancelled = True
        if self.process:
            self.process.terminate()
    
    def run(self, input_path, model_name, temp_dir):
        try:
            output_path = os.path.join(temp_dir, f"upscaled_{uuid.uuid4().hex}.png")
            
            cmd = [
                "bin/realesrgan-ncnn-vulkan.exe",
                "-i", input_path,
                "-o", output_path,
                "-n", model_name
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Progress regex pattern
            progress_pattern = re.compile(r"(\d+)%")
            
            while True:
                if self.cancelled:
                    break
                    
                line = self.process.stdout.readline()
                if not line:
                    break
                    
                # Extract progress percentage
                match = progress_pattern.search(line)
                if match:
                    percent = int(match.group(1))
                    self.progress.emit(percent)
                
                # Check for completion
                if "done" in line.lower():
                    self.progress.emit(100)
            
            # Wait for process to finish
            return_code = self.process.wait()
            
            if self.cancelled:
                os.remove(output_path) if os.path.exists(output_path) else None
                return
                
            if return_code == 0 and os.path.exists(output_path):
                self.finished.emit(output_path)
            else:
                self.error.emit(f"Process failed with code {return_code}")
                
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
        finally:
            self.process = None