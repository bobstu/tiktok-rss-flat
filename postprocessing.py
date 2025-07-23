import os
import asyncio
import csv
import time
from datetime import datetime, timezone, timedelta
from feedgen.feed import FeedGenerator
#from tiktokapipy.api import TikTokAPI
from TikTokApi import TikTokApi
import config
from playwright.async_api import async_playwright, Playwright
from pathlib import Path
from urllib.parse import urlparse

# Add browser context options to simulate real browser
context_options = {
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'viewport': {'width': 1920, 'height': 1080}
}

# Edit config.py to change your URLs
ghRawURL = config.ghRawURL
api = TikTokApi()
ms_token = os.environ.get("MS_TOKEN", None)

async def runscreenshot(playwright: Playwright, url, screenshotpath):
    chromium = playwright.chromium # or "firefox" or "webkit".
    browser = await chromium.launch()
    page = await browser.new_page()
    await page.goto(url)
    # Save the screenshot
    await page.screenshot(path=screenshotpath, quality = 20, type = 'jpeg')
    await browser.close()

async def user_videos():
    with open('subscriptions.csv') as f:
        cf = csv.DictReader(f, fieldnames=['username'])
        for row in cf:
            user = row['username']
            print(f'Running for user \'{user}\'')
            fg = FeedGenerator()
            fg.id('https://www.tiktok.com/@' + user)
            fg.title(user + ' TikTok')
            fg.author( {'name':'Conor ONeill','email':'conor@conoroneill.com'} )
            fg.link( href='http://tiktok.com', rel='alternate' )
            fg.logo(ghRawURL + 'tiktok-rss.png')
            fg.subtitle('OK Boomer, all the latest TikToks from ' + user)
            fg.link( href=ghRawURL + 'rss/' + user + '.xml', rel='self' )
            fg.language('en')
            # Set the last modification time for the feed to be the most recent post, else now.
            updated=None
            
            async with TikTokApi() as api:
                await api.create_sessions(num_sessions=1, sleep_after=10, headless=False)
                try:
                    # Get the user object from the API
                    ttuser = api.user(user)
                    user_data = await ttuser.info()
                    #print(user_data)
                    
                    # COLLECT ALL VIDEOS FIRST
                    videos = []
                    async for video in ttuser.videos(count=20):  # Get more videos to ensure we have recent ones
                        videos.append(video)
                    
                    # SORT BY CREATION TIME (NEWEST FIRST)
                    videos.sort(key=lambda x: x.as_dict['createTime'], reverse=True)
                    
                    # FILTER TO ONLY RECENT VIDEOS (last 60 days)
                    cutoff_date = datetime.now() - timedelta(days=60)
                    recent_videos = []
                    
                    for video in videos:
                        video_date = datetime.fromtimestamp(video.as_dict['createTime'])
                        if video_date > cutoff_date:
                            recent_videos.append(video)
                        if len(recent_videos) >= 10:  # Limit to 10 most recent videos
                            break
                    
                    print(f"Found {len(recent_videos)} recent videos for {user}")
                    
                    # PROCESS THE SORTED, RECENT VIDEOS
                    for video in reversed(recent_videos):  #added reversed order
                        fe = fg.add_entry()
                        link = "https://tiktok.com/@" + user + "/video/" + video.id
                        fe.id(link)
                        ts = datetime.fromtimestamp(video.as_dict['createTime'], timezone.utc)
                        fe.published(ts)
                        fe.updated(ts)
                        updated = max(ts, updated) if updated else ts
                        
                        # Debug: Print video date to verify sorting
                        print(f"Processing video from {ts.strftime('%Y-%m-%d %H:%M:%S')}: {video.as_dict.get('desc', 'No title')[:50]}...")
                        
                        if video.as_dict['desc']:
                            fe.title(video.as_dict['desc'][0:255])
                        else:
                            fe.title("No Title")
                        fe.link(href=link)
                        if video.as_dict['desc']:
                            content = video.as_dict['desc'][0:255]
                        else:
                            content = "No Description"
                        if video.as_dict['video']['cover']:
                            videourl = video.as_dict['video']['cover']
                            parsed_url = urlparse(videourl)
                            path_segments = parsed_url.path.split('/')
                            last_segment = [seg for seg in path_segments if seg][-1]
                            screenshotsubpath = "thumbnails/" + user + "/screenshot_" + last_segment + ".jpg"
                            screenshotpath = os.path.dirname(os.path.realpath(__file__)) + "/" + screenshotsubpath
                            if not os.path.isfile(screenshotpath):
                                async with async_playwright() as playwright:
                                    await runscreenshot(playwright, videourl, screenshotpath)
                            screenshoturl =  ghRawURL + screenshotsubpath
                            content = '<img src="' + screenshoturl + '" / > ' + content    
                        fe.content(content)
                    
                    fg.updated(updated)
                    fg.rss_file('rss/' + user + '.xml', pretty=True) # Write the RSS feed to a file
                    print(f"RSS feed updated for {user} with {len(recent_videos)} videos")
                        
                except Exception as e:
                    print(f"Error processing {user}: {e}")

# Add repost detection to your existing postprocessing.py
async def analyze_video_type(video, username):
    video_data = video.as_dict
    
    # Check for explicit repost indicators
    if any(field in video_data for field in ['isRepost', 'repost', 'shareInfo']):
        return 'repost'
    
    # Check for duet/stitch
    if 'duetInfo' in video_data:
        return 'duet'
    if 'stitchInfo' in video_data:
        return 'stitch'
    
    # Check if different author
    video_author = video_data.get('author', {}).get('uniqueId', '').lower()
    if video_author != username.lower() and video_author:
        return 'cross_post'
    
    return 'original'


if __name__ == "__main__":
    asyncio.run(user_videos())
