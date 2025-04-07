"""
Media Downloader Pro - Main Application File
Optimized for fast startup with background FFmpeg check
"""

import sys
import os
import platform
import subprocess
import urllib.request
import zipfile
import tempfile
import shutil
import yt_dlp
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox,
    QComboBox, QCheckBox, QAction, QActionGroup, QScrollArea, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTranslator, QLocale, QTimer
from PyQt5.QtGui import QFont, QIcon, QTextOption, QColor, QPalette

class FFmpegManager(QThread):
    """Handles FFmpeg installation and verification in background"""
    status_changed = pyqtSignal(str, str)  # status, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ffmpeg_path = None
        self.install_status = "checking"
        self.platform = platform.system().lower()
        self.parent = parent
    
    def run(self):
        """Run in background thread"""
        self.find_ffmpeg()
        
    def find_ffmpeg(self):
        """Try to find FFmpeg in system PATH or common locations"""
        try:
            # First quick check if ffmpeg is in PATH
            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                self.ffmpeg_path = ffmpeg_path
                self.install_status = "installed"
                self.status_changed.emit("installed", "FFmpeg ready")
                return True
            
            # More thorough check in background
            if self.platform == "windows":
                common_paths = [
                    os.path.join(os.environ.get("ProgramFiles", ""), "FFmpeg", "bin", "ffmpeg.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", ""), "FFmpeg", "bin", "ffmpeg.exe"),
                    os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe")
                ]
            else:  # Linux/Mac
                common_paths = [
                    "/usr/local/bin/ffmpeg",
                    "/usr/bin/ffmpeg",
                    os.path.join(os.path.expanduser("~"), "bin", "ffmpeg")
                ]
            
            for path in common_paths:
                if os.path.exists(path):
                    self.ffmpeg_path = path
                    self.install_status = "installed"
                    self.status_changed.emit("installed", "FFmpeg ready")
                    return True
            
            # If not found, attempt download (Windows only)
            if self.platform == "windows":
                self.status_changed.emit("downloading", "Downloading FFmpeg...")
                if self.download_ffmpeg():
                    self.status_changed.emit("installed", "FFmpeg ready")
                    return True
            
            self.install_status = "missing"
            self.status_changed.emit("missing", "FFmpeg missing")
            return False
            
        except Exception as e:
            print(f"Error finding FFmpeg: {e}")
            self.install_status = "missing"
            self.status_changed.emit("missing", "FFmpeg check failed")
            return False
    
    def download_ffmpeg(self):
        """Download FFmpeg for Windows"""
        try:
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            temp_dir = tempfile.mkdtemp()
            archive_path = os.path.join(temp_dir, "ffmpeg.zip")
            
            # Download with progress feedback
            def report_progress(block_num, block_size, total_size):
                percent = min(int(block_num * block_size * 100 / total_size), 100)
                self.status_changed.emit("downloading", f"Downloading FFmpeg... {percent}%")
            
            urllib.request.urlretrieve(url, archive_path, reporthook=report_progress)
            
            # Extract
            extract_dir = os.path.join(os.getcwd(), "ffmpeg")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the binary
            for root, dirs, files in os.walk(extract_dir):
                if "ffmpeg.exe" in files:
                    self.ffmpeg_path = os.path.join(root, "ffmpeg.exe")
                    self.install_status = "installed"
                    
                    # Add to PATH for this session
                    os.environ["PATH"] = os.path.dirname(self.ffmpeg_path) + os.pathsep + os.environ.get("PATH", "")
                    
                    shutil.rmtree(temp_dir)
                    return True
            
            return False
                
        except Exception as e:
            print(f"Error downloading FFmpeg: {e}")
            return False

