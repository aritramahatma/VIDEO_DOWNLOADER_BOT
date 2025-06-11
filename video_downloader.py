"""
Video Downloader Module
Handles video downloading and processing using yt-dlp and ffmpeg
"""

import os
import asyncio
import logging
import subprocess
import tempfile
from typing import Optional, Dict, Any
import yt_dlp
from utils import format_file_size

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        self.ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'format': 'best',
            'cookiefile': None,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'age_limit': None,
            'max_filesize': 500 * 1024 * 1024,  # 500MB max
        }
        
    async def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get video information without downloading."""
        try:
            def extract_info():
                with yt_dlp.YoutubeDL(self.ydl_opts_info) as ydl:
                    info = ydl.extract_info(url, download=False)
                    # Filter and validate formats
                    if info and 'formats' in info:
                        valid_formats = []
                        for fmt in info['formats']:
                            if self._is_format_downloadable(fmt):
                                valid_formats.append(fmt)
                        info['formats'] = valid_formats
                    return info
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, extract_info)
            
            return info
            
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            return None

    def _is_format_downloadable(self, fmt: dict) -> bool:
        """Check if a format is actually downloadable."""
        # Skip audio-only formats
        if fmt.get('vcodec') == 'none':
            return False
        
        # Skip formats without URL
        if not fmt.get('url'):
            return False
        
        # Skip formats that are marked as unavailable
        format_note = fmt.get('format_note', '')
        if format_note and 'unavailable' in str(format_note).lower():
            return False
        
        # Skip very low quality formats (below 144p)
        height = fmt.get('height', 0)
        if height > 0 and height < 144:
            return False
        
        # Skip corrupted or incomplete formats
        if fmt.get('filesize') == 0:
            return False
            
        return True

    async def download_video(self, url: str, output_dir: str, format_id: str = "best") -> Optional[str]:
        """Download video with specified format."""
        try:
            # Prepare output template
            output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
            
            # Configure yt-dlp options with better Instagram support
            ydl_opts = {
                'format': format_id,
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': False,
                'retries': 3,
                'fragment_retries': 3,
                'http_chunk_size': 10485760,  # 10MB chunks
                'max_filesize': 500 * 1024 * 1024,  # 500MB max
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            }
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                    # Get the actual filename
                    if info and isinstance(info, dict) and 'entries' in info and info['entries']:
                        # Playlist - get first video
                        video_info = info['entries'][0]
                    else:
                        video_info = info
                    
                    filename = ydl.prepare_filename(video_info)
                    return filename
            
            # Run download in thread pool
            loop = asyncio.get_event_loop()
            filename = await loop.run_in_executor(None, download)
            
            # Check if file exists and return path
            if os.path.exists(filename):
                return filename
            else:
                # Sometimes the extension might be different
                base_name = os.path.splitext(filename)[0]
                for ext in ['.mp4', '.mkv', '.webm', '.avi', '.mov']:
                    potential_file = base_name + ext
                    if os.path.exists(potential_file):
                        return potential_file
                
                logger.error(f"Downloaded file not found: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return None

    async def compress_video(self, input_path: str, max_size_bytes: int) -> Optional[str]:
        """Compress video to fit within size limit using ffmpeg."""
        try:
            if not os.path.exists(input_path):
                logger.error(f"Input file does not exist: {input_path}")
                return None

            # Get video duration
            duration = await self._get_video_duration(input_path)
            if not duration:
                logger.error("Could not get video duration")
                return None

            # Calculate target bitrate (80% of max to leave some headroom)
            target_bitrate = int((max_size_bytes * 0.8 * 8) / duration / 1000)  # kbps
            
            # Minimum bitrate threshold
            if target_bitrate < 100:
                logger.error(f"Target bitrate too low: {target_bitrate}kbps")
                return None

            # Output path
            output_path = input_path.rsplit('.', 1)[0] + '_compressed.mp4'
            
            # FFmpeg command for compression
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',
                '-b:v', f'{target_bitrate}k',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-preset', 'fast',
                '-movflags', '+faststart',
                '-y',  # Overwrite output file
                output_path
            ]
            
            def run_ffmpeg():
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return process
            
            # Run FFmpeg in thread pool
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(None, run_ffmpeg)
            
            if process.returncode == 0 and os.path.exists(output_path):
                # Check if compressed file is smaller
                compressed_size = os.path.getsize(output_path)
                if compressed_size <= max_size_bytes:
                    logger.info(f"Video compressed successfully: {format_file_size(compressed_size)}")
                    return output_path
                else:
                    logger.warning(f"Compressed file still too large: {format_file_size(compressed_size)}")
                    # Try with lower bitrate
                    os.remove(output_path)
                    return await self._compress_aggressively(input_path, max_size_bytes, duration)
            else:
                logger.error(f"FFmpeg compression failed: {process.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error compressing video: {str(e)}")
            return None

    async def _compress_aggressively(self, input_path: str, max_size_bytes: int, duration: float) -> Optional[str]:
        """More aggressive compression for very large files."""
        try:
            # Even lower bitrate (60% of max)
            target_bitrate = int((max_size_bytes * 0.6 * 8) / duration / 1000)
            
            if target_bitrate < 50:
                logger.error("Cannot compress further - file too large")
                return None

            output_path = input_path.rsplit('.', 1)[0] + '_compressed_aggressive.mp4'
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',
                '-b:v', f'{target_bitrate}k',
                '-c:a', 'aac',
                '-b:a', '64k',  # Lower audio bitrate
                '-preset', 'ultrafast',
                '-crf', '28',  # Higher compression
                '-movflags', '+faststart',
                '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',  # Ensure even dimensions
                '-y',
                output_path
            ]
            
            def run_ffmpeg():
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return process
            
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(None, run_ffmpeg)
            
            if process.returncode == 0 and os.path.exists(output_path):
                compressed_size = os.path.getsize(output_path)
                if compressed_size <= max_size_bytes:
                    logger.info(f"Video aggressively compressed: {format_file_size(compressed_size)}")
                    return output_path
                else:
                    logger.error(f"Even aggressive compression failed: {format_file_size(compressed_size)}")
                    os.remove(output_path)
                    return None
            else:
                logger.error(f"Aggressive FFmpeg compression failed: {process.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error in aggressive compression: {str(e)}")
            return None

    async def _get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration using ffprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            def run_ffprobe():
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return process
            
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(None, run_ffprobe)
            
            if process.returncode == 0:
                import json
                data = json.loads(process.stdout)
                duration = float(data['format']['duration'])
                return duration
            else:
                logger.error(f"ffprobe failed: {process.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting video duration: {str(e)}")
            return None

    def get_supported_sites(self) -> list:
        """Get list of supported sites from yt-dlp."""
        try:
            extractors = yt_dlp.list_extractors()
            sites = []
            for extractor in extractors:
                if hasattr(extractor, 'IE_NAME'):
                    sites.append(extractor.IE_NAME)
            return sorted(sites)
        except Exception as e:
            logger.error(f"Error getting supported sites: {str(e)}")
            return []
