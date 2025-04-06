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
pyinstaller --onefile --windowed --icon=resources/logo.ico src/media_downloader.py

Supported Platforms

    YouTube

    All other platforms supported by yt-dlp


License

GNU GPLv3 - See LICENSE


Note
This software uses yt-dlp under The Unlicense.
Please respect copyright laws when downloading content.

### Key advantages of this README:
1. **Visual-first** - Space for screenshots/animations (add these later)
2. **Feature highlights** - Using emojis for quick scanning
3. **Clear sections** - Separated usage, building, and legal info
4. **Concise** - Under 50 lines but covers all essentials
5. **Professional** - Follows GitHub best practices

### Recommended next steps:
1. Create a `docs/` folder with:
   - `screenshot.png` (800x600px)
   - `usage.gif` (short 10-15sec screen recording)
2. Replace `yourusername` with your actual GitHub username
3. Upload your EXE to Releases when you create the repo

Would you like me to:
- Add a German version below the English one?
- Include more technical details about the implementation?
- Create a simpler version without the build instructions?