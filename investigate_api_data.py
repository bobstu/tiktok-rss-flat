#!/usr/bin/env python3
import asyncio
import json
import os
from TikTokApi import TikTokApi
import config

# Get MS token
ms_token = os.environ.get("MS_TOKEN", None)

async def investigate_video_data():
    print("🔍 Investigating TikTok API data structure...")
    
    # Test with a user who likely has reposts
    test_users = ["maklelan", "aprilajoy", "aaron.higashi"]
    
    async with TikTokApi() as api:
        await api.create_sessions(num_sessions=1, sleep_after=10, headless=False)
        
        for username in test_users:
            print(f"\n{'='*60}")
            print(f"🔎 ANALYZING USER: {username}")
            print(f"{'='*60}")
            
            try:
                ttuser = api.user(username)
                user_data = await ttuser.info()
                
                print(f"\n📊 USER INFO:")
                print(f"  Display Name: {user_data.get('displayName', 'N/A')}")
                print(f"  Followers: {user_data.get('stats', {}).get('followerCount', 'N/A')}")
                print(f"  Total Videos: {user_data.get('stats', {}).get('videoCount', 'N/A')}")
                
                print(f"\n🎥 ANALYZING VIDEOS (First 5):")
                video_count = 0
                
                async for video in ttuser.videos(count=5):
                    video_count += 1
                    video_data = video.as_dict
                    
                    print(f"\n--- VIDEO #{video_count} ---")
                    print(f"Video ID: {video_data.get('id', 'N/A')}")
                    print(f"Description: {video_data.get('desc', 'N/A')[:100]}...")
                    print(f"Author ID: {video_data.get('author', {}).get('uniqueId', 'N/A')}")
                    print(f"Author Display: {video_data.get('author', {}).get('nickname', 'N/A')}")
                    
                    # Check for potential repost indicators
                    author_id = video_data.get('author', {}).get('uniqueId', '')
                    is_original = author_id.lower() == username.lower()
                    print(f"🔍 Is Original Content: {is_original}")
                    
                    if not is_original:
                        print(f"🔄 POTENTIAL REPOST DETECTED!")
                        print(f"   Original Author: {author_id}")
                        print(f"   Current Profile: {username}")
                    
                    # Look for specific repost fields
                    repost_fields = [
                        'isRepost', 'repost', 'share', 'shareInfo', 'duetInfo', 
                        'stitchInfo', 'forwardId', 'officalItem', 'originalItem'
                    ]
                    
                    print(f"\n🔍 CHECKING FOR REPOST FIELDS:")
                    found_repost_fields = {}
                    for field in repost_fields:
                        if field in video_data:
                            found_repost_fields[field] = video_data[field]
                            print(f"   ✅ Found '{field}': {video_data[field]}")
                    
                    if not found_repost_fields:
                        print(f"   ❌ No obvious repost fields found")
                    
                    # Check video stats
                    stats = video_data.get('stats', {})
                    print(f"\n📈 VIDEO STATS:")
                    print(f"   Views: {stats.get('playCount', 'N/A')}")
                    print(f"   Likes: {stats.get('diggCount', 'N/A')}")
                    print(f"   Shares: {stats.get('shareCount', 'N/A')}")
                    print(f"   Comments: {stats.get('commentCount', 'N/A')}")
                    
                    # Look for duet/stitch info (these might indicate reposts)
                    if 'duetInfo' in video_data:
                        print(f"🎭 DUET INFO: {video_data['duetInfo']}")
                    if 'stitchInfo' in video_data:
                        print(f"✂️ STITCH INFO: {video_data['stitchInfo']}")
                    
                    # Save full data for the first video of each user
                    if video_count == 1:
                        filename = f"/tmp/video_data_{username}.json"
                        with open(filename, 'w') as f:
                            json.dump(video_data, f, indent=2, default=str)
                        print(f"💾 Full video data saved to: {filename}")
                
                print(f"\n✅ Completed analysis for {username}")
                
            except Exception as e:
                print(f"❌ Error analyzing {username}: {e}")

        print(f"\n{'='*60}")
        print(f"🏁 INVESTIGATION COMPLETE")
        print(f"{'='*60}")
        print(f"Check /tmp/video_data_*.json files for detailed data structure")

if __name__ == "__main__":
    asyncio.run(investigate_video_data())
