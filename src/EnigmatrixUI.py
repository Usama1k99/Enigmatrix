import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QProgressBar,
    QFrame, QLabel, QLineEdit, QFileDialog, QWidget, QTextEdit, QInputDialog,
    QMessageBox, QButtonGroup, QRadioButton, QScrollArea, QGridLayout
)
from PyQt6.QtGui import QIcon, QTextCursor, QKeySequence, QKeyEvent
from PyQt6.QtCore import Qt, QTimer, QThreadPool, QEvent, QCoreApplication
import key_utils
from utils import (
    load_config, dump_config, save_command, load_command_history,
    get_rsa_files, save_rsa_directory
)
import time
import utils
import encryptor
from command_handler import execute_command
from parallel_worker import *
from cfg import *


class RetroTerminal(QTextEdit):
    def __init__(self, parent=None,app=None):
        super().__init__(parent)
        self.app = app
        self.setAcceptRichText(False)
        self.command_history = load_command_history()
        self.history_index = len(self.command_history)
        self.prompt = "\n>>> "  # Command-line style prompt
        self._prompt = self.prompt[1:-1]
        # Pending command variables
        self.awaiting_response = False # default case
        self.pending_command = None # (func,args,'msg to display after')
        # Typing Effect Variables
        self.current_text = ""
        self.full_text = ""
        self.index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._add_next_character)
        # Variables
        self._is_cmd_running = False
        self.cwd = os.getcwd()
        self.is_dragging = False
        self.threadpool = QThreadPool.globalInstance()
        # Load stylesheet and set policies
        self.load_stylesheet("qss/retro_terminal.qss")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.createContextMenu)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.update_protected_region()

    @property
    def is_cmd_running(self):
        return self._is_cmd_running

    @is_cmd_running.setter
    def is_cmd_running(self,value):
        self._is_cmd_running = bool(value)
        if value:
            self.app.disable_buttons()
        else:
            self.app.enable_buttons()

    def exec_pending(self):
        """Executes the pending command using a worker thread to prevent UI freezing."""
        callback, args, msg_ini, msg_fin = self.pending_command  # Extract pending command details
        pb = "rsa" not in msg_ini.lower()
        def run_exec(signals):
            """Worker function to execute the pending command."""
            signals.update_terminal.emit(msg_ini)
            if pb:
                signals.start_pb.emit()
            kw = {
                "signals" : signals
            }
            try:
                if pb:
                    callback(*args,**kw)
                else:
                    callback(*args)
                if "rsa" in msg_ini.lower():
                    signals.load_rsa.emit(False,True)
            except Exception as e:
                signals.update_terminal.emit(f"Error: {e.args[0]}")
                signals.stop_pb.emit() if pb else None
                signals.confirmed.emit(True)
                return
            signals.update_terminal_full.emit(msg_fin,False)
            signals.p_time.emit() if pb else None
            signals.confirmed.emit(True)
        # Create and start worker
        worker = ParallelWorker(run_exec,terminal=True)
        self.connect_worker_signals(worker,pb)
        self.threadpool.start(worker)

    def set_pending_state(self,callback,args,msg_ini,msg_fin):
        self.awaiting_response = True
        self.pending_command = callback,args,msg_ini,msg_fin

    def confirmed(self,confirm=True):
        self.awaiting_response = False
        self.pending_command = None
        self.force_scroll_to_bottom()
        if not confirm:
            self.type_text("Operation cancelled.",add_prompt=True)

    def update_protected_region(self):
        """Updates the protected region to ensure past outputs are not editable."""
        self.protected_region_end = self.document().characterCount()

    def createContextMenu(self, position):
        menu = self.createStandardContextMenu()
        # Find and remove Cut & Paste actions
        for action in menu.actions():
            actext = action.text().lower()
            if any(x in actext for x in ["+y","+z","+x","+v","+a","delete"]):
                menu.removeAction(action)
        menu.exec(self.viewport().mapToGlobal(position))

    def connect_worker_signals(self, worker, pb=False):
        """Connects worker signals to update terminal state."""
        if pb:
            worker.signals.progress_update.connect(self.app.update_progress_bar)
            worker.signals.start_pb.connect(self.app.start_progress_bar)
            worker.signals.stop_pb.connect(self.app.reset_progress_bar)
            worker.signals.terminal_progress.connect(self.terminal_progress_update)
        worker.signals.command_started.connect(self.on_command_started)
        worker.signals.command_finished.connect(self.on_command_finished)
        worker.signals.time1.connect(self.app.set_t1)
        worker.signals.time2.connect(self.app.set_t2)
        worker.signals.update_terminal.connect(self.type_text)
        worker.signals.update_terminal_full.connect(self.type_text)
        worker.signals.nblock_update.connect(self.app.update_processed_blocks)
        worker.signals.p_time.connect(self.print_time)
        worker.signals.load_rsa.connect(self.app.load_rsa_keys)
        worker.signals.confirmed.connect(self.confirmed)

    def terminal_progress_update(self,processed,total):
        self.replace_current_line(f"Blocks processed : {processed}/{total}",False)

    def print_time(self):
        t1,t2 = self.app.t1, self.app.t2
        self.type_text(f"Time taken for operation: {t2 - t1:.6f}")
        self.app.t1, self.app.t2 = None, None

    def on_command_started(self):
        """Called when a command starts execution."""
        self.is_cmd_running = True  # Disable input

    def on_command_finished(self):
        """Called when a command finishes execution."""
        self.is_cmd_running = False  # Re-enable input

    def keyPressEvent(self, event):
        """Handles keyboard input while restricting movement before the prompt."""
        if self.isReadOnly() or self.is_cmd_running:
            return
        cursor = self.textCursor()
        last_prompt_index = self.toPlainText().rfind(self.prompt) + len(self.prompt)

        ctrl_flag = event.key() == Qt.Key.Key_Control
        cpy_flag = False
        if cursor.position() < self.protected_region_end - 1:
            if event.matches(QKeySequence.StandardKey.Copy) or event.key() == Qt.Key.Key_Control:
                cpy_flag = True
            else:
                self.moveCursor(QTextCursor.MoveOperation.End)
                return
        if cursor.hasSelection():
            if not (cpy_flag or ctrl_flag):
                selection_start = cursor.selectionStart()
                selection_end = cursor.selectionEnd()
                if selection_start < self.protected_region_end - 1:
                    self.moveCursor(QTextCursor.MoveOperation.End)
                    return
                else:
                    pass
        if event.key() in (Qt.Key.Key_Z, Qt.Key.Key_Y, Qt.Key.Key_A, Qt.Key.Key_X) and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return
        # Prevent moving left beyond prompt
        if event.key() == Qt.Key.Key_Left:
            if cursor.position() < self.protected_region_end - 1:  # If before prompt, do nothing
                return
        # Allow moving right without restriction
        elif event.key() == Qt.Key.Key_Right:
            pass  # No restrictions for right movement
        elif event.key() == Qt.Key.Key_Up:
            self.show_previous_command()
            return
        elif event.key() == Qt.Key.Key_Down:
            self.show_next_command()
            return
        elif event.key() == Qt.Key.Key_PageUp:
            return
        elif event.key() == Qt.Key.Key_PageDown:
            return
        elif event.key() == Qt.Key.Key_Home:
            move_mode = QTextCursor.MoveMode.KeepAnchor if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else QTextCursor.MoveMode.MoveAnchor
            cursor.setPosition(self.protected_region_end-1, move_mode)
            self.setTextCursor(cursor)
            return

        # Allow Enter to process command
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.process_command()
            self.moveCursor(QTextCursor.MoveOperation.End)
            self.history_index = len(self.command_history)
            return

        # Prevent deleting text in the protected region
        elif event.key() == Qt.Key.Key_Backspace:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                cursor_position = cursor.position()
                if cursor_position <= self.protected_region_end-1:
                    return
                prev_text = self.toPlainText()[:cursor_position]
                last_space_index = prev_text.rfind(" ")
                if last_space_index == -1 or last_space_index < self.protected_region_end:
                    last_word_start = self.protected_region_end-1
                else:
                    last_word_start = last_space_index
                cursor.setPosition(last_word_start, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                return
            if cursor.hasSelection():
                selection_start = cursor.selectionStart()
                selection_end = cursor.selectionEnd()
                # Disallow deleting any selection that includes protected text
                if selection_start < self.protected_region_end-1:
                    self.moveCursor(QTextCursor.MoveOperation.End)
                    return
                else:
                    pass
            # If cursor is in the protected region, prevent deletion
            elif cursor.position() < self.protected_region_end:
                self.moveCursor(QTextCursor.MoveOperation.End)
                return

        # Prevent deleting protected text using the Delete key
        elif event.key() == Qt.Key.Key_Delete:
            if cursor.hasSelection():
                selection_start = cursor.selectionStart()
                selection_end = cursor.selectionEnd()
                if selection_start < self.protected_region_end-1:
                    self.moveCursor(QTextCursor.MoveOperation.End)
                    return
                else:
                    pass
            elif cursor.position() < self.protected_region_end-1:
                self.moveCursor(QTextCursor.MoveOperation.End)
                return

        # Call parent method for other keys
        super().keyPressEvent(event)

    def process_command(self):
        """Extract last command, execute it, and reset prompt."""
        text = self.toPlainText().strip().split("\n")
        if not text:
            return
        last_command = text[-1].replace(self._prompt, "").strip()  # Extract command
        if last_command:
            if not self.awaiting_response:
                save_command(last_command)
                if len(self.command_history)==0:
                    self.command_history.append(last_command)
                    execute_command(last_command,self.app)
                    return self.append(self.prompt)
                if len(self.command_history) > CMD_HISTORY_LIMIT:
                    self.command_history.pop(0)
                if last_command != self.command_history[-1]:
                    self.command_history.append(last_command)
            execute_command(last_command,self.app)
        else:
            self.type_text(add_prompt=True)

    def show_previous_command(self):
        """Displays the previous command from history when Up Arrow is pressed."""
        self.moveCursor(QTextCursor.MoveOperation.End)
        if self.history_index > 0:
            self.history_index -= 1  # Move back in history
            self.replace_current_line(self.command_history[self.history_index])

    def show_next_command(self):
        """Displays the next command from history when Down Arrow is pressed."""
        self.moveCursor(QTextCursor.MoveOperation.End)
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1  # Move forward in history
            self.replace_current_line(self.command_history[self.history_index])
        else:
            self.history_index = len(self.command_history)  # Reset index
            self.replace_current_line("")  # Clear command line

    def replace_current_line(self, command, prompt=True):
        """Replaces the current command line with a command from history.

        If `prompt=True`, only the text after the prompt is replaced.
        If `prompt=False`, the entire last line (including the prompt) is replaced.
        """
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        # Move to the start of the current line
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        if prompt:
            # Move cursor right past the prompt (`>>> `) to keep it intact
            for _ in range(len(self.prompt) - 1):
                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor)
        else:
            pass
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(command)
        self.setTextCursor(cursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            cursor = self.cursorForPosition(event.pos())
            if cursor.hasSelection():
                self.is_dragging = True
            else:
                self.setTextCursor(cursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging:
            event.ignore()
        else:
            super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        event.ignore()  # Ignore drag event

    def dropEvent(self, event):
        event.ignore()  # Ignore drop event completely

    def force_scroll_to_bottom(self):
        self.simulate_keypress(Qt.Key.Key_Backspace)
        scrollbar = self.verticalScrollBar()
        cursor = self.textCursor()
        if scrollbar.value() < scrollbar.maximum():  # Check if not already at bottom
            scrollbar.setValue(scrollbar.maximum())
        self.moveCursor(QTextCursor.MoveOperation.Start)

    def simulate_keypress(self, key):
        """Simulates a key press event in the terminal."""
        key_event = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
        QCoreApplication.postEvent(self, key_event)

    def type_text(self,text="",add_prompt=False):
        full_text = f"\n{text}"
        if add_prompt:
            full_text += self.prompt
        self.current_text = self.toPlainText()
        self.current_text += full_text
        self.setText(self.current_text)
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.update_protected_region()
        QApplication.processEvents()

    def type_effect(self, text: str, typing_speed = 40, clear_before_typing: bool = False):
        """Simulates typing effect over a fixed speed."""
        if clear_before_typing:
            self.clear()
        self.current_text = self.toPlainText()  # Preserve previous text
        self.full_text = f"\n{text}" + self.prompt
        self.index = 0
        delay = (1 / typing_speed) * 1000  # Enforce min speed
        self.setReadOnly(True)
        # Ensure previous connections are cleared to avoid stacking
        self.timer.stop()
        self.timer.timeout.disconnect() if self.timer.isActive() else None
        self.timer.timeout.connect(self._add_next_character)
        self.timer.start(int(delay))  # Start typing effect

    def _add_next_character(self):
        """Adds the next character from `full_text` to `current_text`."""
        if self.index < len(self.full_text):
            self.current_text += self.full_text[self.index]
            self.setPlainText(self.current_text)  # Update text in terminal
            self.index += 1
            # Move cursor to end
            self.moveCursor(QTextCursor.MoveOperation.End)
        else:
            self.setReadOnly(False)
            self.timer.stop()  # Stop typing effect
            self.update_protected_region()
            config = utils.load_config()
            benchmarks = config.get("benchmarks")
            prefs = config.get("preferences")
            cores = prefs.get("cores")
            bm_time = benchmarks.get(str(cores))
            if not bm_time:
                self.moveCursor(QTextCursor.MoveOperation.End)
                self.append(f"benchmark {cores}")
                self.process_command()

    def load_stylesheet(self, file_name):
        """Loads a QSS stylesheet from an external file."""
        try:
            with open(file_name, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"Warning: Stylesheet '{file_name}' not found.")

    def add_ascii_art(self,welcome_msg=False,clear=False,speed=220):
        with open(ASCII_FILE, 'r') as f:
            ascii_art = f.read()
            txt = f"{ascii_art} \n\nWelcome to Enigmatrix - The Ultimate Encryption Tool.\n" if welcome_msg else f"{ascii_art}"
            self.type_effect(txt,speed,clear)

class EnigmatrixApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Enigmatrix - the ultimate encryption tool".title())
        # Core Operation Variables :
        self.input_path = None
        self.rsa_file = None
        self.output_path = None

        # Set window icon
        self.icon_path = "./assets/Enigmatrix.ico"
        self.setWindowIcon(QIcon(self.icon_path))

        # Apply external QSS stylesheet
        self.load_stylesheet("qss/main_style.qss")

        if not os.path.exists(CONFIG_FILE):
            self.init_config()

        # Variables
        self.t1, self.t2 = None, None
        self.threadpool = QThreadPool.globalInstance()
        self.est_op_time = 0

        # Central widget setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # === Main Layout ===
        self.main_layout = QHBoxLayout()

        self.gui_frame = QFrame()
        self.gui_frame.setProperty("class","app-frames")
        self.gui_frame.setObjectName("gui_frame")

        self.gui_layout = QVBoxLayout(self.gui_frame)
        self.rsa_list_layout = QVBoxLayout(self.gui_frame)
        self.info_layout = QVBoxLayout(self.gui_frame)

        self.rsa_list_header = QLabel("RSA header placeholder")
        self.rsa_list_header.setFixedHeight(30)
        self.rsa_list_header.setProperty("class","header")

        self.rsa_list_layout.addWidget(self.rsa_list_header,Qt.AlignmentFlag.AlignTop)

        self.info_header = QLabel("File info :")
        self.file_name_info = QLabel("Selected file : None")
        self.file_size_info = QLabel("File size : None")
        self.output_file_info = QLabel("Output file path : None")
        self.time_info = QLabel("Time taken : None")
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress-bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.file_name_info.setWordWrap(True)
        self.info_header.setProperty("class", "header")
        self.file_name_info.setProperty("class", "info-labels")
        self.file_size_info.setProperty("class", "info-labels")
        self.output_file_info.setProperty("class", "info-labels")
        self.time_info.setProperty("class", "info-labels")
        self.info_layout.addWidget(self.info_header, Qt.AlignmentFlag.AlignTop)
        self.info_layout.addWidget(self.file_name_info, Qt.AlignmentFlag.AlignTop)
        self.info_layout.addWidget(self.file_size_info, Qt.AlignmentFlag.AlignTop)
        self.info_layout.addWidget(self.output_file_info, Qt.AlignmentFlag.AlignTop)
        self.info_layout.addWidget(self.time_info, Qt.AlignmentFlag.AlignTop)
        self.info_layout.addWidget(self.progress_bar, Qt.AlignmentFlag.AlignTop)

        self.key_entry = QLineEdit()
        self.key_entry.setObjectName("key_entry")
        self.key_entry.setPlaceholderText("Enter encryption key")
        self.key_entry.setEchoMode(QLineEdit.EchoMode.Password)

        self.btn_grid = QGridLayout()

        self.generate_rsa_btn = QPushButton("Generate RSA Key")
        self.generate_rsa_btn.setProperty("class", "gui-buttons")
        self.generate_rsa_btn.clicked.connect(self.create_rsa_key)
        self.select_rsa_dir_btn = QPushButton("Select RSA Directory")
        self.select_rsa_dir_btn.setProperty("class", "gui-buttons")
        self.select_rsa_dir_btn.clicked.connect(self.select_rsa_dir)

        self.select_file_btn = QPushButton("Select File")
        self.select_file_btn.setProperty("class", "gui-buttons")
        self.select_file_btn.clicked.connect(self.select_input_file)

        self.show_hide_btn = QPushButton("Show key")
        self.show_hide_btn.setProperty("class", "gui-buttons")
        self.show_hide_btn.clicked.connect(self.show_hide)

        self.encrypt_btn = QPushButton("Encrypt")
        self.encrypt_btn.setProperty("class", "gui-buttons")
        self.encrypt_btn.clicked.connect(self.encrypt_file)

        self.decrypt_btn = QPushButton("Decrypt")
        self.decrypt_btn.setProperty("class", "gui-buttons")
        self.decrypt_btn.clicked.connect(self.decrypt_file)

        self.reset_btn = QPushButton("Reset fields")
        self.reset_btn.setProperty("class", "gui-buttons")
        self.reset_btn.clicked.connect(self.reset)

        self.btn_grid.addWidget(self.select_file_btn,0,0)
        self.btn_grid.addWidget(self.show_hide_btn,0,1)
        self.btn_grid.addWidget(self.select_rsa_dir_btn,1,0)
        self.btn_grid.addWidget(self.generate_rsa_btn,1,1)
        self.btn_grid.addWidget(self.encrypt_btn,2,0)
        self.btn_grid.addWidget(self.decrypt_btn,2,1)
        self.btn_grid.addWidget(self.reset_btn,3,0,1,2)

        self.gui_layout.addLayout(self.rsa_list_layout,Qt.AlignmentFlag.AlignTop)
        self.gui_layout.addLayout(self.info_layout, Qt.AlignmentFlag.AlignTop)
        self.gui_layout.addWidget(self.key_entry)
        self.gui_layout.addLayout(self.btn_grid)

        self.terminal_frame = QFrame()
        self.terminal_frame.setProperty("class","app-frames")
        self.terminal_frame.setObjectName("terminal_frame")

        self.terminal_layout = QVBoxLayout(self.terminal_frame)
        self.terminal_layout.setContentsMargins(0,0,0,0)
        self.terminal_layout.setSpacing(0)

        self.retro_terminal = RetroTerminal(app=self)
        self.retro_terminal.add_ascii_art(welcome_msg=True,speed=350)
        self.retro_terminal.setObjectName("RetroTerminal")

        self.terminal_layout.addWidget(self.retro_terminal)

        self.main_layout.addWidget(self.terminal_frame, 5)
        self.main_layout.addWidget(self.gui_frame, 3)

        # Set layout to central widget
        self.init_preferences()
        self.central_widget.setLayout(self.main_layout)
        self.display_rsa_keys_as_radio(get_rsa_files())
        self.retro_terminal.setFocus()

    def init_preferences(self):
        config = load_config()
        if utils.is_admin():
            self.setWindowTitle("(Admin) Enigmatrix - the ultimate encryption tool".title())
        pref = config.get("preferences")
        window = pref.get("window_mode")
        ui = pref.get("ui_mode")
        if window=="fullscreen":
            self.showFullScreen()
        elif window=="maximize":
            self.showMaximized()
        elif window=="normal":
            if self.windowState() == Qt.WindowState.WindowFullScreen:
                self.showMaximized()
            self.setMinimumSize(*NORMAL_WINDOW_SIZE)
            self.resize(*NORMAL_WINDOW_SIZE)
            self.showNormal()
        elif window=="small":
            if self.windowState() == Qt.WindowState.WindowFullScreen:
                self.showMaximized()
            self.setMinimumSize(*SMALL_WINDOW_SIZE)
            self.resize(*SMALL_WINDOW_SIZE)
            self.showNormal()

        if ui=="terminal":
            self.gui_frame.hide()
        if ui=="gui":
            self.gui_frame.show()

    def init_config(self):
        obj = {
            "rsa_directory" : None,
            "preferences" : {
                "cores" : utils.get_default_core_count(),
                "window_mode" : "normal",
                "ui_mode" : "gui",
            },
            "benchmarks" : {},
            "command_history" :[]
        }
        dump_config(obj)

    def reset(self):
        """Resets the file variables and clears the key field"""
        self.input_path = None
        self.output_path = None
        self.rsa_file = None
        self.key_entry.setText("")
        self.show_hide_btn.setText("Show key")
        self.key_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.load_rsa_keys(tprint=False)
        self.file_name_info.setText("Selected file : None")
        self.file_size_info.setText("File size : None")
        self.output_file_info.setText("Output file path : None")
        self.time_info.setText("Time taken : None")
        self.reset_progress_bar()
        self.retro_terminal.type_text("Reset Successful.",add_prompt=True)

    def show_hide(self):
        mode = self.key_entry.echoMode()
        if mode==QLineEdit.EchoMode.Normal:
            self.show_hide_btn.setText("Show key")
            self.key_entry.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.show_hide_btn.setText("Hide key")
            self.key_entry.setEchoMode(QLineEdit.EchoMode.Normal)

    def update_processed_blocks(self, processed, total):
        tnow = time.time() if not self.t2 else self.t2
        if processed==total:
            self.time_info.setText(f"Time taken : {tnow-self.t1:.6f} seconds")
        else:
            self.time_info.setText(f"Time elapsed : {tnow-self.t1:.6f} seconds\n"
                               f"Blocks processed : {processed}/{total}")

    def start_progress_bar(self):
        self.progress_bar.show()

    def update_progress_bar(self, progress):
        if progress == 100:
            self.reset_progress_bar()
        self.progress_bar.setValue(progress)

    def stop_pb_update(self):
        self.progress_bar.hide()
        self.progress_bar.setValue(0)

    def reset_progress_bar(self):
        self.progress_bar.setValue(100)
        QTimer.singleShot(1000, self.stop_pb_update)

    def display_time(self):
        self.time_info.setText(f"Time taken : {self.t2-self.t1:.6f} seconds")
        self.reset_progress_bar()
        self.t1,self.t2 = None,None

    def enable_buttons(self):
        self.generate_rsa_btn.setEnabled(True)
        self.encrypt_btn.setEnabled(True)
        self.decrypt_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)

    def disable_buttons(self):
        self.generate_rsa_btn.setEnabled(False)
        self.encrypt_btn.setEnabled(False)
        self.decrypt_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

    def set_t1(self,):
        self.t1 = time.time()

    def set_t2(self,):
        self.t2 = time.time()

    def connect_worker_signals(self,worker,finished_cb):
        self.retro_terminal.connect_worker_signals(worker)
        worker.signals.msg_box.connect(self.msgBox)
        worker.signals.time1.connect(self.set_t1)
        worker.signals.time2.connect(self.set_t2)
        worker.signals.progress_update.connect(self.update_progress_bar)
        worker.signals.finished.connect(finished_cb)

    def msgBox(self,title,text):
        QMessageBox.information(self,title,text)

    def worker_wrapper(self,signals,func,cb_args,*args,**kwargs):
        kw = {
            "signals" : signals
        }
        try:
            if func == key_utils.generate_rsa_keypair:
                func(*cb_args)
            else:
                func(*cb_args,**kw)
        except Exception as e:
            signals.update_terminal.emit(e.args[0])
            signals.stop_pb.emit()
            return signals.msg_box.emit("Error",e.args[0])
        signals.finished.emit()

    def encrypt_file(self):
        """Encrypts the selected file with the key and RSA key if selected"""
        config = load_config()
        pref = config.get("preferences")
        benchmarks = config.get("benchmarks")
        cores = pref.get("cores")
        rsa_dir = config.get('rsa_directory')
        if not self.input_path:
            return QMessageBox.information(self,"Error","Select a file first!")
        else:
            if os.path.exists(self.input_path):
                pass
            else:
                return QMessageBox.information(self,"Error","Selected input file does not exist!")
        raw_key = self.key_entry.text()
        if len(raw_key) < MIN_KEY_LEN:
            return QMessageBox.information(self,"Error",f"Key length should be atleast {MIN_KEY_LEN} characters!")
        if not self.output_path:
            if not self.select_output_file():
                return
        file_size,*_ = utils.file_info(self.input_path)
        bm_time = benchmarks.get(str(cores))
        if not bm_time:
            return QMessageBox.information(self,"Error",f"You have to run the benchmark command with {cores} cores to perform encryption / decryption")
        self.est_op_time = utils.estimate_encryption_time(file_size,bm_time)
        raw_key = raw_key.encode()
        if self.rsa_file:
            if os.path.exists(os.path.join(rsa_dir,self.rsa_file)):
                if key_utils.detect_rsa_key(os.path.join(rsa_dir,self.rsa_file)) != "public":
                    return QMessageBox.information(self, "Error",f"This is not a public key")
                reply = QMessageBox.question(
                    self, "Confirmation",
                    f"Input file: {self.input_path}\n"
                    f"Output file: {self.output_path}\n"
                    f"RSA key: {self.rsa_file}\n"
                    f"Estimated time required : {self.est_op_time} seconds\n"
                    f"Operation : Encryption\n"
                    f"Are you sure you want to continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
                # Disable buttons here
                self.start_progress_bar()
                public_key = key_utils.load_rsa_key(os.path.join(rsa_dir,self.rsa_file))
                cb_args = (self.input_path,self.output_path,raw_key,public_key,cores)
                worker = ParallelWorker(self.worker_wrapper, encryptor.encrypt_file, cb_args)
                self.connect_worker_signals(worker,self.on_encrypted)
                self.threadpool.start(worker)
            else:
                self.rsa_file = None
                self.load_rsa_keys(tprint=False)
                return QMessageBox.information(self,"Error","Selected RSA file does not exist!")
        else:
            reply = QMessageBox.question(
                self, "Confirmation",
                f"Input file: {self.input_path}\n"
                f"Output file: {self.output_path}\n"
                f"Estimated time required : {self.est_op_time} seconds\n"
                f"Operation : Encryption\n"
                f"Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            # Disable buttons here
            self.start_progress_bar()
            cb_args = (self.input_path,self.output_path,raw_key,None,cores)
            worker = ParallelWorker(self.worker_wrapper, encryptor.encrypt_file, cb_args)
            self.connect_worker_signals(worker,self.on_encrypted)
            self.threadpool.start(worker)

    def on_encrypted(self):
        self.retro_terminal.type_text("Encryption Successful!")
        self.display_time()
        self.output_path = None
        QMessageBox.information(self,"Success","Encryption Successful!")

    def decrypt_file(self):
        """Decrypts the selected file with the key and RSA key if selected"""
        config = load_config()
        pref = config.get("preferences")
        benchmarks = config.get("benchmarks")
        cores = pref.get("cores")
        rsa_dir = config.get('rsa_directory')
        if not self.input_path:
            return QMessageBox.information(self,"Error","Select a file first!")
        else:
            if os.path.exists(self.input_path):
                pass
            else:
                return QMessageBox.information(self,"Error","Selected input file does not exist!")
        if not self.output_path:
            if not self.select_output_file():
                return
        raw_key = self.key_entry.text()
        enc_check = utils.check_encrypted(self.input_path)
        if not enc_check:
            self.input_path = None
            self.file_name_info.setText("Selected file : None")
            self.file_size_info.setText("File size : None")
            return QMessageBox.information(self,"Error","Selected file is not encrypted by this software, or file might be corrupted.\nChoose a different file.")

        file_size, *_ = utils.file_info(self.input_path)
        bm_time = benchmarks.get(str(cores))
        if not bm_time:
            return QMessageBox.information(self, "Error", f"You have to run the benchmark command with {cores} cores to perform encryption / decryption")
        self.est_op_time = utils.estimate_encryption_time(file_size, bm_time)
        rsa_flag, rsa_enc_key, lcs = utils.read_file_header(self.input_path)
        if rsa_flag:
            if not self.rsa_file:
                return QMessageBox.information(self,"Error","This file requiers RSA key, please select an RSA key file!")
            else:
                if os.path.exists(os.path.join(rsa_dir, self.rsa_file)):
                    if key_utils.detect_rsa_key(os.path.join(rsa_dir,self.rsa_file)) != "private":
                        return QMessageBox.information(self, "Error", f"This is not a private key")
                    reply = QMessageBox.question(
                        self, "Confirmation",
                        f"Input file: {self.input_path}\n"
                        f"Output file: {self.output_path}\n"
                        f"RSA key: {self.rsa_file}\n"
                        f"Estimated time required : {self.est_op_time} seconds\n"
                        f"Operation : Decryption\n"
                        f"Are you sure you want to continue?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return
                    # Disable buttons here
                    priv_key = key_utils.load_rsa_key(os.path.join(rsa_dir,self.rsa_file))
                    self.start_progress_bar()
                    cb_args = (self.input_path, self.output_path, None, priv_key, cores)
                    worker = ParallelWorker(self.worker_wrapper, encryptor.decrypt_file, cb_args)
                    self.connect_worker_signals(worker,self.on_decrypted)
                    self.threadpool.start(worker)
                else:
                    return QMessageBox.information(self,"Error","Selected RSA file does not exist!")
        else:
            raw_key = raw_key.encode()
            reply = QMessageBox.question(
                self, "Confirmation",
                f"Input file: {self.input_path}\n"
                f"Output file: {self.output_path}\n"
                f"Estimated time required : {self.est_op_time} seconds\n"
                f"Operation : Decryption\n"
                f"Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            # Disable buttons here
            self.start_progress_bar()
            cb_args = (self.input_path, self.output_path, raw_key, None, cores)
            worker = ParallelWorker(self.worker_wrapper, encryptor.decrypt_file, cb_args)
            self.connect_worker_signals(worker,self.on_decrypted)
            self.threadpool.start(worker)

    def on_decrypted(self):
        self.retro_terminal.type_text("Decryption Successful!")
        self.display_time()
        self.output_path = None
        QMessageBox.information(self,"Success","Decryption Successful!")

    def create_rsa_key(self):
        """Handles RSA key pair creation while checking for existing keys and preventing accidental overwrites."""
        # Load the RSA directory from config.json
        config = load_config()
        rsa_directory = config.get("rsa_directory")
        # If no directory is set, just exit
        if not rsa_directory:
            rsa_directory = self.select_rsa_dir()
            if not rsa_directory:
                return
        # Ensure the directory exists
        if not os.path.exists(rsa_directory):
            os.makedirs(rsa_directory)
        # Scan directory for existing key pairs
        all_rsa_files = get_rsa_files()
        prv_rsa_files = [x for x in all_rsa_files if x.endswith("_private.pem")]
        existing_keys = set([x.replace("_private.pem", "") for x in prv_rsa_files])
        # Ask the user for a new key name
        key_name, ok = QInputDialog.getText(self, "RSA Key Name", "Enter a name for the new RSA key pair:")
        if not ok or not key_name.strip():
            return  # User canceled input
        key_name = key_name.strip()
        # Check if the name already exists
        if key_name in existing_keys:
            reply = QMessageBox.question(
                self, "Key Exists",
                f"A key named '{key_name}' already exists. Do you want to overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return  # User chose not to overwrite
        # Generate RSA key pair and save them
        cb_args = (key_name,rsa_directory)
        worker = ParallelWorker(self.worker_wrapper, key_utils.generate_rsa_keypair, cb_args)
        self.connect_worker_signals(worker,self.on_rsa_key_generated)
        self.threadpool.start(worker)

    def on_rsa_key_generated(self):
        self.retro_terminal.type_text("RSA key pair created successfully!")
        QMessageBox.information(self, "Success", f"RSA key pair created successfully!")
        self.load_rsa_keys(tprint=False)

    def display_rsa_keys_as_radio(self, rsa_files):
        """Displays available RSA keys as radio buttons inside a scrollable area."""

        # Remove existing RSA key selection area if it exists
        if hasattr(self, 'rsa_scroll_area'):
            self.rsa_scroll_area.deleteLater()

        # Create a scroll area to contain the list
        self.rsa_scroll_area = QScrollArea(self)
        # self.rsa_scroll_area.setFixedHeight(400)
        self.rsa_scroll_area.setWidgetResizable(True)  # Allow resizing

        # Create a container widget to hold radio buttons
        self.rsa_key_widget = QWidget()
        self.rsa_key_layout = QVBoxLayout(self.rsa_key_widget)
        self.rsa_key_widget.setObjectName("rsa-radio-layout")

        # Button group to ensure only one selection at a time
        self.rsa_button_group = QButtonGroup(self.rsa_key_widget)
        self.rsa_button_group.setExclusive(True)

        if not rsa_files:
            rsa_dir = utils.get_rsa_directory()
            if not rsa_dir:
                self.rsa_list_header.setText("Select RSA directory to show files.")
            elif not os.path.exists(rsa_dir):
                self.rsa_list_header.setText("Select RSA directory to show files.")
            else:
                self.rsa_list_header.setText("No RSA keys found in selected folder")
        else:
            self.rsa_list_header.setText("RSA key files in selected folder :")

            for filename in rsa_files:
                radio_button = QRadioButton(filename)
                radio_button.setProperty("class","rsa-radio-btn")
                radio_button.clicked.connect(self.rsa_radio_slot)
                self.rsa_button_group.addButton(radio_button)
                self.rsa_key_layout.addWidget(radio_button, alignment=Qt.AlignmentFlag.AlignTop)

        # Set the container widget inside the scroll area
        self.rsa_scroll_area.setWidget(self.rsa_key_widget)

        # Add the scroll area to the right panel layout
        self.rsa_list_layout.addWidget(self.rsa_scroll_area, 5, alignment=Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignVCenter)
        self.rsa_scroll_area.show()

    def select_rsa_key_by_name(self, key_name):
        """Selects the radio button with the given key_name if it exists."""
        found = False
        for button in self.rsa_button_group.buttons():
            if button.text() == key_name:
                self.rsa_file = key_name
                button.setChecked(True)
                return self.retro_terminal.type_text(f"\"{self.rsa_file}\" is selected as RSA key file.")
        self.retro_terminal.type_text(f"No such file in selected RSA directory \"{key_name}\"")

    def rsa_radio_slot(self):
        radio_btn = self.sender()
        if radio_btn.isChecked():
            self.rsa_file = radio_btn.text()
            if not self.retro_terminal.is_cmd_running:
                self.retro_terminal.type_text(f"\"{self.rsa_file}\" is selected as RSA key file.\n",add_prompt=True)

    def load_stylesheet(self, file_name):
        """Loads a QSS stylesheet from an external file."""
        try:
            with open(file_name, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"Warning: Stylesheet '{file_name}' not found.")

    def select_rsa_dir(self):
        self.rsa_file = None
        file_dialog = QFileDialog()
        dir_path = file_dialog.getExistingDirectory(self,"Select RSA Directory")
        if dir_path:
            save_rsa_directory(dir_path)
            self.load_rsa_keys()
            if not self.retro_terminal.is_cmd_running:
                self.retro_terminal.type_text(f"Selected RSA Directory as \"{dir_path}\".",add_prompt=True)
            return dir_path

    def load_rsa_keys(self,add_prompt=True,tprint=True):
        self.rsa_file = None
        rsa_files = get_rsa_files()
        self.display_rsa_keys_as_radio(rsa_files)
        if rsa_files and tprint and not self.retro_terminal.is_cmd_running:
            t_text = self.str_rsa_files()
            self.retro_terminal.type_text(t_text,add_prompt=add_prompt)

    def str_rsa_files(self):
        rsa_files = get_rsa_files()
        if rsa_files:
            t_text = ""
            for i in range(len(rsa_files)):
                if rsa_files[i] == self.rsa_file:
                    t_text += f"{i+1}. {rsa_files[i]} -> [SELECTED]\n"
                else:
                    t_text += f"{i+1}. {rsa_files[i]}\n"
                if i==len(rsa_files)-1:
                    t_text = t_text[:-1] # removing last newline
            return t_text
        else:
            return "No RSA key files in selected directory."

    # === FUNCTION TO SELECT A FILE ===
    def select_input_file(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select File")
        if file_path:
            self.input_path = file_path
            file_size,_,lcs = utils.file_info(file_path)
            readable_size = utils.readable_size(file_size)
            est_size = utils.readable_size(utils.estimate_encrypted_size(file_size))
            fname = file_path.split("/")[-1]
            self.file_name_info.setText(f"Selected file : {fname}")
            self.file_size_info.setText(f"File size : {readable_size} , Estimated size after encryption : {est_size}")
            if not self.retro_terminal.is_cmd_running:
                self.retro_terminal.type_text(f"Selected file : {file_path}\n"
                                              f"File size : {readable_size} , Estimated Size after encryption : {est_size}",add_prompt=True)

    def select_output_file(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Save file as")
        if file_path:
            if self.input_path == file_path:
                QMessageBox.information(self, "Error", "Input and output files cannot be same!")
                return False
            self.output_path = file_path
            fname = file_path.split("/")[-1]
            self.output_file_info.setText(f"Output file name : {fname}")
            self.retro_terminal.type_text(f"Selected output file path : {file_path}",add_prompt=True)
            return True
        return False
