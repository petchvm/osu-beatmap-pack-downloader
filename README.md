# osu! Beatmap Pack Downloader

A powerful and user-friendly tool for automatically downloading osu! Beatmap Packs from the official website.

![Terminal Preview](https://i.ibb.co/Nd539wH9/screen.png)

## Features

- **Multi-threaded downloading**: Download multiple packs simultaneously
- **Smart URL detection**: Automatically detects the correct URL pattern for each pack
- **Resume capability**: Continue interrupted downloads where you left off
- **Download queue**: Efficiently manages the download order
- **Progress tracking**: Real-time download speed and progress display
- **Configuration persistence**: Remembers which packs you've already downloaded
- **Bandwidth control**: Optional download speed limiting
- **Comprehensive logging**: Detailed logs for troubleshooting

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
  - [Using uv (Recommended)](#using-uv-recommended)
  - [Using pip](#using-pip)
- [Basic Usage](#basic-usage)
- [Advanced Usage](#advanced-usage)
- [Command-Line Options](#command-line-options)
- [Configuration](#configuration)
- [Understanding the Output](#understanding-the-output)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [How It Works](#how-it-works)
- [FAQ](#faq)

## Quick Start

Get started in 60 seconds:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/yourusername/osu-beatmap-pack-downloader.git
cd osu-beatmap-pack-downloader
uv sync

# Download packs
uv run osu-downloader --start 1580 --end 1590
```

## Installation

### Prerequisites

- Python 3.13 or higher
- Internet connection
- ~500MB free disk space per beatmap pack

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast, reliable Python package manager. Here's how to install:

1. **Install uv**:
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/osu-beatmap-pack-downloader.git
   cd osu-beatmap-pack-downloader
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

   This will automatically:
   - Create a virtual environment (`.venv/`)
   - Install all dependencies from `uv.lock`
   - Set up the `osu-downloader` command

4. **Verify installation**:
   ```bash
   uv run osu-downloader --help
   ```

**Note:** The `uv.lock` file ensures everyone gets the same dependency versions for reproducibility.

### Using pip

If you prefer pip or can't use uv:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/osu-beatmap-pack-downloader.git
   cd osu-beatmap-pack-downloader
   ```

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv .venv

   # On Windows
   .venv\Scripts\activate

   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install package**:
   ```bash
   pip install -e .
   ```

## Basic Usage

### Downloading a Range of Packs

To download packs #1580 through #1590:

```bash
osu-downloader --start 1580 --end 1590
```

### Downloading Specific Packs

To download specific packs (e.g., #1586, #1587, and #1590):

```bash
osu-downloader --packs 1586,1587,1590
```

### Specifying a Download Directory

By default, packs are saved to `./osu_packs`. To change this:

```bash
# Unix/Linux/macOS
osu-downloader --start 1580 --end 1590 --dir ~/osu-packs

# Windows
osu-downloader --start 1580 --end 1590 --dir "D:\OsuBeatmaps"
```

## Advanced Usage

### Concurrent Downloads

Increase download speed by running multiple downloads simultaneously:

```bash
osu-downloader --start 1580 --end 1590 --threads 5
```

### Adjusting Chunk Size

For faster downloads on high-speed connections, increase the chunk size:

```bash
osu-downloader --start 1580 --end 1590 --chunk-size 16384
```

### Limiting Bandwidth

Limit download speed (useful when you need to use your network for other tasks):

```bash
osu-downloader --start 1580 --end 1590 --bandwidth-limit 5.0
```
This will limit each thread to 5 MB/s (total bandwidth used will be `threads × limit`).

### Retry Failed Downloads

Resume any previously failed downloads:

```bash
osu-downloader --retry-failed
```

### Disable Resuming

Start fresh downloads even if partial downloads exist:

```bash
osu-downloader --start 1580 --end 1590 --no-resume
```

### Disable Delays

For maximum speed (use with caution as it might stress the server):

```bash
osu-downloader --start 1580 --end 1590 --no-delay
```

### Debugging

Increase log verbosity for troubleshooting:

```bash
osu-downloader --start 1580 --end 1590 --log-level DEBUG
```

## Command-Line Options

Here's the complete list of available options:

| Option | Description | Default |
|--------|-------------|---------|
| `--start` | Starting pack number | None |
| `--end` | Ending pack number (inclusive) | None |
| `--packs` | Comma-separated list of specific pack numbers | None |
| `--dir` | Directory to save the packs | `./osu_packs` |
| `--threads` | Number of concurrent downloads | 3 |
| `--chunk-size` | Download chunk size in bytes | 8192 |
| `--no-delay` | Disable random delay between downloads | False |
| `--no-resume` | Disable resuming of partial downloads | False |
| `--retry-failed` | Retry previously failed downloads | False |
| `--config` | Configuration file path | `osu_downloader_config.json` |
| `--bandwidth-limit` | Limit download bandwidth in MB/s per thread | None |
| `--log-level` | Set logging level (DEBUG, INFO, WARNING, ERROR) | INFO |

## Configuration

The downloader creates a configuration file at `osu_downloader_config.json` to track your downloads and remember settings.

### Configuration File Structure

```json
{
  "download_dir": "./osu_packs",
  "threads": 3,
  "chunk_size": 8192,
  "delay": true,
  "completed_packs": [1589, 1590, 1631, 1632],
  "failed_packs": []
}
```

### Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `download_dir` | string | Default download location |
| `threads` | integer | Default concurrent downloads |
| `chunk_size` | integer | Download chunk size in bytes |
| `delay` | boolean | Whether to add delays between downloads |
| `completed_packs` | array | List of successfully downloaded pack numbers |
| `failed_packs` | array | List of failed pack numbers |

### Managing Configuration

- **Location:** Same directory where you run the command
- **Editing:** Safe to edit manually (ensure valid JSON)
- **Reset:** Delete the file to start fresh
- **Backup:** Copy this file to preserve your download history

## Understanding the Output

When running the script, you'll see output similar to this:

```
Progress: 3/10 complete, 0 failed (30.0%) | Pack #1586: 65.2% at 15.4 MB/s, Pack #1587: 32.1% at 14.8 MB/s
```

This indicates:
- 3 out of 10 packs have been successfully downloaded
- 0 packs have failed to download
- 30% of the total download task is complete
- Pack #1586 is 65.2% downloaded at a speed of 15.4 MB/s
- Pack #1587 is 32.1% downloaded at a speed of 14.8 MB/s

A log file named `osu_downloader.log` will also be created in the same directory as the script, which contains detailed information about the download process.

## Troubleshooting

### Common Issues

#### "URL not found" for all URL patterns

This typically means the pack doesn't exist or has a different URL pattern. Check if the pack number is correct.

#### Slow Downloads

Try these solutions:
- Increase the number of threads (`--threads` option)
- Increase the chunk size (`--chunk-size` option)
- Disable delays between downloads (`--no-delay` option)

#### Downloads Keep Failing

Possible solutions:
- Check your internet connection
- Try with fewer threads (the server might be throttling)
- Enable resumable downloads (remove `--no-resume` if used)
- Check the log file for detailed error messages

#### "Permission denied" Errors

Make sure you have write permissions to the download directory.

### Reading Logs

The log file contains detailed information about each action the downloader takes. If you're having issues, check this file for clues. You can increase log verbosity with `--log-level DEBUG`.

## Development

### Setting Up for Development

```bash
# Clone repository
git clone https://github.com/yourusername/osu-beatmap-pack-downloader.git
cd osu-beatmap-pack-downloader

# Install with uv
uv sync

# Install in editable mode
uv pip install -e .

# Run from source
uv run osu-downloader --help
```

### Project Structure

```
osu-beatmap-pack-downloader/
├── src/
│   └── osu_beatmap_pack_downloader/
│       ├── __init__.py          # Package initialization
│       └── cli.py               # Main CLI application
├── .venv/                       # Virtual environment (auto-created)
├── pyproject.toml              # Project configuration & dependencies
├── uv.lock                     # Locked dependencies (commit this!)
├── README.md                   # This file
├── LICENSE                     # MIT License
└── osu_packs/                  # Default download location (created at runtime)
```

### Architecture Overview

The application consists of two main classes:

- **DownloadManager** - Handles multi-threaded downloads using a producer-consumer pattern with `ThreadPoolExecutor` and `queue.Queue`. Manages progress tracking, URL pattern detection, and resume capability.

- **ConfigManager** - Handles JSON persistence for tracking completed/failed downloads and user settings.

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## How It Works

The osu! Beatmap Pack Downloader works by:

1. **Parsing your command-line options** to determine which packs to download
2. **Creating a download queue** for all the requested packs
3. **Spawning worker threads** to process the download queue
4. **For each pack**:
   - Checking if it's already downloaded
   - Trying different URL patterns to find the correct one
   - Downloading the pack with progress tracking
   - Handling any errors that occur
5. **Saving configuration** to remember which packs were downloaded successfully

The downloader uses a `.part` file extension for files being downloaded. Once a download is complete, the file is renamed to its final name.

## FAQ

### Q: Is this tool official from osu!?

A: No, this is an unofficial tool created to help osu! players download beatmap packs more efficiently.

### Q: Will this get me banned from osu!?

A: The tool respects the server by adding delays between downloads and using proper headers. However, excessive downloading might be noticed by server administrators. Use responsibly.

### Q: Why does it download some packs but fail on others?

A: The URL patterns for packs can vary. The tool tries the most common patterns, but some packs might use a different pattern. Future versions might add support for more patterns.

### Q: Can I download all existing packs at once?

A: While technically possible, it's not recommended as it would put significant load on the server. Consider downloading in smaller batches.

### Q: Will this work on Mac/Linux?

A: Yes, the tool is compatible with any platform that supports Python 3.13+.

### Q: How can I see which packs I've already downloaded?

A: Check the `osu_downloader_config.json` file, which contains lists of completed and failed packs.

---

## Legal Notice

This tool is provided for educational purposes only. Please respect osu!'s terms of service and use this tool responsibly. Do not distribute downloaded content without permission.

## Credits

This tool was created to make downloading osu! beatmap packs more efficient for the community. osu! is the property of ppy Pty Ltd.

---

If you find this tool helpful, consider supporting osu! by becoming an [osu!supporter](https://osu.ppy.sh/home/support).