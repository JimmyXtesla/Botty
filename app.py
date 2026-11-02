
import sys
import os
import math
import random
import shutil
import datetime
import subprocess
import webbrowser

import pyttsx3
import psutil

from PyQt6.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal, pyqtSlot, QPoint
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen,
    QFont, QRadialGradient
)
from PyQt6.QtWidgets import QApplication, QWidget



APP_NAME = "DR. TESLA"

PURE_WHITE = QColor(255, 255, 255)
DARK = QColor(15, 20, 28)
MUTED = QColor(155, 165, 180)
ACCENT = QColor(0, 220, 195)

WINDOW_WIDTH = 560
WINDOW_HEIGHT = 520

CENTER_X = 280
CENTER_Y = 180




class SpeechWorker(QObject):

    speaking = pyqtSignal(bool)
    status = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.engine = None

    @pyqtSlot(str)
    def speak(self, message):

        try:

            if self.engine is None:

                self.engine = pyttsx3.init()

                self.engine.setProperty("rate", 190)
                self.engine.setProperty("volume", 1.0)

                voices = self.engine.getProperty("voices")

                for voice in voices:

                    if any(
                        name in voice.name.lower()
                        for name in [
                            "zira", "hazel", "female",
                            "susan", "helen", "cathy"
                        ]
                    ):

                        self.engine.setProperty(
                            "voice", voice.id
                        )
                        break

            self.speaking.emit(True)
            self.status.emit("SPEAKING")

            self.engine.say(message)
            self.engine.runAndWait()

        except Exception as error:

            print("Speech error:", error)
            self.status.emit("VOICE ERROR")

        finally:

            self.speaking.emit(False)
            self.finished.emit()