class DownloadThread(QThread):
    """
    A QThread subclass that handles the actual downloading process in the background.
    """
    update_progress = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, urls, download_folder, format_type, ffmpeg_path):
        super().__init__()
        self.urls = urls
        self.download_folder = download_folder
        self.format_type = format_type
        self.ffmpeg_path = ffmpeg_path
        self.is_running = True
        self.ydl = None

    def run(self):
        for i, url in enumerate(self.urls):
            if not self.is_running:
                break

            self.update_progress.emit(0, self.tr("Processing: %s") % url)
            
            try:
                ydl_opts = self.build_ytdlp_options()
                with yt_dlp.YoutubeDL(ydl_opts) as self.ydl:
                    self.ydl.add_progress_hook(self.progress_hook)
                    self.ydl.download([url])
                    
                self.update_progress.emit(100, f"✔ {self.tr('Finished: %s') % url}")
                
            except Exception as e:
                self.update_progress.emit(0, f"❌ {self.tr('Error: %s') % str(e)}")

        self.finished.emit()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            progress = d.get('_percent_str', '0%').replace('%', '')
            try:
                progress_int = int(float(progress))
                self.update_progress.emit(
                    progress_int,
                    self.tr("Downloading: %s") % d.get('filename', '')
                )
            except (ValueError, TypeError):
                pass

    def build_ytdlp_options(self):
        opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'ignoreerrors': True,
            'ffmpeg_location': self.ffmpeg_path if self.ffmpeg_path else None,
        }

        if self.format_type.startswith("mp3"):
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320' if self.format_type == "mp3_320" else '192',
                }],
                'keepvideo': False,
            })
        elif self.format_type.startswith("mp4"):
            height_map = {
                'mp4_720': '720',
                'mp4_1080': '1080',
                'mp4_best': 'best'
            }
            height = height_map.get(self.format_type, 'best')
            
            if height == 'best':
                opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best'
            
            opts['merge_output_format'] = 'mp4'

        return opts

    def stop(self):
        self.is_running = False
        if self.ydl:
            self.ydl.cancel_download()
        if self.isRunning():
            self.requestInterruption()
            self.wait(2000)

class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("GPL License"))
        self.setMinimumSize(700, 500)
        
        # Hauptlayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Container für Lizenztext
        self.text_container = QWidget()
        self.text_layout = QVBoxLayout(self.text_container)
        self.text_layout.setContentsMargins(15, 15, 15, 15)
        
        # Lizenztext-Label
        self.license_label = QLabel()
        self.license_label.setTextFormat(Qt.PlainText)
        self.license_label.setWordWrap(True)
        self.license_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.license_label.setFont(QFont("Consolas", 10))
        
        self.text_layout.addWidget(self.license_label)
        scroll.setWidget(self.text_container)
        
        # OK-Button
        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setFixedWidth(100)
        
        layout.addWidget(scroll)
        layout.addWidget(self.btn_ok, alignment=Qt.AlignRight)
        
        self.load_license_text()
        self.apply_theme(parent.dark_mode if parent else False)

    def load_license_text(self):
        try:
            base_path = os.path.dirname(sys.argv[0])
            license_path = os.path.join(base_path, "LICENSE.txt")
            
            if not os.path.exists(license_path) and hasattr(sys, '_MEIPASS'):
                license_path = os.path.join(sys._MEIPASS, "LICENSE.txt")
            
            if os.path.exists(license_path):
                with open(license_path, 'r', encoding='utf-8') as f:
                    self.license_label.setText(f.read())
            else:
                self.license_label.setText("License file not found at: " + license_path)
        except Exception as e:
            self.license_label.setText(f"Error loading license: {str(e)}")

    def apply_theme(self, dark_mode):
        if dark_mode:
            self.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                }
                QScrollArea {
                    background-color: #252525;
                    border: 1px solid #444;
                }
                QLabel {
                    color: #f0f0f0;
                    background-color: #252525;
                }
                QPushButton {
                    background-color: #555;
                    color: white;
                    border: 1px solid #666;
                    padding: 5px;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
            self.text_container.setStyleSheet("background-color: #252525;")
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                }
                QScrollArea {
                    background-color: #f9f9f9;
                    border: 1px solid #ddd;
                }
                QLabel {
                    color: #333333;
                    background-color: #f9f9f9;
                }
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: 1px solid #45a049;
                    padding: 5px;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.text_container.setStyleSheet("background-color: #f9f9f9;")

