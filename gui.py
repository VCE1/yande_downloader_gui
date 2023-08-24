import logging
import sys
import os
import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QMessageBox, QWidget, QCheckBox
from PyQt5.QtGui import QIcon, QPixmap, QPalette, QColor, QFont
from PyQt5.QtCore import QThreadPool, QRunnable, QObject, pyqtSignal, QRect, Qt

from download import Downloader

class LogHandler(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)

class DownloadWorkerSignals(QObject):
    finished = pyqtSignal()
    log = pyqtSignal(str)
    download_finished = pyqtSignal()

class DownloadWorker(QRunnable):
    def __init__(self, directory, search_tag, start_page, end_page, download_original, limits):
        super().__init__()
        self.directory = directory
        self.search_tag = search_tag
        self.start_page = start_page
        self.end_page = end_page
        self.download_original = download_original
        self.limits = limits
        self.signals = DownloadWorkerSignals()

    def run(self):
        downloader = Downloader()
        downloader.log_signal.connect(self.signals.log)
        downloader.finished_signal.connect(self.signals.finished)
        downloader.setup(self.directory, self.search_tag, self.start_page, self.end_page, self.download_original)
        downloader.download_images(self.limits)
        self.signals.download_finished.emit()
        self.signals.finished.emit()

class YandeDownload(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_worker = None
        self.setWindowTitle("我直接一个卡哇伊")
        self.setGeometry(100, 100, 1251, 805)

        self.init_ui()

        # 在屏幕上居中显示窗口
        self.center_window()

        log_handler = LogHandler(self.log_text)
        log_handler.setLevel(logging.INFO)
        logging.root.addHandler(log_handler)

    def init_ui(self):
        self.setFixedSize(1251, 805)

        self.background_label = QLabel(self)
        self.background_label.setGeometry(0, 0, 1251, 805)
        self.setBackgroundImage("background.jpg")

        self.tag_label = QLabel("搜索标签:", self)
        self.tag_entry = QLineEdit(self)
        self.start_page_label = QLabel("起始页码:", self)
        self.start_page_entry = QLineEdit(self)
        self.end_page_label = QLabel("结束页码:", self)
        self.end_page_entry = QLineEdit(self)
        self.directory_label = QLabel("下载目录:", self)
        self.directory_entry = QLineEdit(self)
        self.original_checkbutton = QCheckBox("下载原图", self)
        self.original_checkbutton.setChecked(True)  # 设置默认勾选状态
        self.limits_label = QLabel("每页图片数量:", self)
        self.limits_entry = QLineEdit(self)
        self.limits_entry.setText("40")  # 设置默认值
        self.log_text = QTextEdit(self)
        self.download_button = QPushButton("开始下载", self)

        self.directory_button = QPushButton("选择目录", self)
        self.directory_button.clicked.connect(self.select_directory)

        self.right_layout = QVBoxLayout()
        self.right_layout.addWidget(self.tag_label)
        self.right_layout.addWidget(self.tag_entry)
        self.right_layout.addWidget(self.start_page_label)
        self.right_layout.addWidget(self.start_page_entry)
        self.right_layout.addWidget(self.end_page_label)
        self.right_layout.addWidget(self.end_page_entry)
        self.right_layout.addWidget(self.directory_label)
        self.right_layout.addWidget(self.directory_entry)
        self.right_layout.addWidget(self.directory_button)
        self.right_layout.addWidget(self.original_checkbutton)
        self.right_layout.addWidget(self.limits_label)
        self.right_layout.addWidget(self.limits_entry)
        self.right_layout.addWidget(self.download_button)
        self.right_layout.addWidget(self.log_text)

        self.main_widget = QWidget(self)
        self.main_widget.setGeometry(QRect(834, 0, 417, 805))
        self.main_widget.setLayout(self.right_layout)

        self.log_text.setGeometry(0, 537, 417, 268)
        self.log_text.setReadOnly(True)

        # 设置字体
        font = QFont("Microsoft YaHei")
        self.tag_label.setFont(font)
        self.tag_entry.setFont(font)
        self.start_page_label.setFont(font)
        self.start_page_entry.setFont(font)
        self.end_page_label.setFont(font)
        self.end_page_entry.setFont(font)
        self.directory_label.setFont(font)
        self.directory_entry.setFont(font)
        self.original_checkbutton.setFont(font)
        self.limits_label.setFont(font)
        self.limits_entry.setFont(font)
        self.log_text.setFont(font)
        self.download_button.setFont(font)
        self.directory_button.setFont(font)

        # 设置按钮颜色
        palette = self.tag_entry.palette()
        palette.setColor(QPalette.Base, QColor(255, 255, 255, 127))  # 设置为80%透明白色
        self.tag_entry.setPalette(palette)

        palette = self.directory_entry.palette()
        palette.setColor(QPalette.Base, QColor(255, 255, 255, 127))  # 设置为80%透明白色
        self.directory_entry.setPalette(palette)

        palette = self.start_page_entry.palette()
        palette.setColor(QPalette.Base, QColor(255, 255, 255, 127))  # 设置为80%透明白色
        self.start_page_entry.setPalette(palette)

        palette = self.end_page_entry.palette()
        palette.setColor(QPalette.Base, QColor(255, 255, 255, 127))  # 设置为80%透明白色
        self.end_page_entry.setPalette(palette)

        palette = self.log_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 255, 255, 204))  # 设置为80%透明白色
        self.log_text.setPalette(palette)

        # 将按钮与相应的函数连接起来
        self.download_button.clicked.connect(self.start_download)

    def center_window(self):
        # 获取屏幕几何信息
        screen_geometry = QApplication.desktop().screenGeometry()

        # 计算屏幕中心点
        center_point = screen_geometry.center()

        # 计算窗口左上角的位置
        window_position = self.frameGeometry()
        window_position.moveCenter(center_point)

        # 将窗口移动到计算出的位置
        self.move(window_position.topLeft())

    def download_finished(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("下载完成")
        msg_box.setText("下载完成！")
        msg_box.addButton(QMessageBox.Ok)
        msg_box.exec_()

        self.download_worker = None  # 重置下载worker

    def setBackgroundImage(self, image_path):
        pixmap = QPixmap(image_path)
        self.background_label.setPixmap(pixmap)
        self.background_label.setScaledContents(True)
        app = QApplication.instance()
        app.setWindowIcon(QIcon("favicon.ico"))

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择目录")
        if directory:
            self.directory_entry.setText(directory)

    def start_download(self):
        if self.download_worker is not None:
            self.log_text.append("已有下载任务在进行中...")
            return

        directory = self.directory_entry.text()
        search_tag = self.tag_entry.text()
        start_page = self.start_page_entry.text()
        end_page = self.end_page_entry.text()
        download_original = self.original_checkbutton.isChecked()
        limits = int(self.limits_entry.text())

        if not directory:
            directory = os.path.join(os.getcwd(), datetime.date.today().strftime('%Y%m%d') + '_' + search_tag)

        if not os.path.exists(directory):
            os.makedirs(directory)

        if not search_tag:
            self.log_text.append("请输入搜索标签。")
            return

        if not start_page or not end_page:
            self.log_text.append("请输入起始页码和结束页码。")
            return

        self.log_text.clear()

        self.download_worker = DownloadWorker(directory, search_tag, int(start_page), int(end_page), download_original, limits)
        self.download_worker.signals.log.connect(self.log_text.append)
        self.download_worker.signals.download_finished.connect(self.download_finished)

        # 在后台线程池中启动下载 worker
        QThreadPool.globalInstance().start(self.download_worker)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = YandeDownload()
    window.show()
    sys.exit(app.exec_())