class DrTeslaHUD(QWidget):

    speech_requested = pyqtSignal(str)

    def __init__(self):

        super().__init__()

        self.setWindowTitle(APP_NAME)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_NoSystemBackground,
            True
        )

        self.setMouseTracking(True)

        # STATE
        self.is_speaking = False
        self.is_blinking = False
        self.radial_menu_open = False

        self.mouth_phase = 0
        self.status_text = "SYSTEM ONLINE"

        self.speech_busy = False

        self.drag_start = None
        self.drag_origin = None
        self.dragged = False

        self.cpu_usage = 0
        self.ram_usage = 0
        self.battery = "N/A"

        self.current_time = ""
        self.current_date = ""

        # RADIAL MENU OPTIONS
        self.menu_options = [
            ("VS Code", "vscode"),
            ("Browser", "browser"),
            ("Explorer", "explorer"),
            ("System", "system"),
            ("Time", "time"),
            ("Notepad", "notepad"),
            ("Motivate", "motivate"),
            ("Exit", "exit")
        ]

  

        self.speech_thread = QThread(self)

        self.speech_worker = SpeechWorker()

        self.speech_worker.moveToThread(
            self.speech_thread
        )

        self.speech_requested.connect(
            self.speech_worker.speak
        )

        self.speech_worker.speaking.connect(
            self.set_speaking
        )

        self.speech_worker.status.connect(
            self.update_status
        )

        self.speech_worker.finished.connect(
            self.speech_finished
        )

        self.speech_thread.start()


        screen = QApplication.primaryScreen().availableGeometry()

        self.move(
            screen.right() - self.width() - 30,
            screen.top() + 30
        )

    

        self.animation_timer = QTimer(self)

        self.animation_timer.timeout.connect(
            self.animate
        )

        self.animation_timer.start(100)

      

        self.telemetry_timer = QTimer(self)

        self.telemetry_timer.timeout.connect(
            self.refresh_telemetry
        )

        self.telemetry_timer.start(2000)

        self.refresh_telemetry()

        QTimer.singleShot(1200, self.greet)

 

    def say(self, message):

        if self.speech_busy:
            return

        self.speech_busy = True

        self.status_text = "PREPARING VOICE..."

        self.speech_requested.emit(message)

        self.update()

    def greet(self):

        hour = datetime.datetime.now().hour

        if hour < 12:
            greeting = "Good morning"
        elif hour < 18:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        messages = [
            f"{greeting}, Boss. Dr. Tesla is online. What are we building today?",
            f"{greeting}, Boss. All systems are ready. What is our next mission?",
            f"{greeting}. Welcome back. Let's build something extraordinary."
        ]

        self.say(random.choice(messages))

    def speech_finished(self):

        self.speech_busy = False

        self.status_text = "DR. TESLA | STANDBY"

        self.update()

    def set_speaking(self, state):

        self.is_speaking = state
        self.update()

    def update_status(self, text):

        self.status_text = text
        self.update()



    def get_menu_rect(self, index):

        # Eight evenly spaced positions around the robot
        angle = math.radians(-90 + index * 45)

        radius = 150

        x = CENTER_X + math.cos(angle) * radius
        y = CENTER_Y + math.sin(angle) * radius

        return (
            int(x - 48),
            int(y - 19),
            96,
            38
        )

    def get_clicked_option(self, position):

        for index, option in enumerate(self.menu_options):

            x, y, width, height = self.get_menu_rect(index)

            if (
                x <= position.x() <= x + width
                and y <= position.y() <= y + height
            ):
                return option[1]

        return None

  

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.RightButton:

            self.radial_menu_open = not self.radial_menu_open
            self.update()
            return

        if event.button() == Qt.MouseButton.LeftButton:

            self.drag_start = event.globalPosition().toPoint()
            self.drag_origin = self.pos()
            self.dragged = False

    def mouseMoveEvent(self, event):

        if (
            self.drag_start is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):

            current = event.globalPosition().toPoint()

            delta = current - self.drag_start

            if delta.manhattanLength() > 5:
                self.dragged = True

            if self.dragged:
                self.move(self.drag_origin + delta)

    def mouseReleaseEvent(self, event):

        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self.drag_start is None:
            return

        position = event.position().toPoint()

        if not self.dragged:

            if self.radial_menu_open:

                option = self.get_clicked_option(position)

                if option:

                    self.radial_menu_open = False
                    self.execute_command(option)

                else:

                    self.radial_menu_open = False

                    if self.is_inside_face(position):
                        self.handle_face_click()

            elif self.is_inside_face(position):

                self.handle_face_click()

        self.drag_start = None
        self.drag_origin = None
        self.dragged = False

        self.update()

    def is_inside_face(self, position):

        dx = position.x() - CENTER_X
        dy = position.y() - CENTER_Y

        return (
            abs(dx) <= 78
            and abs(dy) <= 53
        )

    def handle_face_click(self):

        responses = [
            "Yes Boss? I'm listening.",
            "I'm right here. What do you need?",
            "Ready when you are. Let's get to work.",
            "Systems operational. Give me a challenge.",
            "You have my attention. What's the mission?",
            "Another day to build something remarkable."
        ]

        self.say(random.choice(responses))

  

    def execute_command(self, command):

        if command == "vscode":
            self.open_vscode()

        elif command == "browser":
            webbrowser.open("https://www.google.com")
            self.say("Opening your browser, Boss.")

        elif command == "explorer":
            self.open_explorer()

        elif command == "system":
            self.speak_system_status()

        elif command == "time":
            self.speak_time()

        elif command == "notepad":
            self.open_notepad()

        elif command == "motivate":
            self.motivate()

        elif command == "exit":
            self.close()

   

    def open_vscode(self):

        try:

            code_path = shutil.which("code")

            if code_path:

                subprocess.Popen([code_path])

            else:

                possible_paths = [
                    os.path.expandvars(
                        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"
                    ),
                    os.path.expandvars(
                        r"%PROGRAMFILES%\Microsoft VS Code\Code.exe"
                    ),
                    os.path.expandvars(
                        r"%PROGRAMFILES(X86)%\Microsoft VS Code\Code.exe"
                    )
                ]

                code_path = next(
                    (
                        path for path in possible_paths
                        if os.path.isfile(path)
                    ),
                    None
                )

                if not code_path:
                    self.say(
                        "I couldn't locate Visual Studio Code. "
                        "Please check that it is installed."
                    )
                    return

                subprocess.Popen([code_path])

            self.say("Launching Visual Studio Code, Boss.")

        except Exception as error:

            print("VS Code error:", error)
            self.say("I encountered an error opening Visual Studio Code.")

    def open_notepad(self):

        try:

            subprocess.Popen(["notepad.exe"])
            self.say("Opening Notepad, Boss.")

        except Exception:

            self.say("I couldn't open Notepad.")

    def open_explorer(self):

        try:

            subprocess.Popen(["explorer.exe"])
            self.say("Opening File Explorer, Boss.")

        except Exception:

            self.say("I couldn't open File Explorer.")



    def speak_time(self):

        now = datetime.datetime.now()

        self.say(
            f"The current time is {now.strftime('%I:%M %p')}. "
            f"Today is {now.strftime('%A, %B %d, %Y')}."
        )

    def speak_system_status(self):

        cpu = psutil.cpu_percent(interval=None)

        ram = psutil.virtual_memory()

        message = (
            f"System status report. "
            f"CPU utilization is {cpu} percent. "
            f"Memory utilization is {ram.percent} percent. "
            f"You have {ram.available / (1024 ** 3):.1f} "
            f"gigabytes of available memory."
        )

        self.say(message)

    def motivate(self):

        messages = [
            "Great things are built through consistent execution.",
            "Focus on the work. Build the fundamentals. Let the results speak.",
            "Every complex system begins with a working implementation. Start building.",
            "Do not confuse being busy with making progress. Choose one important task and finish it."
        ]

        self.say(random.choice(messages))



    def refresh_telemetry(self):

        now = datetime.datetime.now()

        self.current_time = now.strftime("%H:%M:%S")

        self.current_date = now.strftime("%A, %d %B %Y")

        self.cpu_usage = psutil.cpu_percent()

        self.ram_usage = psutil.virtual_memory().percent

        battery = psutil.sensors_battery()

        self.battery = (
            f"{battery.percent}%"
            if battery else "N/A"
        )

        self.update()



    def animate(self):

        self.mouth_phase += 1

        if not self.is_speaking and not self.is_blinking:

            if random.random() < 0.015:

                self.is_blinking = True

                QTimer.singleShot(
                    140,
                    self.stop_blink
                )

        self.update()

    def stop_blink(self):

        self.is_blinking = False
        self.update()

   

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        painter.setRenderHint(
            QPainter.RenderHint.TextAntialiasing
        )

        cx = CENTER_X
        cy = CENTER_Y

    

        glow = QRadialGradient(cx, cy, 110)

        glow.setColorAt(0, QColor(0, 220, 195, 42))
        glow.setColorAt(0.5, QColor(0, 220, 195, 14))
        glow.setColorAt(1, QColor(0, 220, 195, 0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))

        painter.drawEllipse(
            int(cx - 110),
            int(cy - 110),
            220,
            220
        )

      

        if self.radial_menu_open:

            painter.setPen(
                QPen(
                    QColor(0, 220, 195, 65),
                    1,
                    Qt.PenStyle.DashLine
                )
            )

            for index in range(8):

                angle = math.radians(-90 + index * 45)

                end_x = cx + math.cos(angle) * 105
                end_y = cy + math.sin(angle) * 105

                painter.drawLine(
                    int(cx),
                    int(cy),
                    int(end_x),
                    int(end_y)
                )

  

        painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(QBrush(PURE_WHITE))

        painter.drawRoundedRect(
            int(cx - 78),
            int(cy - 53),
            156,
            106,
            48,
            48
        )

    

        eye_height = 3 if self.is_blinking else 18

        painter.setBrush(QBrush(DARK))

        for eye_x in [cx - 35, cx + 35]:

            painter.drawRoundedRect(
                int(eye_x - 7),
                int(cy - eye_height / 2),
                14,
                eye_height,
                6,
                6
            )

     

        if self.is_speaking:

            mouth_height = (
                5 + abs((self.mouth_phase % 6) - 3) * 3
            )

        else:

            mouth_height = 3

        painter.setBrush(QBrush(DARK))

        painter.drawRoundedRect(
            int(cx - 13),
            int(cy + 26),
            26,
            mouth_height,
            5,
            5
        )

      

        if self.radial_menu_open:

            for index, (label, command) in enumerate(
                self.menu_options
            ):

                x, y, width, height = self.get_menu_rect(index)

                # Small dark translucent command capsules
                painter.setPen(
                    QPen(QColor(255, 255, 255, 45), 1)
                )

                painter.setBrush(
                    QBrush(QColor(20, 25, 35, 225))
                )

                painter.drawRoundedRect(
                    x, y, width, height, 12, 12
                )

                # Command labels
                painter.setPen(PURE_WHITE)

                painter.setFont(
                    QFont("Segoe UI", 9, QFont.Weight.DemiBold)
                )

                painter.drawText(
                    x, y, width, height,
                    Qt.AlignmentFlag.AlignCenter,
                    label
                )

      

        painter.setPen(PURE_WHITE)

        painter.setFont(
            QFont("Segoe UI", 12, QFont.Weight.Bold)
        )

        painter.drawText(
            0, 385, WINDOW_WIDTH, 22,
            Qt.AlignmentFlag.AlignCenter,
            "DR. TESLA"
        )

    

        painter.setPen(ACCENT)

        painter.setFont(
            QFont("Segoe UI", 8, QFont.Weight.Bold)
        )

        painter.drawText(
            0, 408, WINDOW_WIDTH, 20,
            Qt.AlignmentFlag.AlignCenter,
            self.status_text
        )

   

        painter.setPen(MUTED)

        painter.setFont(
            QFont("Segoe UI", 8)
        )

        telemetry = (
            f"CPU {self.cpu_usage:.0f}%     "
            f"RAM {self.ram_usage:.0f}%     "
            f"BAT {self.battery}"
        )

        painter.drawText(
            0, 450, WINDOW_WIDTH, 20,
            Qt.AlignmentFlag.AlignCenter,
            telemetry
        )

     

        painter.setPen(PURE_WHITE)

        painter.setFont(
            QFont("Segoe UI", 17, QFont.Weight.DemiBold)
        )

        painter.drawText(
            0, 485, WINDOW_WIDTH, 25,
            Qt.AlignmentFlag.AlignCenter,
            self.current_time
        )

        painter.setPen(MUTED)

        painter.setFont(
            QFont("Segoe UI", 8)
        )

        painter.drawText(
            0, 505, WINDOW_WIDTH, 15,
            Qt.AlignmentFlag.AlignCenter,
            self.current_date
        )

 
    def closeEvent(self, event):

        self.animation_timer.stop()
        self.telemetry_timer.stop()

        self.speech_thread.quit()

        if not self.speech_thread.wait(10000):
            print("Speech is still running; shutdown incomplete.")

        event.accept()



if __name__ == "__main__":

    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)

    hud = DrTeslaHUD()

    hud.show()

    sys.exit(app.exec())
