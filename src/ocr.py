import os
import sys
import time
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPixmap, QScreen
from PIL import Image
import pytesseract

class ScreenCaptureOverlay(QWidget):
    # Signal emitted when OCR capture is complete with the extracted text
    text_captured = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        # Set window flags for full screen overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False
        
        # Capture the whole screen
        screen = QApplication.primaryScreen()
        if screen:
            self.screenshot = screen.grabWindow(0)
        else:
            self.screenshot = QPixmap()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw the dim background screenshot
        painter.drawPixmap(0, 0, self.screenshot)
        
        # Overlay a dark semi-transparent color on the whole screen
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self.is_selecting and not self.begin.isNull() and not self.end.isNull():
            # Get selected rectangle
            selected_rect = QRect(self.begin, self.end).normalized()
            
            # Use composition mode to restore the original screenshot color on the selected area
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Redraw the clear area of the screenshot in the rectangle
            painter.drawPixmap(selected_rect, self.screenshot, selected_rect)
            
            # Draw border around translation selection
            pen = QPen(QColor(0, 150, 255), 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            painter.drawRect(selected_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin = event.position().toPoint()
            self.end = self.begin
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.end = event.position().toPoint()
            self.is_selecting = False
            self.update()
            
            # Close overlay and perform OCR on selected region
            self.close()
            self.perform_ocr()

    def keyPressEvent(self, event):
        # Escape key cancel capture
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def perform_ocr(self):
        rect = QRect(self.begin, self.end).normalized()
        if rect.width() < 5 or rect.height() < 5:
            return # Too small
            
        # Extract selected zone from desktop screenshot
        cropped_pixmap = self.screenshot.copy(rect)
        
        # Convert QPixmap to PIL Image
        cropped_image = cropped_pixmap.toImage()
        width = cropped_image.width()
        height = cropped_image.height()
        
        ptr = cropped_image.bits()
        # Ensure we have access to the memory pointers in a compatible manner
        ptr.setsize(height * width * 4)
        
        # Create PIL Image from raw bytes
        pil_img = Image.frombuffer(
            "RGBA", 
            (width, height), 
            ptr.asstring(), 
            "raw", 
            "BGRA", 
            0, 
            1
        )
        
        # Convert to grayscale for better OCR results
        pil_img_gray = pil_img.convert("L")
        
        import platform
        try:
            # On Windows, try to find standard Tesseract installations if not in path
            if platform.system() == "Windows":
                possible_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break

            # Run pytesseract OCR engine
            # We support multiple languages (English and French by default)
            config = '--oem 3 --psm 6'
            extracted_text = pytesseract.image_to_string(pil_img_gray, config=config, lang="eng+fra")
            
            self.text_captured.emit(extracted_text.strip())
        except Exception as e:
            # Emit error in case tesseract is not installed
            if platform.system() == "Windows":
                error_msg = (
                    f"[OCR Error] Could not perform OCR.\n"
                    f"Please install Tesseract OCR for Windows from 'https://github.com/UB-Mannheim/tesseract/wiki'\n"
                    f"and ensure it is in your system PATH or installed to 'C:\\Program Files\\Tesseract-OCR'.\n\n"
                    f"Technical details: {str(e)}"
                )
            else:
                error_msg = (
                    f"[OCR Error] Could not perform OCR.\n"
                    f"Please make sure Tesseract is installed on your Linux system:\n"
                    f"'sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra'\n\n"
                    f"Technical details: {str(e)}"
                )
            self.text_captured.emit(error_msg)


class PowerToysOCRHelper:
    def __init__(self, on_text_ready):
        self.on_text_ready = on_text_ready
        try:
            self.initial_text = QApplication.clipboard().text()
        except Exception:
            self.initial_text = ""
        self.timer = QTimer()
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.check_clipboard)
        self.start_time = time.time()
        
    def start(self):
        # Trigger the Windows PowerToys shortcut Win+Shift+T
        try:
            from pynput.keyboard import Key, Controller
            kb = Controller()
            kb.press(Key.cmd)
            kb.press(Key.shift)
            kb.press('t')
            kb.release('t')
            kb.release(Key.shift)
            kb.release(Key.cmd)
        except Exception as e:
            print(f"Error simulating keypresses: {e}")
            
        self.timer.start()
        
    def check_clipboard(self):
        if time.time() - self.start_time > 15: # Timeout 15s
            self.timer.stop()
            return
            
        try:
            current_text = QApplication.clipboard().text()
            if current_text != self.initial_text:
                if current_text and current_text.strip():
                    self.timer.stop()
                    self.on_text_ready(current_text)
        except Exception:
            pass


def run_ocr_capture(on_text_ready_callback, engine="tesseract"):
    """
    Launches the configured OCR engine (native PyQt Screen selection or PowerToys).
    """
    import platform
    if engine == "powertoys" and platform.system() == "Windows":
        pt_helper = PowerToysOCRHelper(on_text_ready_callback)
        pt_helper.start()
        global _pt_helper_reference
        _pt_helper_reference = pt_helper
    else:
        overlay = ScreenCaptureOverlay()
        overlay.text_captured.connect(on_text_ready_callback)
        overlay.show()
        # Keep reference to avoid garbage collection
        global _overlay_reference
        _overlay_reference = overlay
