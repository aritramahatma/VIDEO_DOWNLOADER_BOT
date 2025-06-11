#!/usr/bin/env python3
"""
Telegram Video Downloader Bot
Downloads videos from various platforms and sends them to users
"""

import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from video_downloader import VideoDownloader
from config import Config
from utils import format_file_size, is_valid_url, cleanup_temp_files
import tempfile
import shutil

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VideoDownloaderBot:
    def __init__(self):
        self.config = Config()
        self.downloader = VideoDownloader()
        self.temp_dir = tempfile.mkdtemp()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        welcome_text = """
🎥 *Video Downloader Bot*

Welcome! I can download videos from various platforms including:
• YouTube
• Instagram
• Twitter/X
• TikTok
• Facebook
• And many more!

*How to use:*
1. Send me a video URL
2. Choose video quality (if available)
3. Wait for download and processing
4. Receive your video!

*Commands:*
/start - Show this message
/help - Get help
/about - About this bot

Just send me any video URL to get started! 🚀
        """
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help information."""
        help_text = """
🆘 *Help - Video Downloader Bot*

*Supported Platforms:*
• YouTube (youtube.com, youtu.be)
• Instagram (instagram.com)
• Twitter/X (twitter.com, x.com)
• TikTok (tiktok.com)
• Facebook (facebook.com)
• Reddit (reddit.com)
• And 1000+ other sites!

*How to Download:*
1. Copy the video URL from any supported platform
2. Send the URL to this bot
3. Select quality if options are available
4. Wait for processing
5. Download your video!

*File Size Limits:*
• Maximum file size: 50MB for bots
• Large files will be compressed automatically

*Tips:*
• Make sure the video is public/accessible
• Private videos cannot be downloaded
• Some platforms may have restrictions