class AboutDialog(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("About Media Downloader Pro"))
        
        about_text = f"""
        <h2>Media Downloader Pro</h2>
        <p>{self.tr('A tool for downloading videos and audio from various platforms')}</p>
        
        <h3>{self.tr('Features')}</h3>
        <ul>
            <li>{self.tr('Download videos as MP4 in various qualities')}</li>
            <li>{self.tr('Extract audio as MP3 with different bitrates')}</li>
            <li>{self.tr('Batch download from multiple URLs')}</li>
            <li>{self.tr('Progress tracking')}</li>
            <li>{self.tr('Automatic FFmpeg integration')}</li>
        </ul>
        
        <p><b>{self.tr('Author')}:</b> Jörg Schröder</p>
        <p><b>Website:</b> <a href="https://github.com/xGohac/Media-Downloader-Pro">Media-Downloader-Pro</a></p>
        <p><b>{self.tr('License')}:</b> GNU General Public License v3.0</p>
        """
        
        self.setText(about_text)
        self.setIcon(QMessageBox.Information)
        
        self.addButton(self.tr("View Full License"), QMessageBox.ActionRole)
        self.buttonClicked.connect(self.on_button_click)
        
        self.apply_theme(parent.dark_mode if parent else True)

    def on_button_click(self, button):
        if button.text() == self.tr("View Full License"):
            license_dialog = LicenseDialog(self.parent())
            license_dialog.exec_()

    def apply_theme(self, dark_mode):
        if dark_mode:
            self.setStyleSheet("""
                QMessageBox {
                    background-color: #2d2d2d;
                }
                QLabel {
                    color: white;
                }
                QPushButton {
                    min-width: 120px;
                }
            """)
        else:
            self.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: black;
                }
                QPushButton {
                    min-width: 120px;
                }
            """)

class YouTubeDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dark_mode = True
        self.current_language = "en"
        self.translator = QTranslator()
        
        self.setWindowTitle("Media Downloader Pro")
        self.setGeometry(100, 100, 800, 600)
        self.download_folder = os.path.expanduser("~/Downloads")
        self.download_thread = None
        self.show_log = False
        
        # Initialize FFmpeg manager
        self.ffmpeg_manager = FFmpegManager(self)
        self.ffmpeg_manager.status_changed.connect(self.update_ffmpeg_status)
        
        # Start FFmpeg check in background after short delay
        QTimer.singleShot(100, self.ffmpeg_manager.start)

        icon_path = os.path.join(os.path.dirname(__file__), "resources", "logo.ico")
        if not os.path.exists(icon_path):
            icon_path = ""
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
            
        self.init_ui()
        self.apply_dark_theme()
        self.load_language(self.current_language)

    def update_ffmpeg_status(self, status, message):
        """Update UI based on FFmpeg status (called from background thread)"""
        color = QColor(255, 255, 255)
        
        if status == "checking":
            color = QColor(200, 200, 0)
        elif status == "downloading":
            color = QColor(0, 0, 200)
        elif status == "installed":
            color = QColor(0, 200, 0)
            self.download_btn.setEnabled(True)
        elif status == "missing":
            color = QColor(255, 0, 0)
            self.download_btn.setEnabled(False)
            self.log(self.tr("FFmpeg is required for audio conversion and video merging."), QColor(255, 165, 0))
        
        self.ffmpeg_status_label.setText(message)
        self.ffmpeg_status_label.setStyleSheet(f"color: {color.name()};")
        
        if status == "missing" and "check failed" in message:
            self.log(self.tr("FFmpeg check failed. Please install manually."), QColor(255, 0, 0))
        
        # Show additional info for errors
        if status == "missing" and "check failed" in message:
            self.log(self.tr("FFmpeg check failed. Please install manually."), QColor(255, 0, 0))

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
        self.update_theme_button_text()
        self.update()

    def load_language(self, lang_code):
        self.current_language = lang_code
        QApplication.instance().removeTranslator(self.translator)
        
        if lang_code == "de":
            translations = {
                "Media Downloader Pro": "Media Downloader Pro",
                "Enter Video/Audio URLs": "Video/Audio URLs eingeben",
                "Paste one URL per line...": "Eine URL pro Zeile einfügen...",
                "Download Options": "Download-Optionen",
                "Quality:": "Qualität:",
                "Save location: %s": "Speicherort: %s",
                "Change folder": "Ordner ändern",
                "Progress": "Fortschritt",
                "Ready to start": "Bereit zum Starten",
                "Show log": "Log anzeigen",
                "Activity Log": "Aktivitätsprotokoll",
                "Download Now": "Download starten",
                "Cancel": "Abbrechen",
                "Exit": "Beenden",
                "File": "Datei",
                "Language": "Sprache",
                "Help": "Hilfe",
                "About": "Über",
                "Error": "Fehler",
                "No URLs entered!": "Keine URLs eingegeben!",
                "Download completed": "Download abgeschlossen",
                "Download cancelled": "Download abgebrochen",
                "A download is still active. Really quit?": "Ein Download ist noch aktiv. Wirklich beenden?",
                "Download in progress": "Download läuft",
                "Processing: %s": "Verarbeite: %s",
                "Downloading: %s": "Download: %s",
                "Finished: %s": "Fertig: %s",
                "Error with: %s": "Fehler bei: %s",
                "Error: %s": "Fehler: %s",
                "Could not create folder: %s": "Ordner konnte nicht erstellt werden: %s",
                "yt-dlp is not installed!": "yt-dlp ist nicht installiert!",
                "Toggle light/dark mode": "Hell/Dunkel Modus wechseln",
                "About Media Downloader Pro": "Über Media Downloader Pro",
                "A tool for downloading videos and audio from various platforms": 
                    "Ein Tool zum Herunterladen von Videos und Audio von verschiedenen Plattformen",
                "Features": "Funktionen",
                "Download videos as MP4 in various qualities": 
                    "Videos als MP4 in verschiedenen Qualitäten herunterladen",
                "Extract audio as MP3 with different bitrates": 
                    "Audio als MP3 mit verschiedenen Bitraten extrahieren",
                "Batch download from multiple URLs": 
                    "Mehrere URLs gleichzeitig herunterladen",
                "Progress tracking": "Fortschrittsverfolgung",
                "Automatic FFmpeg integration": "Automatische FFmpeg-Integration",
                "Author": "Autor",
                "License": "Lizenz",
                "Checking FFmpeg...": "Prüfe FFmpeg...",
                "Downloading FFmpeg...": "Lade FFmpeg herunter...",
                "FFmpeg ready": "FFmpeg bereit",
                "FFmpeg missing": "FFmpeg fehlt",
                "FFmpeg is required for audio conversion and video merging.": 
                    "FFmpeg wird für Audio-Konvertierung und Video-Merging benötigt.",
                "Please install FFmpeg or restart the application to attempt automatic download.": 
                    "Bitte installieren Sie FFmpeg oder starten Sie die Anwendung neu für einen automatischen Download-Versuch.",
                "Failed to download FFmpeg. Please install it manually.": 
                    "FFmpeg konnte nicht heruntergeladen werden. Bitte manuell installieren."
            }
            
            class GermanTranslator(QTranslator):
                def translate(self, context, source, disambiguation=None, n=-1):
                    return translations.get(source, source)
            
            self.translator = GermanTranslator()
            QApplication.instance().installTranslator(self.translator)
        
        self.retranslate_ui()

    def retranslate_ui(self):
        """Update all UI elements with current translation"""
        # Main window title
        self.setWindowTitle(self.tr("Media Downloader Pro"))
        
        # URL group
        self.url_group.setTitle(self.tr("Enter Video/Audio URLs"))
        
        # Options group
        self.format_group.setTitle(self.tr("Download Options"))
        self.quality_label.setText(self.tr("Quality:"))
        self.folder_label.setText(self.tr("Save location: %s") % self.download_folder)
        self.folder_btn.setText(self.tr("Change folder"))
        
        # Progress group
        self.progress_group.setTitle(self.tr("Progress"))
        self.status_label.setText(self.tr("Ready to start"))
        
        # Log
        self.log_checkbox.setText(self.tr("Show log"))
        self.log_group.setTitle(self.tr("Activity Log"))
        
        # Buttons
        self.download_btn.setText(self.tr("Download Now"))
        self.cancel_btn.setText(self.tr("Cancel"))
        self.exit_btn.setText(self.tr("Exit"))
        
        # Menu items
        self.file_menu.setTitle(self.tr("File"))
        self.language_menu.setTitle(self.tr("Language"))
        self.help_menu.setTitle(self.tr("Help"))
        self.about_action.setText(self.tr("About"))
        self.exit_action.setText(self.tr("Exit"))
        
        # Theme button
        self.update_theme_button_text()

        # Update FFmpeg status text without changing status
        current_text = self.ffmpeg_status_label.text()
        self.ffmpeg_status_label.setText(self.tr(current_text))

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        self.create_menu_bar()

        # Header with FFmpeg status, title and theme toggle
        header_layout = QHBoxLayout()
        
        # FFmpeg status
        ffmpeg_layout = QHBoxLayout()
        ffmpeg_layout.setAlignment(Qt.AlignLeft)
        self.ffmpeg_status_label = QLabel("Checking FFmpeg...")
        self.ffmpeg_status_label.setFont(QFont("Arial", 9))
        ffmpeg_layout.addWidget(self.ffmpeg_status_label)
        header_layout.addLayout(ffmpeg_layout)
        
        # Title
        self.header = QLabel("Media Downloader Pro")
        self.header.setFont(QFont("Arial", 16, QFont.Bold))
        self.header.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.header, stretch=1)
        
        # Theme toggle
        self.theme_btn = QPushButton()
        self.theme_btn.setFixedSize(100, 30)
        self.update_theme_button_text()
        self.theme_btn.setToolTip(self.tr("Toggle light/dark mode"))
        self.theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_btn)
        
        main_layout.addLayout(header_layout)

        # URL input
        self.url_group = QGroupBox()
        url_layout = QVBoxLayout()
        self.url_edit = QTextEdit()
        self.url_edit.setPlaceholderText(self.tr("Paste one URL per line..."))
        self.url_edit.setFont(QFont("Arial", 10))
        url_layout.addWidget(self.url_edit)
        self.url_group.setLayout(url_layout)
        main_layout.addWidget(self.url_group)

        # Format selection
        self.format_group = QGroupBox()
        format_layout = QVBoxLayout()
        
        self.format_combo = QComboBox()
        formats = [
            (self.tr("MP3 (192 kbps)"), "mp3_192"),
            (self.tr("MP3 (320 kbps)"), "mp3_320"),
            (self.tr("MP4 (720p)"), "mp4_720"),
            (self.tr("MP4 (1080p)"), "mp4_1080"),
            (self.tr("MP4 (Best quality)"), "mp4_best"),
        ]
        
        for text, mode in formats:
            self.format_combo.addItem(text, mode)

        self.format_combo.setCurrentIndex(0)
        
        self.quality_label = QLabel()
        format_layout.addWidget(self.quality_label)
        format_layout.addWidget(self.format_combo)
        
        # Download location
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel()
        self.folder_label.setFont(QFont("Arial", 9))
        folder_layout.addWidget(self.folder_label)
        
        self.folder_btn = QPushButton()
        self.folder_btn.clicked.connect(self.select_download_folder)
        folder_layout.addWidget(self.folder_btn)
        format_layout.addLayout(folder_layout)
        
        self.format_group.setLayout(format_layout)
        main_layout.addWidget(self.format_group)

        # Progress display
        self.progress_group = QGroupBox()
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFont(QFont("Arial", 9))
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        progress_layout.addWidget(self.status_label)
        
        self.progress_group.setLayout(progress_layout)
        main_layout.addWidget(self.progress_group)

        # Log output (optional)
        self.log_checkbox = QCheckBox()
        self.log_checkbox.setChecked(False)
        self.log_checkbox.stateChanged.connect(self.toggle_log)
        main_layout.addWidget(self.log_checkbox)
        
        self.log_group = QGroupBox()
        self.log_group.setVisible(False)
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 9))
        self.log_output.setWordWrapMode(QTextOption.NoWrap)
        log_layout.addWidget(self.log_output)
        self.log_group.setLayout(log_layout)
        main_layout.addWidget(self.log_group)

        # Button bar
        button_layout = QHBoxLayout()
        
        self.download_btn = QPushButton()
        self.download_btn.setFont(QFont("Arial", 10, QFont.Bold))
        self.download_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.download_btn.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton()
        self.cancel_btn.setFont(QFont("Arial", 10))
        self.cancel_btn.setIcon(QIcon.fromTheme("process-stop"))
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)
        
        self.exit_btn = QPushButton()
        self.exit_btn.setFont(QFont("Arial", 10))
        self.exit_btn.setIcon(QIcon.fromTheme("application-exit"))
        self.exit_btn.clicked.connect(self.close)
        button_layout.addWidget(self.exit_btn)
        
        main_layout.addLayout(button_layout)

        # Widget settings
        self.setMinimumSize(700, 550)
        self.url_edit.setMinimumHeight(80)
        self.log_output.setMinimumHeight(120)
        self.url_edit.setAcceptRichText(False)
        self.url_edit.setLineWrapMode(QTextEdit.NoWrap)

    def update_theme_button_text(self):
        if self.dark_mode:
            self.theme_btn.setText(self.tr("Light Mode"))
            self.theme_btn.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: white;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
        else:
            self.theme_btn.setText(self.tr("Dark Mode"))
            self.theme_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ddd;
                    color: black;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #eee;
                }
            """)

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        self.file_menu = menubar.addMenu("File")
        self.exit_action = self.file_menu.addAction("Exit", self.close)
        
        # Language menu
        self.language_menu = menubar.addMenu("Language")
        self.language_group = QActionGroup(self)
        
        english_action = self.language_menu.addAction("English")
        english_action.setCheckable(True)
        english_action.setChecked(True)
        english_action.triggered.connect(lambda: self.load_language("en"))
        self.language_group.addAction(english_action)
        
        german_action = self.language_menu.addAction("Deutsch")
        german_action.setCheckable(True)
        german_action.triggered.connect(lambda: self.load_language("de"))
        self.language_group.addAction(german_action)
        
        # Help menu
        self.help_menu = menubar.addMenu("Help")
        self.about_action = self.help_menu.addAction("About", self.show_about)
        self.license_action = self.help_menu.addAction(self.tr("License"), self.show_license)

    def show_license(self):
        license_dialog = LicenseDialog(self)
        license_dialog.exec_()

    def show_about(self):
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def apply_dark_theme(self):
        dark_palette = QPalette()
        
        dark_palette.setColor(QPalette.Window, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(60, 60, 60))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.white)
        dark_palette.setColor(QPalette.Link, QColor(100, 150, 240))
        
        self.setPalette(dark_palette)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2d2d2d;
            }
            QGroupBox {
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #1e1e1e;
                color: white;
            }
            QGroupBox::title {
                color: #ddd;
            }
            QTextEdit, QProgressBar, QComboBox {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #444;
            }
            QLabel, QCheckBox {
                color: white;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #777;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
            QComboBox QAbstractItemView {
                background-color: #3a3a3a;
                color: white;
            }
            QMenuBar {
                background-color: #3a3a3a;
                color: white;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #555;
            }
            QMenu {
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #555;
            }
            QMenu::item:selected {
                background-color: #555;
            }
        """)

    def apply_light_theme(self):
        self.setPalette(QApplication.style().standardPalette())
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
                color: black;
            }
            QTextEdit, QProgressBar, QComboBox {
                background-color: white;
                color: black;
                border: 1px solid #ddd;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #777;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
            QMenuBar {
                background-color: #f0f0f0;
            }
            QMenu {
                background-color: white;
                border: 1px solid #ddd;
            }
        """)

    def toggle_log(self, state):
        self.show_log = state == Qt.Checked
        self.log_group.setVisible(self.show_log)

    def select_download_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 
            self.tr("Select download folder"), 
            self.download_folder,
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder:
            self.download_folder = folder
            self.folder_label.setText(self.tr("Save location: %s") % folder)
            self.log(self.tr("Download folder changed to: %s") % folder, QColor(0, 128, 0))

    def log(self, message, color=None):
        if not self.show_log:
            return
            
        if color:
            self.log_output.setTextColor(color)
        self.log_output.append(message)
        self.log_output.ensureCursorVisible()
        if color:
            self.log_output.setTextColor(Qt.black if not self.dark_mode else Qt.white)

    def start_download(self):
        if self.ffmpeg_manager.install_status != "installed":
            QMessageBox.critical(self, self.tr("Error"), self.tr("FFmpeg is not ready. Please wait or install manually."))
            return

        urls = self.url_edit.toPlainText().strip().split("\n")
        urls = [url.strip() for url in urls if url.strip()]

        if not urls:
            QMessageBox.critical(self, self.tr("Error"), self.tr("No URLs entered!"))
            return

        if not os.path.exists(self.download_folder):
            try:
                os.makedirs(self.download_folder)
            except OSError as e:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Could not create folder: %s") % str(e))
                return

        format_type = self.format_combo.currentData()
        self.download_thread = DownloadThread(
            urls, 
            self.download_folder, 
            format_type,
            self.ffmpeg_manager.ffmpeg_path
        )
        self.download_thread.update_progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.exit_btn.setEnabled(False)
        self.download_thread.start()

    def update_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
        if message and self.show_log:
            if "✔" in message:
                self.log(message, QColor(0, 200, 0))
            elif "❌" in message:
                self.log(message, QColor(255, 0, 0))
            else:
                self.log(message)

    def download_finished(self):
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.exit_btn.setEnabled(True)
        self.status_label.setText(self.tr("Download completed"))
        self.download_thread = None

    def cancel_download(self):
        if self.download_thread:
            self.download_thread.stop()
            self.download_thread.wait()
            self.log(self.tr("Download cancelled"), QColor(255, 165, 0))
            self.download_finished()

    def closeEvent(self, event):
        if self.download_thread and self.download_thread.isRunning():
            reply = QMessageBox.question(
                self, self.tr("Download in progress"),
                self.tr("A download is still active. Really quit?"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            else:
                self.cancel_download()
        event.accept()

    def tr(self, text):
        return QApplication.translate("YouTubeDownloaderApp", text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    locale = QLocale("en")
    QLocale.setDefault(locale)
    
    window = YouTubeDownloaderApp()
    window.show()
    sys.exit(app.exec_())