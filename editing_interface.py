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
        self.image = QPixmap(prevImage)

    def redo(self):
        painter = QPainter(self.widget.label)
        painter.setPen(QPen(self.widget.brushColor, self.widget.brushSize, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(self.startPoint, self.endPoint)
        painter.end()
        self.widget.update()


    def undo(self):
        self.widget.label = QPixmap(self.image)
        self.widget.update()

class FillAction(MouseMoveAction):
    def __init__(self, widget, position, fillColor, prevImage):
        super().__init__(widget)
        self.position = position
        self.fillColor = fillColor
        self.image = prevImage

    def redo(self):
        self.widget.floodFill(self.image, self.position.x(), self.position.y(), self.fillColor)
        self.widget.label = QPixmap.fromImage(self.image)
        self.widget.update()
    
    def undo(self):
        self.widget.label = QPixmap(self.image)
        self.widget.update()

class DrawingWidget(QWidget):

    actionPerformed = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        # set size
        self.setMinimumSize(512, 512)
        self.lastPoint = QPoint()
        self.currentPoint = QPoint()
        self.drawing = False
        self.showBrush = False
        self.brushSize = 5
        self.brushColor = Qt.black
        self.setMouseTracking(True)  # 마우스 트래킹 활성화
        # Pixmap 생성
        self.image = QPixmap(self.size())  # QPixmap을 위젯 크기로 초기화
        self.image.fill(Qt.white)  # 초기 배경색 설정
        self.label = QPixmap(self.size())
        self.label.fill(Qt.white)
        self.opacity = 0.5  # 투명도 초기값 50%
        #undo 스택 생성
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
        painter.drawPixmap(0, 0, self.image)  # QPixmap을 위젯에 그립니다.
        painter.setOpacity(self.opacity)  # 예시로 50% 투명도 설정
        painter.drawPixmap(0, 0, self.label)
        if self.showBrush:
            # 브러시 사이즈를 표시하는 원 그리기
            painter.setPen(QPen(Qt.black, 1, Qt.DotLine))
            if isinstance(self.brushColor, Qt.GlobalColor):
                color = QColor(self.brushColor)
            else:
                color = self.brushColor
            painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 150), Qt.SolidPattern))
            painter.drawEllipse(self.currentPoint, self.brushSize / 2, self.brushSize / 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus(Qt.MouseFocusReason)  # 포커스를 DrawingWidget에 설정
            self.drawing = True
            self.lastPoint = event.pos()
            self.startImage = QPixmap(self.label)
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.currentPoint = event.pos()
        if self.drawing:
            painter = QPainter(self.label)
            painter.setPen(QPen(self.brushColor, self.brushSize, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(self.lastPoint, event.pos())
            self.lastPoint = event.pos()
            painter.end()
            self.showBrush = True
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            draw_action = DrawAction(self, self.lastPoint, event.pos(), self.startImage)
            self.undo_stack.push(draw_action)
            self.update()
            self.parent().setFocus(Qt.MouseFocusReason)
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        fillColor = self.brushColor  # 채울 색상 설정
        image = self.label.toImage()
        fill_action = FillAction(self, event.pos(), fillColor, image)
        self.undo_stack.push(fill_action)
        self.update()

    def mouseLeaveEvent(self, event):
        self.showBrush = False
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Plus:
            self.brushSize += 1
        if event.key() == Qt.Key_Minus:
            self.brushSize = max(1, self.brushSize - 1)

    def setBrushColor(self, color):
        # color is #RRGGBB
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

        width, height = image.width(), image.height()
        stack = [(x, y)]

        while stack:
            x, y = stack.pop()
            currentColor = image.pixelColor(x, y)
            
            if currentColor == targetColor:
                image.setPixelColor(x, y, newColor)

                if x > 0:
                    stack.append((x - 1, y))
                if x < width - 1:
                    stack.append((x + 1, y))
                if y > 0:
                    stack.append((x, y - 1))
                if y < height - 1:
                    stack.append((x, y + 1))
    
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

        # Assert that the number of images and masks are equal
        assert len(self.img_files) == len(self.mask_files)

        self.initUI()

    def initUI(self):
        #self.setFixedSize(1592, 903)
        layout = QVBoxLayout()

        self.img_label = QLabel(self)
        self.canvas = DrawingWidget(self)
        #self.canvas.actionPerformed.connect(self.onActionPerformed)
        self.loadImages()

        # Horizontal layout for buttons
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

        # Horizontal layout for images
        hbox = QHBoxLayout()
        hbox.addWidget(self.img_label)
        hbox.addWidget(self.canvas)

        # add slider that controls brush size
        self.brush_slider = QSlider(Qt.Vertical, self)
        self.brush_slider.setMinimum(1)
        self.brush_slider.setMaximum(50)
        self.brush_slider.setValue(5)
        self.brush_slider.valueChanged.connect(self.canvas.setBrushSize)
        hbox.addWidget(self.brush_slider)

        layout.addLayout(hbox)

        # 슬라이더 추가
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(50)  # 초기값 50%로 설정
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

        # print fixed window size
    
    
    def loadImages(self):
        if self.img_files:
            img_path = os.path.join("./img", self.img_files[self.img_index])
            img_pixmap = QPixmap(img_path)
            scaled_img_pixmap = img_pixmap.scaled(512, 512, Qt.KeepAspectRatio)
            self.img_label.setPixmap(scaled_img_pixmap)

            # Canvas에 이미지를 표시
            self.canvas.setImagePixmap(img_pixmap)

        if self.mask_files:
            mask_path = os.path.join("./mask", self.mask_files[self.mask_index])
            self.mask_pixmap = QPixmap(mask_path)

            # Canvas에 mask 이미지를 표시
            self.canvas.setLabelPixmap(self.mask_pixmap)
    
    # 슬라이더 값에 따라 투명도 업데이트
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
        # Add color button to the layout
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
            print("Left bracket key pressed")
            self.canvas.setBrushSize(self.canvas.brushSize - 10)
            self.canvas.update()
            self.brush_slider.setValue(self.canvas.brushSize)
        if event.key() == Qt.Key_BracketRight:
            print("Right bracket key pressed")
            self.canvas.setBrushSize(self.canvas.brushSize + 10)
            self.canvas.update()
            self.brush_slider.setValue(self.canvas.brushSize)
        # < and > keys
        if event.key() == Qt.Key_Comma:
            print("Comma key pressed")
            self.saveLabel()
            self.prevImage()
        if event.key() == Qt.Key_Period:
            print("Period key pressed")
            self.saveLabel()
            self.nextImage()
        # ctrl + s to save
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_S:
            print("Ctrl + S key pressed")
            self.saveLabel()
        # - = for changing opacity
        if event.key() == Qt.Key_Minus:
            print("Minus key pressed")
            self.opacity_slider.setValue(self.opacity_slider.value() - 10)
        if event.key() == Qt.Key_Equal:
            print("Equal key pressed")
            self.opacity_slider.setValue(self.opacity_slider.value() + 10)
        # press c to clear canvas
        if event.key() == Qt.Key_C:
            print("C key pressed")
            self.canvas.clearCanvas()
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Z :
            self.canvas.undo_stack.undo()
            self.canvas.update()
        if event.key() == event.modifiers() & Qt.ControlModifier and Qt.Key_Y :
            self.canvas.undo_stack.redo()
            self.canvas.update()
        # number to change color
        for i in range(6):
            if event.key() == Qt.Key_1 + i:
                self.color_buttons[i].click()
                print(self.size())


    def saveLabel(self):
        print(f"Saving label {os.path.join('./mask', self.mask_files[self.mask_index])}")
        self.canvas.saveLabel(os.path.join('./mask', self.mask_files[self.mask_index]))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageViewer()
    ex.show()
    sys.exit(app.exec_())
