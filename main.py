import sys
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QSlider, QLabel, QFileDialog,
                           QStatusBar, QSpinBox)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QPalette
from PIL import Image
import cv2
import os

class CustomSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.setFixedWidth(45)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

class PreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.image = None
        self.contours = None
        self.threshold = 0.5
        self.precision = 0.01
        self.expansion = 0
        self.scale = 1.0  # 缩放比例
        self.offset_x = 0  # 平移偏移量
        self.offset_y = 0
        self.last_mouse_pos = None  # 用于跟踪鼠标移动
        self.setBackgroundRole(QPalette.ColorRole.Base)
        self.setAutoFillBackground(True)
        self.setMouseTracking(True)  # 启用鼠标跟踪
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)  # 允许接收滚轮事件

    def set_image(self, image):
        if isinstance(image, Image.Image):
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            data = image.tobytes('raw', 'RGBA')
            self.image = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888)
        self.update()

    def set_threshold(self, value):
        self.threshold = value / 100.0
        self.update_contours()
        self.update()
        
    def set_precision(self, value):
        self.precision = value / 1000.0
        self.update_contours()
        self.update()

    def set_expansion(self, value):  # 添加边界扩展设置方法
        self.expansion = value
        self.update_contours()
        self.update()

    def update_contours(self):
        if self.image is None:
            return

        # 转换QImage为numpy数组
        width = self.image.width()
        height = self.image.height()
        ptr = self.image.bits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))

        # 获取alpha通道
        alpha = arr[:, :, 3]

        # 二值化
        _, binary = cv2.threshold(alpha, int(self.threshold * 255), 255, cv2.THRESH_BINARY)

        # 如果有扩展值，进行膨胀操作
        if self.expansion > 0:
            kernel_size = 2 * self.expansion + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            binary = cv2.dilate(binary, kernel, iterations=1)

        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 简化轮廓
        simplified_contours = []
        for contour in contours:
            epsilon = self.precision * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            simplified_contours.append(approx)

        self.contours = simplified_contours

    def wheelEvent(self, event):
        # 处理滚轮缩放
        delta = event.angleDelta().y()
        if delta > 0:
            self.scale *= 1.1  # 放大
        else:
            self.scale *= 0.9  # 缩小
        self.scale = max(0.1, min(5.0, self.scale))  # 限制缩放范围
        self.update()

    def mousePressEvent(self, event):
        # 开始拖动
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.pos()

    def mouseReleaseEvent(self, event):
        # 结束拖动
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = None

    def mouseMoveEvent(self, event):
        # 处理拖动平移
        if self.last_mouse_pos is not None:
            delta = event.pos() - self.last_mouse_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()

    def paintEvent(self, event):
        if self.image is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 计算基础缩放比例以适应窗口
        base_scale = min(self.width() / self.image.width(),
                        self.height() / self.image.height())
        
        # 应用用户的缩放和平移
        total_scale = base_scale * self.scale
        
        # 计算图像绘制的位置
        image_width = self.image.width() * total_scale
        image_height = self.image.height() * total_scale
        
        # 基础居中位置
        base_x = (self.width() - image_width) / 2
        base_y = (self.height() - image_height) / 2
        
        # 应用平移偏移
        x = base_x + self.offset_x
        y = base_y + self.offset_y

        # 绘制图像
        painter.drawImage(QRectF(x, y, image_width, image_height), self.image)

        # 绘制轮廓
        if self.contours is not None:
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            for contour in self.contours:
                # 转换轮廓点并应用缩放和平移
                points = []
                for point in contour:
                    px = x + point[0][0] * total_scale
                    py = y + point[0][1] * total_scale
                    points.append((px, py))

                # 绘制轮廓
                for i in range(len(points)):
                    start = points[i]
                    end = points[(i + 1) % len(points)]
                    painter.drawLine(int(start[0]), int(start[1]),
                                   int(end[0]), int(end[1]))

    def resetView(self):
        # 重置视图状态
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PNG转3D网格工具")
        self.setMinimumSize(800, 600)
        
        # 设置状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_layout.setSpacing(15)
        
        # 添加按钮
        self.import_btn = QPushButton("导入PNG")
        self.import_btn.setMinimumHeight(30)
        self.import_btn.clicked.connect(self.import_png)
        self.export_btn = QPushButton("导出模型")
        self.export_btn.setMinimumHeight(30)
        self.export_btn.clicked.connect(self.export_model)
        self.export_btn.setEnabled(False)

        # 重置视图按钮
        self.reset_view_btn = QPushButton("重置视图")
        self.reset_view_btn.setMinimumHeight(30)
        self.reset_view_btn.clicked.connect(self.reset_view)
        self.reset_view_btn.setEnabled(False)
        
        # 透明度阈值滑块
        threshold_group = QVBoxLayout()
        threshold_group.setSpacing(5)
        threshold_label = QLabel("透明度阈值:")
        threshold_control = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)
        self.threshold_value = CustomSpinBox()
        self.threshold_value.setRange(0, 100)
        self.threshold_value.setValue(50)
        threshold_control.addWidget(self.threshold_slider)
        threshold_control.addWidget(self.threshold_value)
        threshold_group.addWidget(threshold_label)
        threshold_group.addLayout(threshold_control)
        
        # 边界精度滑块
        precision_group = QVBoxLayout()
        precision_group.setSpacing(5)
        precision_label = QLabel("边界精度:")
        precision_control = QHBoxLayout()
        self.precision_slider = QSlider(Qt.Orientation.Horizontal)
        self.precision_slider.setRange(1, 100)
        self.precision_slider.setValue(10)
        self.precision_value = CustomSpinBox()
        self.precision_value.setRange(1, 100)
        self.precision_value.setValue(10)
        precision_control.addWidget(self.precision_slider)
        precision_control.addWidget(self.precision_value)
        precision_group.addWidget(precision_label)
        precision_group.addLayout(precision_control)

        # 边界扩展滑块
        expansion_group = QVBoxLayout()
        expansion_group.setSpacing(5)
        expansion_label = QLabel("边界扩展:")
        expansion_control = QHBoxLayout()
        self.expansion_slider = QSlider(Qt.Orientation.Horizontal)
        self.expansion_slider.setRange(0, 20)
        self.expansion_slider.setValue(0)
        self.expansion_value = CustomSpinBox()
        self.expansion_value.setRange(0, 20)
        self.expansion_value.setValue(0)
        expansion_control.addWidget(self.expansion_slider)
        expansion_control.addWidget(self.expansion_value)
        expansion_group.addWidget(expansion_label)
        expansion_group.addLayout(expansion_control)
        
        # 连接滑块和数值框
        self.threshold_slider.valueChanged.connect(self.threshold_value.setValue)
        self.threshold_value.valueChanged.connect(self.threshold_slider.setValue)
        self.threshold_slider.valueChanged.connect(self.update_preview)
        
        self.precision_slider.valueChanged.connect(self.precision_value.setValue)
        self.precision_value.valueChanged.connect(self.precision_slider.setValue)
        self.precision_slider.valueChanged.connect(self.update_preview)

        self.expansion_slider.valueChanged.connect(self.expansion_value.setValue)
        self.expansion_value.valueChanged.connect(self.expansion_slider.setValue)
        self.expansion_slider.valueChanged.connect(self.update_preview)
        
        # 设置控制面板的最小宽度
        control_panel.setMinimumWidth(300)
        
        # 添加控件到控制面板
        control_layout.addWidget(self.import_btn)
        control_layout.addLayout(threshold_group)
        control_layout.addLayout(precision_group)
        control_layout.addLayout(expansion_group)
        control_layout.addWidget(self.export_btn)
        control_layout.addWidget(self.reset_view_btn)
        control_layout.addStretch()
        
        # 预览窗口
        self.preview_widget = PreviewWidget()
        
        # 添加到主布局
        layout.addWidget(control_panel, 1)
        layout.addWidget(self.preview_widget, 4)
        
        # 保存当前图像
        self.current_image = None
        
    def reset_view(self):
        self.preview_widget.resetView()
        
    def import_png(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择PNG文件", "", "PNG文件 (*.png)")
        if file_name:
            self.statusBar.showMessage(f"正在处理图片: {file_name}")
            self.process_image(file_name)
            
    def process_image(self, file_path):
        try:
            self.current_image = Image.open(file_path)
            self.preview_widget.set_image(self.current_image)
            self.update_preview()
            self.export_btn.setEnabled(True)
            self.reset_view_btn.setEnabled(True)  # 启用重置视图按钮
            self.statusBar.showMessage("图片加载完成")
        except Exception as e:
            self.statusBar.showMessage(f"处理图像时出错: {str(e)}")
            
    def update_preview(self):
        if self.current_image is None:
            return
        self.preview_widget.set_threshold(self.threshold_slider.value())
        self.preview_widget.set_precision(self.precision_slider.value())
        self.preview_widget.set_expansion(self.expansion_slider.value())
            
    def export_model(self):
        if self.current_image is None or self.preview_widget.contours is None:
            return
            
        file_name, _ = QFileDialog.getSaveFileName(
            self, "保存模型", "", "OBJ文件 (*.obj)")
        if file_name:
            try:
                self.statusBar.showMessage("正在导出模型...")
                
                # 获取轮廓点
                contours = self.preview_widget.contours
                
                # 创建3D模型
                vertices = []
                faces = []
                
                # 对每个轮廓创建一个面片
                for contour in contours:
                    start_idx = len(vertices)
                    
                    # 添加轮廓点作为顶点
                    for point in contour:
                        x = (point[0][0] / self.current_image.width - 0.5) * 2
                        y = -(point[0][1] / self.current_image.height - 0.5) * 2
                        vertices.append((x, y, 0))
                    
                    # 使用三角剖分创建面片
                    points = np.array([point[0] for point in contour])
                    try:
                        # 计算三角剖分
                        triangles = cv2.Subdiv2D()
                        rect = (0, 0, self.current_image.width, self.current_image.height)
                        triangles.initDelaunay(rect)
                        for point in points:
                            triangles.insert((float(point[0]), float(point[1])))
                        
                        # 获取三角形列表
                        triangle_list = triangles.getTriangleList()
                        
                        # 将三角形顶点映射回顶点索引
                        for triangle in triangle_list:
                            tri_points = [(triangle[i], triangle[i+1]) for i in range(0, 6, 2)]
                            indices = []
                            for tri_point in tri_points:
                                # 找到最近的轮��点
                                dists = np.sqrt(np.sum((points - tri_point) ** 2, axis=1))
                                idx = np.argmin(dists)
                                indices.append(start_idx + idx)
                            
                            # 检查三角形是否在轮廓内
                            center = np.mean(tri_points, axis=0)
                            if cv2.pointPolygonTest(contour, (center[0], center[1]), False) >= 0:
                                faces.append(tuple(indices))
                    except:
                        # 如果三角剖分失败，使用扇形三角化
                        # 计算轮廓的中心点
                        center_point = np.mean(points, axis=0)
                        x = (center_point[0] / self.current_image.width - 0.5) * 2
                        y = -(center_point[1] / self.current_image.height - 0.5) * 2
                        center_idx = len(vertices)
                        vertices.append((x, y, 0))
                        
                        # 创建从中心点到轮廓点的三角形
                        num_points = len(contour)
                        for i in range(num_points):
                            i1 = start_idx + i
                            i2 = start_idx + ((i + 1) % num_points)
                            faces.append((center_idx, i1, i2))
                
                # 写入OBJ文件
                with open(file_name, 'w') as f:
                    # 写入顶点
                    for v in vertices:
                        f.write(f"v {v[0]} {v[1]} {v[2]}\n")
                    
                    # 写入面片（OBJ索引从1开始）
                    for face in faces:
                        f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
                
                self.statusBar.showMessage("模型导出完成")
            except Exception as e:
                self.statusBar.showMessage(f"导出模型时出错: {str(e)}")
                print(f"错误详情: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 