Need more help? Contact the developer!
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def about(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send about information."""
        about_text = """
ℹ️ *About Video Downloader Bot*

This bot helps you download videos from various social media platforms and video hosting sites.

*Technology Stack:*
• Python 3.11
• yt-dlp for video extraction
• FFmpeg for video processing
• Telegram Bot API

*Features:*
• Support for 1000+ websites
• Multiple quality options
• Automatic video compression
• Fast and reliable downloads

*Version:* 1.0.0
*Developer:* Video Downloader Bot Team

⚠️ *Disclaimer:*
Please respect copyright laws and platform terms of service when downloading videos.
        """
        
        await update.message.reply_text(
            about_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video URL messages."""
        url = update.message.text.strip()
        
        if not is_valid_url(url):
            await update.message.reply_text(
                "❌ Please send a valid video URL.\n\n"
                "Example: https://www.youtube.com/watch?v=..."
            )
            return

        # Send initial processing message
        status_message = await update.message.reply_text(
            "🔍 *Processing your request...*\n"
            "Extracting video information...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Get video info
            video_info = await self.downloader.get_video_info(url)
            
            if not video_info:
                await status_message.edit_text(
                    "❌ *Error*\n"
                    "Could not extract video information. Please check the URL and try again.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Check if video has downloadable formats
            formats = video_info.get('formats', [])
            
            # Filter for video formats only
            video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('url')]
            
            if not video_formats:
                await status_message.edit_text(
                    "❌ *Download Not Available*\n"
                    "This video cannot be downloaded. It may be:\n"
                    "• Private or restricted\n"
                    "• Age-restricted content\n"
                    "• Temporarily unavailable\n"
                    "• From an unsupported platform feature\n\n"
                    "Please try a different video.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Sort formats by quality (height)
            video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
            
            # Check if we have multiple good quality options
            good_formats = [f for f in video_formats if f.get('height', 0) >= 360]
            
            if len(good_formats) > 1:
                # Show quality selection for high quality formats
                keyboard = []
                
                # Add quality options (limit to top 5)
                for i, fmt in enumerate(good_formats[:5]):
                    height = fmt.get('height', 'Unknown')
                    ext = fmt.get('ext', 'mp4')
                    filesize = fmt.get('filesize')
                    
                    quality_text = f"{height}p"
                    if ext != 'mp4':
                        quality_text += f" ({ext})"
                    if filesize:
                        quality_text += f" - {format_file_size(filesize)}"
                    
                    keyboard.append([InlineKeyboardButton(
                        quality_text,
                        callback_data=f"download_{fmt['format_id']}_{update.message.message_id}"
                    )])
                
                # Add best quality option
                keyboard.append([InlineKeyboardButton(
                    "🏆 Best Quality Available",
                    callback_data=f"download_best_{update.message.message_id}"
                )])

                reply_markup = InlineKeyboardMarkup(keyboard)
                
                title = video_info.get('title', 'Unknown')
                duration = video_info.get('duration')
                uploader = video_info.get('uploader', 'Unknown')
                
                info_text = f"🎥 *{title}*\n\n"
                if duration:
                    info_text += f"⏱ Duration: {duration//60}:{duration%60:02d}\n"
                info_text += f"👤 Uploader: {uploader}\n\n"
                info_text += "Select video quality:"

                await status_message.edit_text(
                    info_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                
                # Store URL for callback
                context.user_data[f"url_{update.message.message_id}"] = url
                
            else:
                # Download directly with best available quality
                await self.download_and_send_video(
                    update, context, status_message, url, "best"
                )

        except Exception as e:
            logger.error(f"Error processing URL {url}: {str(e)}")
            await status_message.edit_text(
                f"❌ *Error*\n"
                f"Failed to process video: {str(e)}\n\n"
                f"Please try again or check if the URL is accessible.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def handle_quality_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quality selection callback."""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        parts = callback_data.split('_')
        
        if len(parts) < 3:
            await query.edit_message_text("❌ Invalid selection. Please try again.")
            return
            
        format_id = parts[1]
        message_id = parts[2]
        
        # Get stored URL
        url = context.user_data.get(f"url_{message_id}")
        if not url:
            await query.edit_message_text("❌ Session expired. Please send the URL again.")
            return

        await self.download_and_send_video(
            update, context, query.message, url, format_id
        )

    async def download_and_send_video(self, update, context, status_message, url, format_id):
        """Download and send video to user."""
        try:
            # Update status
            await status_message.edit_text(
                "⬇️ *Downloading video...*\n"
                "This may take a few moments depending on video size.",
                parse_mode=ParseMode.MARKDOWN
            )

            # Download video
            download_path = await self.downloader.download_video(
                url, self.temp_dir, format_id
            )
            
            if not download_path or not os.path.exists(download_path):
                await status_message.edit_text(
                    "❌ *Download Failed*\n"
                    "Could not download the video. Please try again.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Check file size
            file_size = os.path.getsize(download_path)
            max_size = 50 * 1024 * 1024  # 50MB Telegram limit

            if file_size > max_size:
                await status_message.edit_text(
                    "🔄 *Compressing video...*\n"
                    "File is too large, compressing to fit Telegram limits.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Compress video
                compressed_path = await self.downloader.compress_video(
                    download_path, max_size
                )
                
                if compressed_path and os.path.exists(compressed_path):
                    download_path = compressed_path
                else:
                    await status_message.edit_text(
                        "❌ *Compression Failed*\n"
                        "Video is too large and compression failed.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return

            # Update status for upload
            await status_message.edit_text(
                "⬆️ *Uploading video...*\n"
                "Almost done!",
                parse_mode=ParseMode.MARKDOWN
            )

            # Send video
            chat_id = update.effective_chat.id
            with open(download_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    supports_streaming=True,
                    caption="✅ *Video downloaded successfully!*\n\n"
                           "Powered by Video Downloader Bot 🤖",
                    parse_mode=ParseMode.MARKDOWN
                )

            # Delete status message
            await status_message.delete()

            # Clean up temporary files
            try:
                os.remove(download_path)
            except:
                pass

        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            await status_message.edit_text(
                f"❌ *Download Failed*\n"
                f"Error: {str(e)}\n\n"
                f"Please try again or contact support.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )

    def run(self):
        """Start the bot."""
        # Create application
        application = Application.builder().token(self.config.BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("about", self.about))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url))
        application.add_handler(CallbackQueryHandler(self.handle_quality_selection))
        
        # Add error handler
        application.add_error_handler(self.error_handler)

        logger.info("Starting Video Downloader Bot...")
        
        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function."""
    try:
        bot = VideoDownloaderBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
    finally:
        # Cleanup
        cleanup_temp_files()

if __name__ == '__main__':
    main()
