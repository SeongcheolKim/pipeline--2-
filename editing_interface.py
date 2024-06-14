import os
import sys
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class MouseMoveAction(QUndoCommand):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

class DrawAction(MouseMoveAction):
    def __init__(self, widget, startPoint, endPoint, prevImage):
        super().__init__(widget)
        self.widget = widget
        self.startPoint = startPoint
        self.endPoint = endPoint
        self.prevImage = QPixmap(prevImage)
        self.currentImage = QPixmap(prevImage)

    def redo(self):
        painter = QPainter(self.widget.label)
        painter.setPen(QPen(self.widget.brushColor, self.widget.brushSize, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(self.startPoint, self.endPoint)
        painter.end()
        self.widget.update()

    def undo(self):
        self.widget.label = QPixmap(self.prevImage)
        self.widget.update()



class FillAction(MouseMoveAction):
    def __init__(self, widget, position, fillColor, prevImage):
        super().__init__(widget)
        self.position = position
        self.fillColor = fillColor
        self.prevImage = QPixmap(prevImage)
        self.image = QPixmap(prevImage)

    def redo(self):
        image = self.prevImage.toImage()
        self.widget.floodFill(image, self.position.x(), self.position.y(), self.fillColor)
        self.widget.label = QPixmap.fromImage(image)
        self.widget.update()
    
    def undo(self):
        self.widget.label = self.prevImage
        self.widget.update()

class DrawingWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setMinimumSize(1024, 1024)
        self.lastPoint = QPoint()
        self.currentPoint = QPoint()
        self.drawing = False
        self.showBrush = True
        self.brushSize = 5
        self.brushColor = Qt.black
        self.setMouseTracking(True)
        self.image = QPixmap(self.size())
        self.image.fill(Qt.white)
        self.label = QPixmap(self.size())
        self.label.fill(Qt.white)
        self.opacity = 0.5
        self.undo_stack = QUndoStack(self)
        self.startImage = None

    def setImagePixmap(self, pixmap):
        self.image = pixmap.scaled(self.size(), Qt.KeepAspectRatio)
        self.update()

    def setLabelPixmap(self, pixmap):
        self.label = pixmap.scaled(self.size(), Qt.KeepAspectRatio)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.image)
        painter.setOpacity(self.opacity)
        painter.drawPixmap(0, 0, self.label)
        if self.showBrush:
            painter.setPen(QPen(Qt.black, 1, Qt.DotLine))
            color = QColor(self.brushColor)
            painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 150), Qt.SolidPattern))
            painter.drawEllipse(self.currentPoint, self.brushSize / 2, self.brushSize / 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.lastPoint = event.pos()
            self.startImage = QPixmap(self.label)

    def mouseMoveEvent(self, event):
        self.currentPoint = event.pos()
        if self.drawing:
            painter = QPainter(self.label)
            painter.setPen(QPen(self.brushColor, self.brushSize, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(self.lastPoint, self.currentPoint)
            self.lastPoint = self.currentPoint
            painter.end()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            endPoint = event.pos()
            draw_action = DrawAction(self, self.lastPoint, endPoint, self.startImage)
            draw_action.redo()  # 마지막 그리기 작업을 수행하여 화면에 반영
            self.undo_stack.push(draw_action)  # undo 스택에 추가
            self.update()

    def enterEvent(self, event):
        self.showBrush = True
        self.currentPoint = self.mapFromGlobal(QCursor.pos())
        self.update()

    def leaveEvent(self, event):
        self.showBrush = False
        self.update()

    def setBrushColor(self, color):
        self.brushColor = QColor(color)
        self.update()
    
    def setBrushSize(self, size):
        self.brushSize = size
        self.update()

    def saveLabel(self, path):
        self.label.scaled(256, 256, Qt.KeepAspectRatio).save(path)

    def floodFill(self, image, x, y, newColor):
        targetColor = image.pixelColor(x, y)
        if targetColor == newColor:
            return

        self.stack = [(x, y)]

        while self.stack:
            x, y = self.stack.pop()
            if not self.rect().contains(x, y):
                continue
            currentColor = image.pixelColor(x, y)
            
            if currentColor == targetColor:
                image.setPixelColor(x, y, newColor)
                self.stack.append((x - 1, y))
                self.stack.append((x + 1, y))
                self.stack.append((x, y - 1))
                self.stack.append((x, y + 1))

    def paintCanvas(self):
        if self.currentPoint:
            fillColor = self.brushColor
            image = self.label.toImage()
            fill_action = FillAction(self, self.currentPoint, fillColor, self.label)
            self.undo_stack.push(fill_action)
            fill_action.redo()  # redo() 메소드를 즉시 호출하여 액션을 수행합니다.
        self.update()

    def clearCanvas(self):
        while self.undo_stack.canUndo():
            self.undo_stack.undo()
        self.update()




class ImageViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.img_index = 0
        self.mask_index = 0
        self.img_files = sorted([f for f in os.listdir("./img") if f.endswith(('.png', '.jpg', '.jpeg'))])
        self.mask_files = sorted([f for f in os.listdir("./mask") if f.endswith(('.png', '.jpg', '.jpeg'))])
        assert len(self.img_files) == len(self.mask_files)

        self.undo_stacks = {f: QUndoStack(self) for f in self.img_files}
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.img_label = QLabel(self)
        self.canvas = DrawingWidget(self)
        self.loadImages()

        hbox = QHBoxLayout()
        self.index_label = QLabel(f"{self.img_index + 1} / {len(self.img_files)}", self)
        prev_button = QPushButton('Previous', self)
        next_button = QPushButton('Next', self)
        clear_button = QPushButton('Clear', self)
        save_button = QPushButton('Save', self)
        prev_button.clicked.connect(self.prevImage)
        next_button.clicked.connect(self.nextImage)
        clear_button.clicked.connect(self.canvas.clearCanvas)
        save_button.clicked.connect(self.saveLabel)

        hbox.addWidget(self.index_label)
        hbox.addWidget(prev_button)
        hbox.addWidget(next_button)
        hbox.addWidget(clear_button)
        hbox.addWidget(save_button)

        layout.addLayout(hbox)

        hbox = QHBoxLayout()
        hbox.addWidget(self.img_label)
        hbox.addWidget(self.canvas)
        self.brush_slider = QSlider(Qt.Vertical, self)
        self.brush_slider.setMinimum(1)
        self.brush_slider.setMaximum(50)
        self.brush_slider.setValue(5)
        self.brush_slider.valueChanged.connect(self.canvas.setBrushSize)
        hbox.addWidget(self.brush_slider)

        layout.addLayout(hbox)
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(50)
        self.opacity_slider.valueChanged.connect(self.updateOpacity)
        layout.addWidget(self.opacity_slider)

        self.color_mode = "IR"
        self.colors_ir = ['#d60acf', '#9dc53f', '#79d2ec', '#de9846', '#c72c36', '#000000']
        self.colors_rgb = ['#f19bdc', '#44690c', '#d60acf', '#f5f5dc', '#805472', '#f4f812']

        self.color_box = QHBoxLayout()
        self.addColorButtons(self.colors_ir, self.color_box, self.canvas)
        layout.addLayout(self.color_box)

        self.toggle_color_button = QPushButton('Toggle Colors', self)
        self.toggle_color_button.clicked.connect(self.toggleColorButtons)
        layout.addWidget(self.toggle_color_button)

        self.setLayout(layout)
        self.setWindowTitle('Image Viewer')
        self.setGeometry(400, 300, 350, 300)
    
    def loadImages(self):
        if self.img_files:
            img_path = os.path.join("./img", self.img_files[self.img_index])
            img_pixmap = QPixmap(img_path)
            scaled_img_pixmap = img_pixmap.scaled(1024, 1024, Qt.KeepAspectRatio)
            self.img_label.setPixmap(scaled_img_pixmap)
            self.canvas.setImagePixmap(img_pixmap)

        if self.mask_files:
            mask_path = os.path.join("./mask", self.mask_files[self.mask_index])
            self.mask_pixmap = QPixmap(mask_path)
            self.canvas.setLabelPixmap(self.mask_pixmap)
        
        # Update undo stack for the current image
        current_img_file = self.img_files[self.img_index]
        self.canvas.undo_stack = self.undo_stacks[current_img_file]

    def updateOpacity(self):
        self.opacity = self.opacity_slider.value() / 100
        self.canvas.opacity = self.opacity
        self.canvas.update()

    def prevImage(self):
        self.img_index = (self.img_index - 1) % len(self.img_files)
        self.mask_index = (self.mask_index - 1) % len(self.mask_files)
        self.loadImages()
        self.index_label.setText(f"{self.img_index + 1} / {len(self.img_files)}")

    def nextImage(self):
        self.img_index = (self.img_index + 1) % len(self.img_files)
        self.mask_index = (self.mask_index + 1) % len(self.mask_files)
        self.loadImages()
        self.index_label.setText(f"{self.img_index + 1} / {len(self.img_files)}")

    def addColorButtons(self, colors, layout, canvas):
        self.color_buttons = []
        for color in colors:
            button = QPushButton(self)
            button.setFixedSize(50, 50)
            button.setStyleSheet("background-color: %s" % color)
            button.clicked.connect(lambda checked, c=color: canvas.setBrushColor(c))
            layout.addWidget(button)
            self.color_buttons.append(button)

    def removeColorButtons(self, layout):
        for button in self.color_buttons:
            layout.removeWidget(button)
            button.deleteLater()
        self.color_buttons = []

    def toggleColorButtons(self):
        if self.color_mode == "IR":
            self.removeColorButtons(self.layout())
            self.addColorButtons(self.colors_rgb, self.color_box, self.canvas)
            self.color_mode = "RGB"
        else:
            self.removeColorButtons(self.layout())
            self.addColorButtons(self.colors_ir, self.color_box, self.canvas)
            self.color_mode = "IR"

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_BracketLeft:
            self.canvas.setBrushSize(self.canvas.brushSize - 10)
            self.canvas.update()
            self.brush_slider.setValue(self.canvas.brushSize)
        elif event.key() == Qt.Key_BracketRight:
            self.canvas.setBrushSize(self.canvas.brushSize + 10)
            self.canvas.update()
            self.brush_slider.setValue(self.canvas.brushSize)
        elif event.key() == Qt.Key_Comma:
            self.saveLabel()
            self.prevImage()
        elif event.key() == Qt.Key_Period:
            self.saveLabel()
            self.nextImage()
        elif event.key() == Qt.Key_Minus:
            self.opacity_slider.setValue(self.opacity_slider.value() - 10)
        elif event.key() == Qt.Key_Equal:
            self.opacity_slider.setValue(self.opacity_slider.value() + 10)
        elif event.key() == Qt.Key_C:
            self.canvas.clearCanvas()        
        elif event.key() == Qt.Key_P:
            self.canvas.paintCanvas()
            self.canvas.update()
        elif event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                self.saveLabel()
            elif event.key() == Qt.Key_Z:
                self.canvas.undo_stack.undo()
                self.canvas.update()
            elif event.key() == Qt.Key_Y:
                self.canvas.undo_stack.redo()
                self.canvas.update()
        # number keys to change color
        for i in range(6):
            if event.key() == Qt.Key_1 + i:
                self.color_buttons[i].click()

    def saveLabel(self):
        self.canvas.saveLabel(os.path.join('./mask', self.mask_files[self.mask_index]))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageViewer()
    ex.show()
    sys.exit(app.exec_())
