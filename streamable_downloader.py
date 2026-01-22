#!/usr/bin/env python3
"""
Streamable Video Downloader
Downloads all videos from your Streamable account in highest quality.
Preserves original video titles as filenames.
"""

import argparse
import re
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Requests not installed. Run: pip install requests")
    sys.exit(1)


def sanitize_filename(name: str) -> str:
    """Remove invalid characters from filename."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip('. ')
    return name[:200] if name else "untitled"


def get_best_quality_url(files: dict) -> tuple[str, str]:
    """Get the highest quality video URL from files dict."""
    priority = ['original', 'mp4', 'mp4-mobile']
    
    for quality in priority:
        if quality in files and files[quality].get('url'):
            url = files[quality]['url']
            if url.startswith('//'):
                url = 'https:' + url
            return url, quality
    
    return None, None


def download_video(url: str, filepath: Path, session: requests.Session) -> bool:
    """Download video file with progress indication."""
    try:
        response = session.get(url, stream=True, timeout=120)
        response.raise_for_status()
        
        total = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = (downloaded / total) * 100
                    print(f"\r  Progress: {pct:.1f}%", end='', flush=True)
        
        print()
        return True
    except Exception as e:
        print(f"\n  Error downloading: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Download all videos from your Streamable account',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --email user@example.com --password mypassword
  %(prog)s --email user@example.com --password mypassword -o ~/Videos/Streamable
  %(prog)s --email user@example.com --password mypassword --no-headless
        '''
    )
    parser.add_argument('--email', '-e', required=True, help='Streamable email or username')
    parser.add_argument('--password', '-p', required=True, help='Streamable password')
    parser.add_argument('--output', '-o', default='./streamable_videos', help='Output directory (default: ./streamable_videos)')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser headless (default)')
    parser.add_argument('--no-headless', dest='headless', action='store_false', help='Show browser window (useful for debugging)')
    args = parser.parse_args()

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()

        print("Logging in to Streamable...")
        page.goto('https://streamable.com/login')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Dismiss cookie banner if present
        try:
            cookie_btn = page.locator('button:has-text("Accept all cookies"), button:has-text("Continue without accepting")')
            if cookie_btn.count() > 0:
                cookie_btn.first.click()
                time.sleep(1)
        except:
            pass
        
        page.fill('input[placeholder*="Email" i], input[placeholder*="username" i]', args.email)
        page.fill('input[type="password"]', args.password)
        page.click('button[type="submit"]:has-text("Log In")')
        
        try:
            page.wait_for_url('**/videos**', timeout=15000)
            print("Login successful!")
        except:
            print("Login may have failed or redirect is different. Checking...")
            if 'login' in page.url.lower():
                print("ERROR: Login failed. Check credentials.")
                browser.close()
                sys.exit(1)

        print("Fetching video list via API...")
        
        # Use the internal API to get all videos with pagination
        video_links = []
        page_num = 1
        per_page = 50
        
        while True:
            api_url = f"https://api-f.streamable.com/api/v1/videos?sort=date_added&sortd=DESC&count={per_page}&page={page_num}"
            response = page.evaluate(f'''async () => {{
                const resp = await fetch("{api_url}", {{ credentials: "include" }});
                return await resp.json();
            }}''')
            
            if not response or 'videos' not in response:
                print(f"  API error or no videos on page {page_num}")
                break
            
            videos_on_page = response.get('videos', [])
            if not videos_on_page:
                break
            
            for v in videos_on_page:
                video_links.append({
                    'shortcode': v.get('shortcode'),
                    'title': v.get('title', '')
                })
            
            print(f"\r  Fetched {len(video_links)} videos...", end='', flush=True)
            
            total = response.get('total', 0)
            if len(video_links) >= total:
                break
            
            page_num += 1
            time.sleep(0.5)
        
        print()

        cookies = context.cookies()
        browser.close()

    if not video_links:
        print("No videos found. The page structure may have changed.")
        sys.exit(1)

    print(f"Found {len(video_links)} videos. Fetching metadata and downloading...")
    
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    downloaded = 0
    skipped = 0
    failed = 0
    
    for i, video in enumerate(video_links, 1):
        shortcode = video['shortcode']
        print(f"\n[{i}/{len(video_links)}] Processing: {shortcode}")
        
        try:
            api_url = f"https://api.streamable.com/videos/{shortcode}"
            resp = session.get(api_url, timeout=30)
            
            if resp.status_code != 200:
                print(f"  Failed to fetch metadata (status {resp.status_code})")
                failed += 1
                continue
            
            data = resp.json()
            title = data.get('title') or video.get('title') or shortcode
            title = sanitize_filename(title)
            
            files = data.get('files', {})
            if not files:
                print(f"  No video files available")
                failed += 1
                continue
            
            url, quality = get_best_quality_url(files)
            if not url:
                print(f"  No downloadable URL found")
                failed += 1
                continue
            
            file_info = files.get(quality, {})
            width = file_info.get('width', 'unknown')
            height = file_info.get('height', 'unknown')
            
            filename = f"{title}_{shortcode}.mp4"
            filepath = output_dir / filename
            
            if filepath.exists():
                print(f"  Already exists: {filename}")
                skipped += 1
                continue
            
            print(f"  Title: {title}")
            print(f"  Quality: {quality} ({width}x{height})")
            print(f"  Downloading...")
            
            if download_video(url, filepath, session):
                downloaded += 1
                print(f"  Saved: {filename}")
            else:
                failed += 1

        except Exception as e:
            print(f"  Error: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Download complete!")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Output directory: {output_dir}")


if __name__ == '__main__':
    main()
