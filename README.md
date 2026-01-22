# Streamable Downloader

Download all videos from your Streamable account in the highest quality available, with original titles preserved.

> **AI Disclosure:** This project was created with the assistance of [Amp](https://ampcode.com), an AI coding agent.

## Features

- **Bulk download** - Downloads all videos from your account automatically
- **Highest quality** - Prioritizes original quality, then mp4, then mp4-mobile
- **Preserves titles** - Files are named using the original video title
- **Resume support** - Skips already downloaded files
- **Progress indication** - Shows download progress for each video

## Requirements

- Python 3.10+
- Chromium browser (installed automatically by Playwright)

## Installation

```bash
# Clone the repository
git clone https://github.com/wuirm/streamable-downloader.git
cd streamable-downloader

# Install dependencies
pip install playwright requests

# Install Chromium browser
playwright install chromium
```

## Usage

```bash
python streamable_downloader.py --email YOUR_EMAIL --password YOUR_PASSWORD
```

### Options

| Option | Description |
|--------|-------------|
| `--email`, `-e` | Streamable email or username (required) |
| `--password`, `-p` | Streamable password (required) |
| `--output`, `-o` | Output directory (default: `./streamable_videos`) |
| `--no-headless` | Show browser window (useful for debugging login issues) |

### Examples

```bash
# Basic usage
python streamable_downloader.py -e user@example.com -p mypassword

# Specify output directory
python streamable_downloader.py -e user@example.com -p mypassword -o ~/Videos/Streamable

# Debug mode (show browser)
python streamable_downloader.py -e user@example.com -p mypassword --no-headless
```

## Output

Videos are saved as `{title}_{shortcode}.mp4` in the output directory. The shortcode is included to ensure unique filenames.

Example:
```
streamable_videos/
├── My Cool Video_abc123.mp4
├── Another Clip_xyz789.mp4
└── Gaming Moment_def456.mp4
```

## How It Works

1. Logs into your Streamable account using Playwright (headless browser)
2. Fetches the complete list of videos via Streamable's internal API
3. Downloads each video using the public API to get signed URLs
4. Saves videos with their original titles

## Troubleshooting

### Login fails
- Double-check your email and password
- Try running with `--no-headless` to see what's happening
- Make sure you don't have 2FA enabled (not supported)

### Some videos fail to download
- Videos may have been deleted or expired
- The video may still be processing on Streamable's servers

### Browser errors
- Run `playwright install chromium` to reinstall the browser
- Make sure you have sufficient disk space

## License

MIT License - See [LICENSE](LICENSE) for details.

## Disclaimer

This tool is for downloading your own content from Streamable. Please respect copyright and only download videos you have the right to download.


