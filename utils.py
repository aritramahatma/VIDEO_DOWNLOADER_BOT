"""
Utility functions for Video Downloader Bot
"""

import os
import re
import shutil
import tempfile
import logging
from urllib.parse import urlparse
from typing import Optional

logger = logging.getLogger(__name__)

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def is_valid_url(url: str) -> bool:
    """Check if the provided string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various platform URLs."""
    patterns = {
        'youtube': [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
        ],
        'instagram': [
            r'instagram\.com\/p\/([^\/\?]+)',
            r'instagram\.com\/reel\/([^\/\?]+)',
            r'instagram\.com\/tv\/([^\/\?]+)'
        ],
        'tiktok': [
            r'tiktok\.com\/.*\/video\/(\d+)',
            r'vm\.tiktok\.com\/([^\/\?]+)',
            r'tiktok\.com\/@[^\/]+\/video\/(\d+)'
        ],
        'twitter': [
            r'twitter\.com\/\w+\/status\/(\d+)',
            r'x\.com\/\w+\/status\/(\d+)'
        ]
    }
    
    for platform, platform_patterns in patterns.items():
        for pattern in platform_patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
    
    return None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    # Remove invalid characters for most file systems
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length to 255 characters (most file systems limit)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        max_name_length = 255 - len(ext)
        filename = name[:max_name_length] + ext
    
    return filename

def get_video_platform(url: str) -> Optional[str]:
    """Identify video platform from URL."""
    domain_patterns = {
        'youtube': ['youtube.com', 'youtu.be', 'm.youtube.com'],
        'instagram': ['instagram.com', 'www.instagram.com'],
        'tiktok': ['tiktok.com', 'www.tiktok.com', 'vm.tiktok.com'],
        'twitter': ['twitter.com', 'x.com', 'mobile.twitter.com'],
        'facebook': ['facebook.com', 'www.facebook.com', 'm.facebook.com', 'fb.watch'],
        'reddit': ['reddit.com', 'www.reddit.com', 'v.redd.it'],
        'twitch': ['twitch.tv', 'www.twitch.tv', 'clips.twitch.tv'],
        'vimeo': ['vimeo.com', 'www.vimeo.com']
    }
    
    try:
        domain = urlparse(url).netloc.lower()
        
        for platform, domains in domain_patterns.items():
            if any(domain.endswith(d) for d in domains):
                return platform
        
        return 'unknown'
        
    except Exception:
        return None

def cleanup_temp_files(temp_dir: Optional[str] = None):
    """Clean up temporary files and directories."""
    try:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
        
        # Also clean up system temp files related to this bot
        temp_prefix = "video_downloader_bot_"
        temp_root = tempfile.gettempdir()
        
        for item in os.listdir(temp_root):
            if item.startswith(temp_prefix):
                item_path = os.path.join(temp_root, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    logger.warning(f"Could not remove temp item {item_path}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

def validate_video_file(file_path: str) -> bool:
    """Validate if file is a proper video file."""
    if not os.path.exists(file_path):
        return False
    
    # Check file size (should be > 0)
    if os.path.getsize(file_path) == 0:
        return False
    
    # Check file extension
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    file_ext = os.path.splitext(file_path)[1].lower()
    
    return file_ext in video_extensions

def get_file_info(file_path: str) -> dict:
    """Get basic file information."""
    if not os.path.exists(file_path):
        return {}
    
    stat = os.stat(file_path)
    
    return {
        'size': stat.st_size,
        'size_formatted': format_file_size(stat.st_size),
        'modified': stat.st_mtime,
        'name': os.path.basename(file_path),
        'extension': os.path.splitext(file_path)[1],
        'directory': os.path.dirname(file_path)
    }

def create_progress_bar(current: int, total: int, length: int = 20) -> str:
    """Create a text progress bar."""
    if total == 0:
        return "█" * length
    
    filled_length = int(length * current // total)
    bar = "█" * filled_length + "░" * (length - filled_length)
    percent = round(100.0 * current / total, 1)
    
    return f"{bar} {percent}%"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def escape_markdown(text: str) -> str:
    """Escape markdown special characters."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def validate_telegram_file_size(file_path: str) -> tuple[bool, str]:
    """Validate if file meets Telegram size requirements."""
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    file_size = os.path.getsize(file_path)
    max_size = 50 * 1024 * 1024  # 50MB
    
    if file_size > max_size:
        return False, f"File too large: {format_file_size(file_size)} (max: {format_file_size(max_size)})"
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, "File size OK"
