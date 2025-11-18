#!/usr/bin/env python3
import os
import requests
import argparse
import time
import random
import concurrent.futures
import queue
import threading
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json
from pathlib import Path
import hashlib

# Constants for performance tuning
DEFAULT_CHUNK_SIZE = 8192  # 8KB chunks
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_THREADS = 3  # concurrent downloads
DEFAULT_CONFIG_FILE = 'osu_downloader_config.json'
DEFAULT_LOG_LEVEL = 'INFO'

# Set up logger
logging.basicConfig(
    level=DEFAULT_LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('osu_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('osu_downloader')

class DownloadManager:
    """Manages the download queue and workers."""
    
    def __init__(self, download_dir, max_threads=DEFAULT_THREADS, 
                 chunk_size=DEFAULT_CHUNK_SIZE, delay=True, 
                 resume=True, bandwidth_limit=None):
        self.download_dir = download_dir
        self.max_threads = max_threads
        self.chunk_size = chunk_size
        self.delay = delay
        self.resume = resume
        self.bandwidth_limit = bandwidth_limit
        
        # Create download directory
        os.makedirs(download_dir, exist_ok=True)
        
        # Download queue and results
        self.queue = queue.Queue()
        self.results = {}
        self.downloads_in_progress = {}
        self.lock = threading.Lock()
        
        # Progress tracking
        self.total_packs = 0
        self.completed_packs = 0
        self.failed_packs = 0
        self.progress_lock = threading.Lock()
        
        # Status for each pack
        self.pack_status = {}
        
    def add_pack(self, pack_number):
        """Add a pack to the download queue."""
        self.queue.put(pack_number)
        self.total_packs += 1
        self.pack_status[pack_number] = {
            'status': 'queued',
            'attempts': 0,
            'url': None,
            'file_path': None,
            'size': 0,
            'downloaded': 0,
            'speed': 0
        }
    
    def start_downloads(self):
        """Start the download process with multiple threads."""
        logger.info(f"Starting {self.max_threads} download threads for {self.total_packs} packs")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # Start the progress reporter in a separate thread
            progress_thread = threading.Thread(target=self._progress_reporter)
            progress_thread.daemon = True
            progress_thread.start()
            
            # Submit download tasks
            futures = []
            for _ in range(min(self.max_threads, self.total_packs)):
                future = executor.submit(self._download_worker)
                futures.append(future)
            
            # Wait for all tasks to complete
            concurrent.futures.wait(futures)
            
        # Final progress report
        self._print_final_summary()
        
        return self.results
    
    def _download_worker(self):
        """Worker function that processes the download queue."""
        # Create a session for this worker
        session = self._create_optimized_session()
        
        while not self.queue.empty():
            try:
                # Get the next pack from the queue
                pack_number = self.queue.get(block=False)
                
                # Update pack status
                with self.lock:
                    self.pack_status[pack_number]['status'] = 'downloading'
                    self.downloads_in_progress[pack_number] = True
                
                # Try to download the pack
                success, url, file_path = self._download_pack(pack_number, session)
                
                # Update results
                with self.lock:
                    self.results[pack_number] = {
                        'success': success,
                        'url': url,
                        'file_path': file_path
                    }
                    
                    # Update counters
                    with self.progress_lock:
                        if success:
                            self.completed_packs += 1
                            self.pack_status[pack_number]['status'] = 'completed'
                        else:
                            self.failed_packs += 1
                            self.pack_status[pack_number]['status'] = 'failed'
                        
                        # Remove from in-progress list
                        if pack_number in self.downloads_in_progress:
                            del self.downloads_in_progress[pack_number]
                
                # Delay between downloads if enabled
                if self.delay and success:
                    delay_time = random.uniform(0.5, 1.5)
                    time.sleep(delay_time)
                
            except queue.Empty:
                break  # Queue is empty, worker is done
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                with self.progress_lock:
                    self.failed_packs += 1
    
    def _progress_reporter(self):
        """Reports progress periodically without breaking the terminal."""
        last_report_time = time.time()
        
        while self.completed_packs + self.failed_packs < self.total_packs:
            current_time = time.time()
            
            # Report every second
            if current_time - last_report_time >= 1.0:
                self._print_progress()
                last_report_time = current_time
            
            time.sleep(0.2)  # Check progress 5 times per second
    
    def _print_progress(self):
        """Print the current progress without breaking terminal output."""
        with self.progress_lock:
            completed = self.completed_packs
            failed = self.failed_packs
            total = self.total_packs
            in_progress = len(self.downloads_in_progress)
            
            # Get in-progress download information
            active_downloads = []
            for pack_num, status in self.pack_status.items():
                if status['status'] == 'downloading' and status['size'] > 0:
                    progress = (status['downloaded'] / status['size']) * 100
                    active_downloads.append(f"Pack #{pack_num}: {progress:.1f}% at {status['speed']:.1f} MB/s")
            
            # Clear the current line
            print("\033[K", end="\r")
            
            # Print the overall progress
            progress_percent = ((completed + failed) / total * 100) if total > 0 else 0
            print(f"Progress: {completed}/{total} complete, {failed} failed ({progress_percent:.1f}%)", end="")
            
            # Print active downloads (limit to 3 to avoid cluttering)
            if active_downloads:
                active_str = ", ".join(active_downloads[:3])
                if len(active_downloads) > 3:
                    active_str += f" (+ {len(active_downloads) - 3} more)"
                print(f" | {active_str}", end="")
            
            print("", end="\r", flush=True)

    def _print_final_summary(self):
        """Print a final summary of the download process."""
        # Clear the current line
        print("\033[K", end="\r")
        
        # Print summary
        print(f"Download complete: {self.completed_packs}/{self.total_packs} successful, {self.failed_packs} failed")
        
        # List failed packs if any
        if self.failed_packs > 0:
            failed_packs = [pack for pack, result in self.results.items() if not result['success']]
            print(f"Failed packs: {', '.join(map(str, failed_packs))}")
    
    def _create_optimized_session(self):
        """Create a requests session with optimized settings for downloads."""
        session = requests.Session()
        
        # Configure retries with backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        # Apply retry strategy to both http and https
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set a reasonable timeout
        session.timeout = DEFAULT_TIMEOUT
        
        # Set headers to mimic a browser
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        
        return session
    
    def _get_download_urls(self, pack_number):
        """Generate possible download URLs for a given pack number."""
        return [
            f"https://packs.ppy.sh/S{pack_number}%20-%20osu%21%20Beatmap%20Pack%20%23{pack_number}.zip",
            f"https://packs.ppy.sh/S{pack_number}%20-%20Beatmap%20Pack%20%23{pack_number}.zip",
            f"https://packs.ppy.sh/S{pack_number}%20-%20Beatmap%20Pack%20%23{pack_number}.7z"
        ]
    
    def _get_filename_from_url(self, url, pack_number):
        """Extract appropriate filename from URL."""
        if url.endswith('.7z'):
            return f"Beatmap Pack #{pack_number}.7z"
        elif "osu%21" in url:
            return f"osu! Beatmap Pack #{pack_number}.zip"
        else:
            return f"Beatmap Pack #{pack_number}.zip"
    
    def _download_pack(self, pack_number, session):
        """Download a specific beatmap pack by trying different URL patterns."""
        possible_urls = self._get_download_urls(pack_number)
        
        # Check if any of the possible files already exist
        for url in possible_urls:
            filename = self._get_filename_from_url(url, pack_number)
            filepath = os.path.join(self.download_dir, filename)
            if os.path.exists(filepath):
                logger.info(f"Pack #{pack_number} already exists as {filename}. Skipping.")
                return True, url, filepath
        
        # Try each possible URL pattern
        for url in possible_urls:
            filename = self._get_filename_from_url(url, pack_number)
            filepath = os.path.join(self.download_dir, filename)
            temp_filepath = f"{filepath}.part"
            
            # Set file paths in status
            with self.lock:
                self.pack_status[pack_number]['file_path'] = filepath
                self.pack_status[pack_number]['url'] = url
            
            # Check for partially downloaded file
            resume_size = 0
            if self.resume and os.path.exists(temp_filepath):
                resume_size = os.path.getsize(temp_filepath)
                logger.info(f"Resuming download of pack #{pack_number} from {resume_size} bytes")
            
            try:
                logger.info(f"Trying URL: {url}")
                
                # Use a HEAD request first to check if the URL is valid and get content length
                headers = {}
                if resume_size > 0:
                    headers['Range'] = f'bytes={resume_size}-'
                
                head_response = session.head(url, allow_redirects=True)
                
                # If we got a 404, try the next URL pattern
                if head_response.status_code == 404:
                    logger.info(f"URL not found: {url}")
                    continue
                
                # Check if the URL is valid
                if head_response.status_code != 200 and head_response.status_code != 206:
                    logger.warning(f"Failed to access URL. HTTP Status: {head_response.status_code}")
                    continue
                
                # Get the download size
                total_size = int(head_response.headers.get('content-length', 0))
                if resume_size > 0 and head_response.status_code == 200:
                    # Server doesn't support range requests, restart download
                    resume_size = 0
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                
                # Update status with size
                with self.lock:
                    self.pack_status[pack_number]['size'] = total_size + resume_size
                
                # Stream the download with larger chunks
                response = session.get(url, stream=True, headers=headers)
                
                # Open file in appropriate mode based on whether resuming
                file_mode = 'ab' if resume_size > 0 else 'wb'
                
                with open(temp_filepath, file_mode) as file:
                    start_time = time.time()
                    downloaded = resume_size
                    last_update_time = start_time
                    bytes_since_last_update = 0
                    
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            file.write(chunk)
                            
                            # Update progress
                            downloaded += len(chunk)
                            bytes_since_last_update += len(chunk)
                            
                            # Update download speed every second
                            current_time = time.time()
                            if current_time - last_update_time >= 1.0:
                                elapsed = current_time - last_update_time
                                speed = bytes_since_last_update / elapsed / (1024 * 1024)  # MB/s
                                
                                with self.lock:
                                    self.pack_status[pack_number]['downloaded'] = downloaded
                                    self.pack_status[pack_number]['speed'] = speed
                                
                                bytes_since_last_update = 0
                                last_update_time = current_time
                            
                            # Implement bandwidth limiting if needed
                            if self.bandwidth_limit:
                                ideal_time = len(chunk) / (self.bandwidth_limit * 1024 * 1024)
                                actual_time = time.time() - start_time
                                if ideal_time > actual_time:
                                    time.sleep(ideal_time - actual_time)
                
                # Rename the file when download is complete
                os.rename(temp_filepath, filepath)
                logger.info(f"Successfully downloaded Pack #{pack_number}")
                
                return True, url, filepath
                
            except Exception as e:
                logger.error(f"Error downloading {url} for pack #{pack_number}: {str(e)}")
        
        logger.error(f"Failed to download Pack #{pack_number} after trying all URL patterns.")
        return False, None, None


class ConfigManager:
    """Manages configuration and saved state."""
    
    def __init__(self, config_file=DEFAULT_CONFIG_FILE):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or return defaults."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config file: {str(e)}")
        
        # Return default config
        return {
            'download_dir': './osu_packs',
            'threads': DEFAULT_THREADS,
            'chunk_size': DEFAULT_CHUNK_SIZE,
            'delay': True,
            'completed_packs': [],
            'failed_packs': []
        }
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config file: {str(e)}")
    
    def update_downloaded_packs(self, results):
        """Update the list of completed packs."""
        for pack_num, result in results.items():
            if result['success']:
                if pack_num not in self.config['completed_packs']:
                    self.config['completed_packs'].append(pack_num)
            else:
                if pack_num not in self.config['failed_packs']:
                    self.config['failed_packs'].append(pack_num)
        
        # Sort the lists
        self.config['completed_packs'].sort()
        self.config['failed_packs'].sort()
        
        # Save the updated config
        self.save_config()


def main():
    parser = argparse.ArgumentParser(description='Advanced osu! Beatmap Pack Downloader')
    parser.add_argument('--start', type=int, help='Starting pack number')
    parser.add_argument('--end', type=int, help='Ending pack number (inclusive)')
    parser.add_argument('--packs', type=str, help='Comma-separated list of specific pack numbers')
    parser.add_argument('--dir', type=str, help='Directory to save the packs')
    parser.add_argument('--no-delay', action='store_true', help='Disable random delay between downloads')
    parser.add_argument('--threads', type=int, help=f'Number of concurrent downloads (default: {DEFAULT_THREADS})')
    parser.add_argument('--chunk-size', type=int, help=f'Download chunk size in bytes (default: {DEFAULT_CHUNK_SIZE})')
    parser.add_argument('--no-resume', action='store_true', help='Disable resuming of partial downloads')
    parser.add_argument('--retry-failed', action='store_true', help='Retry previously failed downloads')
    parser.add_argument('--config', type=str, default=DEFAULT_CONFIG_FILE, help='Configuration file path')
    parser.add_argument('--bandwidth-limit', type=float, help='Limit download bandwidth in MB/s per thread')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default=DEFAULT_LOG_LEVEL, help='Set logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(args.log_level)
    
    # Load config
    config_manager = ConfigManager(args.config)
    config = config_manager.config
    
    # Override config with command line arguments
    download_dir = args.dir or config['download_dir']
    threads = args.threads or config['threads']
    chunk_size = args.chunk_size or config['chunk_size']
    delay = not args.no_delay if args.no_delay is not None else config['delay']
    
    # Get pack numbers to download
    pack_numbers = []
    
    # Handle range of pack numbers
    if args.start and args.end:
        if args.start > args.end:
            parser.error("Start number must be less than or equal to end number")
        pack_numbers.extend(range(args.start, args.end + 1))
    
    # Handle specific pack numbers
    if args.packs:
        try:
            specific_packs = [int(num.strip()) for num in args.packs.split(',')]
            pack_numbers.extend(specific_packs)
        except ValueError:
            parser.error("Pack numbers must be integers")
    
    # Handle retry of failed downloads
    if args.retry_failed and config['failed_packs']:
        pack_numbers.extend(config['failed_packs'])
    
    # Remove duplicates, sort, and filter out already completed packs (unless overridden)
    pack_numbers = sorted(set(pack_numbers))
    if not args.retry_failed:
        pack_numbers = [p for p in pack_numbers if p not in config['completed_packs']]
    
    if not pack_numbers:
        parser.error("No packs specified to download. Use --start/--end, --packs, or --retry-failed")
    
    # Create download manager
    download_manager = DownloadManager(
        download_dir=download_dir,
        max_threads=threads,
        chunk_size=chunk_size,
        delay=delay,
        resume=not args.no_resume,
        bandwidth_limit=args.bandwidth_limit
    )
    
    # Add packs to queue
    for pack_num in pack_numbers:
        download_manager.add_pack(pack_num)
    
    # Start downloads
    results = download_manager.start_downloads()
    
    # Update config with results
    config_manager.update_downloaded_packs(results)
    
    return 0

if __name__ == "__main__":
    main()