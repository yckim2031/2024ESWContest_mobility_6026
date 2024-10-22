import sys
import os
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QLineEdit
from PyQt5.QtCore import Qt, QTimer, QUrl, QPropertyAnimation, QThread, pyqtSignal
from PyQt5.QtCore import Qt, QTimer, QUrl, QPropertyAnimation, QThread, pyqtSignal
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtGui import QFont, QPixmap, QMovie, QPainter
import time
import playsound
from ecg_id_main import verification
import queue
import threading
import csv

class ECGWorker(QThread):
    result_ready = pyqtSignal(list)
    
    def __init__(self, mode_queue):
        super(ECGWorker, self).__init__()
        self.mode_queue = mode_queue
        self.stop_event = threading.Event()
        
    def run(self):
        print("ECGWorker start.")
        result = verification(self.mode_queue, self.stop_event)
        if result is not None:
            self.result_ready.emit(result)

    def stop(self):
        self.stop_event.set()
        self.quit()
        self.wait()

class DriverMoitoringApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.mode_queue = queue.Queue()
        self.worker = ECGWorker(self.mode_queue)
        self.worker.result_ready.connect(self.handle_result)
        self.worker.start()

        self.background_image = None
        self.show_background_image = True

    def get_path(self, filename):
        base_path = os.path.dirname(__file__)
        return os.path.join(base_path, filename)

    def initUI(self):
        self.setWindowTitle('AI-SW')

        self.is_vedio_finished = False

        self.movie = QMovie(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/gif/1_AI_SW_HYUNDAI.gif"))

        self.videoWidget = QLabel(self)
        self.videoWidget.setMovie(self.movie)
        self.videoWidget.setScaledContents(True)
        
        self.movie.start()

        self.setCentralWidget(self.videoWidget)

        self.movie.frameChanged.connect(self.check_if_finished)

        self.showFullScreen()
        playsound.playsound("/home/jhhan/Downloads/ESW_UI/ui/mp3/AI_SW_hyundai.mp3")

    def check_if_finished(self, frame_number):
        if not self.is_vedio_finished and self.movie.frameCount() > 0 and frame_number == self.movie.frameCount() - 1:
            self.on_video_finished()

    def on_video_finished(self):
        self.is_vedio_finished = True
        self.show_touch_wheel_screen()

    def show_touch_wheel_screen(self):
        self.clear_layout()
        
        self.background_image = QPixmap(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/png/AI_SW_LED.png"))
        '''
        self.background_label = QLabel(self)
        pixmap = QPixmap(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/png/AI_SW_LED.png"))
        self.background_label.setPixmap(pixmap)
        self.background_label.setScaledContents(True)
        '''
        self.label = QLabel('Put your hands on the steering wheel.', self)
        self.label.setFont(QFont("Arial", 24, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)

        self.layout = QVBoxLayout()
        #self.layout.addWidget(self.background_label)
        self.layout.addWidget(self.label)

        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

        QTimer.singleShot(3000, self.mode_select)

    def mode_select(self):
        self.clear_layout()

        self.background_image = QPixmap("/home/jhhan/Downloads/ESW_UI/ui/png/4_AI_SW_mode_select.png")

        layout = QVBoxLayout()

        label = QLabel("Please press 'V' if you want to identify the driver ID, \n 'R' if you want to register a new driver ID.", self)
        label.setStyleSheet("color: white; font-size: 24px;")
        label.setAlignment(Qt.AlignCenter)

        v_button = QPushButton("V", self)
        v_button.setStyleSheet("padding: 10px; font-size: 18px;")
        
        r_button = QPushButton("R", self)
        r_button.setStyleSheet("padding: 10px; font-size: 18px;")

        layout.addWidget(label)
        layout.addWidget(v_button)
        layout.addWidget(r_button)
        layout.setAlignment(Qt.AlignCenter)

        v_button.clicked.connect(lambda: self.send_mode_to_queue('v'))
        r_button.clicked.connect(self.password_input_screen)

        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
    def send_mode_to_queue(self, mode):
        self.mode_queue.put(mode)
        print(f"Mode '{mode}' sent to background thread.")
        self.verification_screen(mode)

    def verification_screen(self, mode):
        self.clear_layout()

        self.background_image = QPixmap(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/png/AI_SW_LED.png"))
        '''
        self.background_label = QLabel(self)
        pixmap = QPixmap(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/png/AI_SW_LED.png"))
        self.background_label.setPixmap(pixmap)
        self.background_label.setScaledContents(True)
        '''
        if mode == 'v':
            new_label = QLabel("Put your hands on the steering wheel.")
            new_label.setFont(QFont("Arial", 24, QFont.Bold))
            new_label.setAlignment(Qt.AlignCenter)

            self.layout = QVBoxLayout()
            #self.layout.addWidget(self.background_label, alignment=Qt.AlignCenter)
            self.layout.addWidget(new_label, alignment=Qt.AlignCenter)

            central_widget = QWidget()
            central_widget.setLayout(self.layout)
            self.setCentralWidget(central_widget)

            QTimer.singleShot(5000, self.verifying)

    def verifying(self):
        self.clear_layout()

        self.movie = QMovie(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/gif/3_AI_SW_ECG_PPG.gif"))

        self.videoWidget = QLabel(self)
        self.videoWidget.setMovie(self.movie)
        self.videoWidget.setScaledContents(True)
        self.setCentralWidget(self.videoWidget)

        self.showFullScreen()

        self.movie.start()

        self.worker.result_ready.connect(self.handle_result)
        print("Verifying started... Waiting for result.")

    def password_input_screen(self):
        self.clear_layout()
        self.label = QLabel('Please enter the password.', self)
        self.label.setFont(QFont("Arial", 24, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFont(QFont("Arial", 18))
        
        self.submit_button = QPushButton('Submit', self)
        self.submit_button.setFont(QFont("Arial", 18))
        self.submit_button.setFixedSize(150, 50)
        
        self.submit_button.clicked.connect(self.check_password)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.password_input, alignment=Qt.AlignCenter)
        self.layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)

        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

    def check_password(self):
        if self.password_input.text() == "aisw1234":  # password 입력
            self.send_mode_to_queue('r')
        else:
            self.password_error()
            
    def password_error(self):
        self.clear_layout()
        self.label = QLabel('The password is incorrect.\nPlease try again.')
        self.label.setFont(QFont("Arial", 24, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label, alignment=Qt.AlignCenter)

        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

        QTimer.singleShot(1000, self.password_input_screen)

    def handle_result(self, result):
        self.movie.stop()

        file_path = 'verification_result.csv'
        
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(result)
            
        self.clear_layout()
            
        if 1 in result:
            QTimer.singleShot(500, self.engine_start_success)
        else:
            QTimer.singleShot(500, self.engine_start_fail)

    def show_touch_wheel_screen2(self):
        self.clear_layout()

        self.background_image = QPixmap(self.get_path("/home/jhhan/Downloads/ESW_UI/AI_SW_LED.png"))
        '''
        self.background_label = QLabel(self)
        pixmap = QPixmap(self.get_path("/home/jhhan/Downloads/ESW_UI/AI_SW_LED.png"))
        self.background_label.setPixmap(pixmap)
        self.background_label.setScaledContents(True)
        '''
        self.label = QLabel('Place your hand on the steering wheel\nto register your driver ID..', self)
        self.label.setFont(QFont("Arial", 24, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)

        self.layout = QVBoxLayout()
        #self.layout.addWidget(self.background_label)
        self.layout.addWidget(self.label)

        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)
                                            
        QTimer.singleShot(10000, self.success_registration_screen)   
        
    def success_registration_screen(self):
        self.clear_layout()
        self.label = QLabel('Driver ID registration was successful.', self)
        self.label.setFont(QFont("Arial", 24, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)

        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)
        
        QTimer.singleShot(3000, self.mode_select)
        
    def engine_start_success(self):
        self.clear_layout()
        self.show_background_image = False

        file_path = 'verification_result.csv'

        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                reader = csv.reader(file)
                rows = next(reader)

                if '1' in rows:
                    i = rows.index('1')
                    message = f"Hello, Person {i+1}, drive safely!"
                else:
                    message = f"Start the engine. Drive safely!"
        else:
            message = f"Start the engine. Drive safely!"
                
        self.label = QLabel(message, self)
        self.label.setFont(QFont("Arial", 24, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white;")
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: black;")
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

        self.fade_out_animation(self.label, 1000)
        QTimer.singleShot(1000, self.play_video2)

    def fade_out_animation(self, widget, duration):
        self.show_background_image = False
        self.animation = QPropertyAnimation(widget, b"windowOpacity")
        self.animation.setDuration(duration)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.start()

    def play_video2(self):
        self.clear_layout()
        self.movie = QMovie(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/gif/2_AI_SW_Cluster.gif"))
       
        self.show_background_image = False

        self.videoWidget = QLabel(self)
        self.videoWidget.setMovie(self.movie)
        self.videoWidget.setScaledContents(True)
        self.setCentralWidget(self.videoWidget)

        #self.layout.addWidget(self.videoWidget)

        self.showFullScreen()

        self.movie.start()
        playsound.playsound("/home/jhhan/Downloads/ESW_UI/ui/mp3/AI_SW.mp3")
        QTimer.singleShot(500, self.play_audio)

    def play_audio(self):
        audio_url = QUrl.fromLocalFile(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/mp3/AI_SW.mp3"))
        self.audio_player = QMediaPlayer()
        self.audio_player.setMedia(QMediaContent(audio_url))
        self.audio_player.play()

    def engine_start_fail(self):
        self.clear_layout()

        self.background_image = QPixmap(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/png/AI_SW_catch.png"))
        '''
        self.background_label = QLabel(self)
        pixmap = QPixmap(self.get_path("/home/jhhan/Downloads/ESW_UI/ui/png/AI_SW_catch.png"))
        self.background_label.setPixmap(pixmap)
        self.background_label.setScaledContents(True)
        '''
        self.label = QLabel('You cannot start the engine.', self)
        self.label.setFont(QFont("Arial", 24, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)

        self.layout = QVBoxLayout()
        #self.layout.addWidget(self.background_label)
        self.layout.addWidget(self.label)

        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

    def paintEvent(self, event):
        if self.show_background_image and self.background_image:
            painter = QPainter(self)
            painter.drawPixmap(self.rect(), self.background_image)

    def closeEvent(self, event):
        if hasattr(self, 'worker'):
            self.worker.stop()
        event.accept()

    def clear_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DriverMoitoringApp()
    ex.show()
    sys.exit(app.exec_())
