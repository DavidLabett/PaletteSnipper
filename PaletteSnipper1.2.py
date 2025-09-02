import sys
import numpy as np
from sklearn.cluster import KMeans
from PIL import Image, ImageGrab, ImageDraw, ImageFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
    QFileDialog, QSystemTrayIcon, QMenu
)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPainter, QPen, QBrush, QColor
from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QGuiApplication
import keyboard
import pyperclip


# ------------------ Utility Functions ------------------ #
def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def load_font(size=26):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


# ------------------ Screenshot Selection ------------------ #
class PaletteSnipper(QWidget):
    snip_complete = pyqtSignal(QRect)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Palette Snipper")
        self.setWindowOpacity(0.01)
        self.setCursor(Qt.CrossCursor)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.begin = None
        self.end = None
        self.show()

    def paintEvent(self, _):
        if self.begin and self.end:
            qp = QPainter(self)
            rect = QRect(self.begin, self.end)

            qp.setBrush(QBrush(QColor(255, 0, 0, 255)))
            qp.setPen(QPen(QColor("white"), 6))
            qp.drawRect(rect)

            qp.setPen(QPen(QColor("red"), 5))
            qp.drawRect(rect)

    def mousePressEvent(self, event):
        self.begin = self.end = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end = event.pos()
        rect = QRect(self.begin, self.end).normalized()
        self.snip_complete.emit(rect)
        self.close()


# ------------------ Pixel Picker ------------------ #
class PixelPicker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Copy Color to Clipboard")
        self.setWindowOpacity(0.01)
        self.setCursor(Qt.CrossCursor)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.show()

    def mousePressEvent(self, event):
        pos = QGuiApplication.primaryScreen().grabWindow(0).toImage().pixelColor(event.globalPos())
        hex_color = rgb_to_hex((pos.red(), pos.green(), pos.blue()))
        try:
            pyperclip.copy(hex_color)
        except Exception:
            QApplication.clipboard().setText(hex_color)
        print(f"Copied {hex_color} to clipboard")
        self.close()


# ------------------ Palette Extraction ------------------ #
def extract_palette(image, n_colors=5):
    img_array = np.array(image)
    pixels = img_array.reshape(-1, 3)

    # Subsample for speed if too large
    if len(pixels) > 50000:
        idx = np.random.choice(len(pixels), 50000, replace=False)
        pixels = pixels[idx]

    kmeans = KMeans(n_clusters=n_colors, n_init="auto", random_state=42)
    kmeans.fit(pixels)
    colors = kmeans.cluster_centers_.astype(int)

    swatch_size = 200
    palette_img = Image.new("RGB", (swatch_size * n_colors, swatch_size + 40), "white")
    draw = ImageDraw.Draw(palette_img)
    font = load_font(26)

    for i, color in enumerate(colors):
        x0, x1 = i * swatch_size, (i + 1) * swatch_size
        draw.rectangle([x0, 0, x1, swatch_size], fill=tuple(color))
        draw.text((x0 + 10, swatch_size + 10), rgb_to_hex(color), fill="black", font=font)

    return palette_img


# ------------------ Palette Display ------------------ #
class PalettePopup(QWidget):
    def __init__(self, palette_img):
        super().__init__()
        self.setWindowTitle("Palette Snipper")
        self.setGeometry(200, 200, palette_img.width, palette_img.height + 140)

        layout = QVBoxLayout(self)

        qimg = QImage(
            palette_img.tobytes("raw", "RGB"),
            palette_img.width, palette_img.height,
            QImage.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(qimg)

        self.label = QLabel()
        self.label.setPixmap(pixmap)
        layout.addWidget(self.label)

        save_btn = QPushButton("Save as .jpg")
        save_btn.clicked.connect(lambda: self.save_palette(palette_img))
        layout.addWidget(save_btn)

        self.show()

    def save_palette(self, palette_img):
        path, _ = QFileDialog.getSaveFileName(self, "Save Palette", "palette.jpg", "JPEG Files (*.jpg)")
        if path:
            palette_img.save(path)
            print(f"Palette saved as {path}")


# ------------------ App Logic ------------------ #
def on_snip_complete(rect):
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    palette_img = extract_palette(screenshot)
    PalettePopup(palette_img)


def start_snipping():
    window = PaletteSnipper()
    window.snip_complete.connect(on_snip_complete)
    # No app.exec_() here


def start_pixel_picker():
    picker = PixelPicker()
    # No app.exec_() here


class PaletteMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Palette Snipper Menu")
        self.setGeometry(400, 400, 300, 200)
        layout = QVBoxLayout(self)

        self.child_window = None  # Keep reference to child window
# ------------------ StyleSheet for Menu ------------------ #
        self.setStyleSheet("""
            QWidget {
                background-color: #232629;
                color: #f3f3f3;
                font-family: 'Helvetica', Arial, sans-serif;
                font-size: 18px;
                font-weight: semi-bold;
            }
            QPushButton {
                background-color: #31363b;
                color: #f3f3f3;
                border: none;
                border-radius: 3px;
                padding: 10px 0;
                margin: 8px 0;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #3a3f44;
            }
            QPushButton:pressed {
                background-color: #1e2124;
            }
        """)
# ------------------ End of StyleSheet ------------------ #

        snip_btn = QPushButton("Snip Palette")
        snip_btn.clicked.connect(self.start_snipping)
        layout.addWidget(snip_btn)

        pixel_btn = QPushButton("Copy Color to Clipboard")
        pixel_btn.clicked.connect(self.start_pixel_picker)
        layout.addWidget(pixel_btn)

        quit_btn = QPushButton("Quit")
        quit_btn.clicked.connect(self.quit_app)
        layout.addWidget(quit_btn)

        self.show()

    def start_snipping(self):
        self.hide()
        self.child_window = PaletteSnipper()
        self.child_window.snip_complete.connect(on_snip_complete)
        self.child_window.show()

    def start_pixel_picker(self):
        self.hide()
        self.child_window = PixelPicker()
        self.child_window.show()

    def quit_app(self):
        QApplication.quit()


def main():
    print("Press Ctrl+Shift+Å to open Palette Snipper menu...")
    keyboard.add_hotkey("ctrl+shift+å", show_menu)
    keyboard.add_hotkey("ctrl+shift+ö", lambda: QApplication.quit())
    keyboard.wait()


def show_menu():
    app = QApplication.instance()
    if (app is None):
        app = QApplication(sys.argv)
    menu = PaletteMenu()
    # Only call app.exec_() here
    app.exec_()


if __name__ == "__main__":
    main()
