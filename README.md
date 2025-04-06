# Media Downloader Pro

![Application Screenshot](docs/screenshot.png) *(optional - add a screenshot later)*

A user-friendly GUI application for downloading videos and audio from various platforms.

## Features
- 🎥 Download videos as MP4 (720p, 1080p, or best quality)
- 🎵 Extract audio as MP3 (192kbps or 320kbps)
- 🌙 Dark/Light theme toggle
- 🌍 Multi-language support (English/German)
- 📝 Batch URL processing
- 📊 Real-time progress tracking

## Download
Ready-to-use Windows executable:  
[Download Latest Release](https://github.com/yourusername/Media-Downloader-Pro/releases) *(you'll create this after uploading)*

## Usage
1. Paste URLs (one per line)
2. Select output format/quality
3. Choose download folder
4. Click "Download Now"

![UI Demo](docs/usage.gif) *(optional - add a short screen recording later)*

## Requirements
- Windows 10/11
- [Python 3.8+](https://www.python.org/downloads/) (for source version)

## Build from Source
```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python src/media_downloader.py

# Build executable (requires PyInstaller)
pyinstaller --onefile --noconsole --icon=resources/logo.ico --add-data="resources/logo.ico;resources" --add-data="../LICENSE.txt;." media_downloader.py

Supported Platforms

    YouTube

    All other platforms supported by yt-dlp


License

GNU GPLv3 - See LICENSE


Note
This software uses yt-dlp under The Unlicense.
Please respect copyright laws when downloading content.



