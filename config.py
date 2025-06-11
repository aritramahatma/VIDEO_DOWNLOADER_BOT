"""
Configuration module for Video Downloader Bot
"""

import os
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration class for bot settings."""
    
    def __init__(self):
        self.BOT_TOKEN = self._get_bot_token()
        self.MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - Telegram limit
        self.TEMP_DIR = os.path.join(os.getcwd(), 'temp')
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        
        # Create temp directory if it doesn't exist
        if not os.path.exists(self.TEMP_DIR):
            os.makedirs(self.TEMP_DIR)
    
    def _get_bot_token(self) -> str:
        """Get bot token from environment variables."""
        token = os.getenv('BOT_TOKEN')
        
        if not token:
            # Try alternative environment variable names
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            
        if not token:
            token = os.getenv('TELE_TOKEN')
            
        if not token:
            logger.error("Bot token not found in environment variables!")
            logger.error("Please set BOT_TOKEN, TELEGRAM_BOT_TOKEN, or TELE_TOKEN environment variable")
            raise ValueError("Bot token is required but not found in environment variables")
        
        return token
    
    def validate_config(self) -> bool:
        """Validate configuration settings."""
        try:
            if not self.BOT_TOKEN:
                logger.error("Bot token is missing")
                return False
                
            if not os.path.exists(self.TEMP_DIR):
                logger.error(f"Temp directory does not exist: {self.TEMP_DIR}")
                return False
                
            # Check if ffmpeg is available
            import subprocess
            try:
                subprocess.run(['ffmpeg', '-version'], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, 
                             check=True)
                logger.info("FFmpeg is available")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("FFmpeg is not available. Please install ffmpeg.")
                return False
            
            # Check if ffprobe is available
            try:
                subprocess.run(['ffprobe', '-version'], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, 
                             check=True)
                logger.info("FFprobe is available")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("FFprobe is not available. Please install ffmpeg with ffprobe.")
                return False
            
            logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False

# Global config instance
config = Config()
