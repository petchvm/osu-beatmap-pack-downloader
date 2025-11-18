# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**osu-beatmap-pack-downloader** is a Python CLI tool for downloading osu! beatmap packs from packs.ppy.sh. It uses multi-threaded downloads with intelligent URL pattern detection, resume capability, and comprehensive progress tracking.

## Entry Point

The main application is located at `src/osu_beatmap_pack_downloader/cli.py`. Users invoke it via the CLI command `osu-downloader` (defined in `pyproject.toml` under `[project.scripts]`).

**To run the application:**
```bash
uv run osu-downloader --start 1580 --end 1590
```

## Architecture

### Core Classes

**DownloadManager** (`cli.py:35-372`)
- Orchestrates multi-threaded downloads using `ThreadPoolExecutor` and `queue.Queue`
- Implements producer-consumer pattern: main thread populates queue, worker threads consume
- Each worker gets its own `requests.Session` with:
  - HTTP retry logic (3 attempts with exponential backoff)
  - Connection pooling via `HTTPAdapter`
  - Browser-like headers to avoid detection
- **Key methods:**
  - `download_pack()` - Main download logic with URL pattern fallback
  - `_download_worker()` - Worker thread function
  - `_progress_reporter()` - Dedicated daemon thread for non-blocking progress updates

**ConfigManager** (`cli.py:375-425`)
- Handles JSON persistence in `osu_downloader_config.json`
- Tracks `completed_packs` and `failed_packs` arrays
- Persists user settings (threads, chunk_size, download_dir, etc.)

### Threading Model

- **Main thread:** Populates download queue
- **Worker threads (default: 3):** Process queue items concurrently
- **Progress reporter thread:** Daemon thread that updates console every second

Pattern: Producer-consumer with thread-safe `queue.Queue()`

### URL Pattern Detection

For each pack, the downloader tries 3 URL patterns in order:
1. `https://packs.ppy.sh/S{num}%20-%20osu%21%20Beatmap%20Pack%20%23{num}.zip`
2. `https://packs.ppy.sh/S{num}%20-%20Beatmap%20Pack%20%23{num}.zip`
3. `https://packs.ppy.sh/S{num}%20-%20Beatmap%20Pack%20%23{num}.7z`

Returns 404 handling: Moves to next pattern, marks as failed if all patterns fail.

### Resume Capability

- Downloads use `.part` extension for incomplete files
- HTTP Range headers request missing bytes: `Range: bytes={existing_size}-`
- On completion, `.part` file is atomically renamed to final name
- Controlled via `--no-resume` flag

### Progress Tracking

- Non-blocking: Separate daemon thread prevents I/O blocking
- Updates every 1 second
- Uses ANSI escape codes (`\033[K`) for clean terminal updates
- Displays: overall progress percentage, per-pack progress, download speeds

## Dependencies

**Runtime (declared in pyproject.toml):**
- `requests>=2.31.0` - HTTP client for downloads
- `urllib3>=2.0.0` - Retry logic utilities

**No development dependencies currently defined.**

## Common Commands

### Development Setup
```bash
# Clone and install
git clone <repo-url>
cd osu-beatmap-pack-downloader
uv sync                    # Create venv, install deps, create lockfile

# Install in editable mode
uv pip install -e .

# Run from source
uv run osu-downloader --help
```

### Running the Application
```bash
# Basic usage
uv run osu-downloader --start 1580 --end 1590

# With custom settings
uv run osu-downloader --start 1580 --end 1590 --threads 5 --chunk-size 16384

# Retry failed downloads
uv run osu-downloader --retry-failed

# Debug mode
uv run osu-downloader --start 1580 --end 1590 --log-level DEBUG
```

### Package Management
```bash
# Add new dependency
uv add <package-name>

# Update dependencies
uv sync

# View dependency tree
uv pip list
```

## State Management

**Configuration File:** `osu_downloader_config.json`
```json
{
  "download_dir": "./osu_packs",
  "threads": 3,
  "chunk_size": 8192,
  "delay": true,
  "completed_packs": [1589, 1590],
  "failed_packs": []
}
```

**Runtime Files (gitignored):**
- `osu_downloader_config.json` - Persistent state
- `osu_downloader.log` - Detailed logs
- `osu_packs/` - Default download directory
- `*.part` - Partial downloads

## Key Patterns and Conventions

### Session Pooling
Each worker thread creates its own `requests.Session` with retry configuration:
```python
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)
```

### Error Handling
- Network errors: Caught per-pack, logged, marked in `failed_packs`
- 404 responses: Try next URL pattern
- Partial downloads: Resume via HTTP Range headers
- Config errors: Gracefully handle missing/corrupt JSON

### Logging Strategy
- Dual output: Console (INFO level) + file (all levels)
- Structured format: `%(asctime)s - %(levelname)s - %(message)s`
- File location: Same directory as execution
- Configurable via `--log-level` flag

### Bandwidth Limiting
Optional per-thread bandwidth limit using `time.sleep()` calculations:
```python
if bandwidth_limit:
    elapsed = time.time() - chunk_start
    expected = chunk_size / (bandwidth_limit * 1024 * 1024)
    if elapsed < expected:
        time.sleep(expected - elapsed)
```

## Project Structure

```
osu-beatmap-pack-downloader/
├── src/
│   └── osu_beatmap_pack_downloader/
│       ├── __init__.py          # Package version and metadata
│       └── cli.py               # Main application (511 lines)
├── pyproject.toml              # uv-managed dependencies, CLI entry point
├── uv.lock                     # Locked dependency versions (COMMIT THIS)
├── README.md                   # User documentation
├── LICENSE                     # MIT License
└── .gitignore                  # Ignores .venv, runtime files, etc.
```

## Important Notes

- **Python Version:** Requires 3.13+ (specified in `pyproject.toml`)
- **uv.lock:** This is an application, not a library - commit the lockfile for reproducibility
- **Entry Point:** Users should use `osu-downloader` command, not `python cli.py`
- **Delays:** Random 0.5-1.5s delays between downloads respect server load (can disable with `--no-delay`)
- **No Tests:** No test suite currently exists

## Making Changes

### Adding a New Feature
1. Modify `src/osu_beatmap_pack_downloader/cli.py`
2. Update README.md with new usage examples
3. Test with `uv run osu-downloader`
4. Update this CLAUDE.md if architecture changes

### Adding Dependencies
```bash
uv add <package-name>           # Automatically updates pyproject.toml and uv.lock
git add pyproject.toml uv.lock  # Commit both files
```

### Modifying CLI Arguments
CLI uses `argparse` - modify the argument parser in `cli.py:main()` function. Remember to update README.md command-line options table.

## Debugging Tips

- **Enable debug logging:** `--log-level DEBUG` provides detailed per-operation logs
- **Check config file:** `osu_downloader_config.json` shows completed/failed state
- **Inspect .part files:** Indicates interrupted downloads
- **Monitor log file:** `osu_downloader.log` has full operation history
- **Test single pack:** Use `--packs <num>` to test with one pack instead of ranges
