# Video Downloader Bot

A powerful Telegram bot that can download videos from various platforms including YouTube, Instagram, TikTok, Twitter, Facebook, and many more using Python and ffmpeg.

## Features

- 🎥 **Multi-platform Support**: Download videos from 1000+ websites
- 🔧 **Quality Selection**: Choose from available video qualities
- 📱 **Smart Compression**: Automatic video compression for Telegram limits
- ⚡ **Fast Processing**: Efficient download and processing pipeline
- 🛡️ **Error Handling**: Comprehensive error handling and user feedback
- 📊 **Progress Updates**: Real-time download and processing status

## Supported Platforms

- YouTube (youtube.com, youtu.be)
- Instagram (instagram.com)
- Twitter/X (twitter.com, x.com)
- TikTok (tiktok.com)
- Facebook (facebook.com)
- Reddit (reddit.com)
- Twitch (twitch.tv)
- Vimeo (vimeo.com)
- And 1000+ other sites supported by yt-dlp

## Installation

### Prerequisites

- Python 3.11+
- ffmpeg
- A Telegram Bot Token

### For Replit

1. Clone this repository to Replit
2. The `replit.nix` file will automatically install required dependencies
3. Set your bot token in the Secrets tab:
   - Key: `BOT_TOKEN`
   - Value: Your Telegram bot token from @BotFather

### For Local Development

1. Install Python dependencies:
```bash
pip install python-telegram-bot yt-dlp
