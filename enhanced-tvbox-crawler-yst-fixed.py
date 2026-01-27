#!/usr/bin/env python3
# coding=utf-8
# Enhanced Btime TVBox Crawler - Auto-fetching version

import json
import sys
import re
import time
from urllib.parse import urljoin, quote, urlparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        print("Btime initialized - Auto-fetch mode")
        return

    def getName(self):
        return "Btime养生堂"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # Base Configuration
    host = 'https://www.btime.com'
    base_url = 'https://www.btime.com/btv/btvws_yst'
    
    # API URL template - cursor-based pagination
    api_url_template = "https://pc.api.btime.com/btimeweb/infoFlow?list_id=btv_08da67cea600bf3c78973427bfaba12d_s0_{year}_{month:02d}&refresh=1&count=50&cursor={cursor}"
    
    # Headers for requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'https://www.btime.com/',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    # Cache for fetched data
    all_videos_cache = None
    cache_timestamp = None
    cache_expiry = 1800  # 30 minutes
    
    # Fetch configuration
    max_videos_per_request = 50
    max_total_videos = 500  # Limit total videos to avoid excessive loading

    def homeContent(self, filter):
        """Generate content for home page with time-based categories"""
        result = {}
        
        # Create categories: Latest (最新), This Month (本月), Last 3 Months (近3月), Last 6 Months (近6月), All (全部)
        classes = [
            {'type_name': '最新', 'type_id': 'latest'},
            {'type_name': '本月', 'type_id': 'thismonth'},
            {'type_name': '近3月', 'type_id': 'recent3'},
            {'type_name': '近6月', 'type_id': 'recent6'},
            {'type_name': '全部', 'type_id': 'all'}
        ]
        
        result['class'] = classes
        result['filters'] = {}
        return result
    
    def homeVideoContent(self):
        """Get videos for the home page (latest videos)"""
        videos = self.fetchLatestVideos(limit=30)
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for a specific category"""
        page = int(pg) if pg else 1
        videos_per_page = 20
        
        # Get videos based on category
        if tid == 'latest':
            all_videos = self.fetchLatestVideos(limit=100)
        elif tid == 'thismonth':
            all_videos = self.fetchVideosForPeriod(months=1)
        elif tid == 'recent3':
            all_videos = self.fetchVideosForPeriod(months=3)
        elif tid == 'recent6':
            all_videos = self.fetchVideosForPeriod(months=6)
        elif tid == 'all':
            all_videos = self.fetchAllAvailableVideos()
        else:
            all_videos = self.fetchLatestVideos(limit=100)
        
        # Implement pagination
        start_idx = (page - 1) * videos_per_page
        end_idx = start_idx + videos_per_page
        
        # Calculate total pages
        total_pages = max(1, (len(all_videos) + videos_per_page - 1) // videos_per_page)
        
        result = {
            'list': all_videos[start_idx:end_idx] if start_idx < len(all_videos) else [],
            'page': page,
            'pagecount': total_pages,
            'limit': videos_per_page,
            'total': len(all_videos)
        }
        
        return result
    
    def detailContent(self, ids):
        """Get details for a specific video"""
        if not ids:
            return {'list': []}
        
        vid = ids[0]
        
        # Find video in cached data
        all_videos = self.getCachedAllVideos()
        video_info = None
        
        for item in all_videos:
            if item.get('vod_id') == vid:
                video_info = item
                break
        
        if not video_info:
            return {'list': [{'vod_name': '未找到视频', 'vod_play_from': 'Btime', 'vod_play_url': '未找到$' + vid}]}
        
        # Create play URL
        play_url = f"{video_info['vod_name']}${video_info['vod_url']}"
        
        vod = {
            'vod_id': vid,
            'vod_name': video_info['vod_name'],
            'vod_pic': video_info['vod_pic'],
            'vod_year': video_info.get('vod_year', ''),
            'vod_area': '养生',
            'vod_remarks': video_info.get('vod_remarks', ''),
            'vod_actor': '',
            'vod_director': '',
            'vod_content': video_info.get('vod_content', ''),
            'vod_play_from': 'Btime',
            'vod_play_url': play_url
        }
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword"""
        results = []
        
        # Search in all cached videos
        all_videos = self.getCachedAllVideos()
        
        for item in all_videos:
            title = item.get('vod_name', '')
            if key.lower() in title.lower():
                results.append(item)
        
        return {
            'list': results[:50],  # Limit to 50 results
            'page': pg,
            'pagecount': 1,
            'limit': 50,
            'total': len(results)
        }
    
    def playerContent(self, flag, id, vipFlags):
        """Get playback information"""
        # If ID looks like a full URL, use it directly
        if id.startswith(('http://', 'https://')):
            return {'parse': 1, 'url': id, 'header': self.headers}
        
        # Otherwise, treat as a relative path and construct full URL
        if not id.startswith('/'):
            id = '/' + id
            
        full_url = f"{self.host}{id}"
        
        return {'parse': 1, 'url': full_url, 'header': self.headers}
    
    def localProxy(self, param):
        return param
    
    # Helper methods
    
    def getCachedAllVideos(self):
        """Get or refresh cached all videos"""
        now = time.time()
        
        # Check if cache is still valid
        if (self.all_videos_cache is not None and 
            self.cache_timestamp is not None and 
            (now - self.cache_timestamp) < self.cache_expiry):
            return self.all_videos_cache
        
        # Refresh cache
        print("Refreshing video cache...")
        self.all_videos_cache = self.fetchAllAvailableVideos()
        self.cache_timestamp = now
        
        return self.all_videos_cache
    
    def fetchLatestVideos(self, limit=50):
        """Fetch the most recent videos"""
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        videos = []
        seen_ids = set()
        
        # Start from current month and go backwards
        months_checked = 0
        year = current_year
        month = current_month
        
        while len(videos) < limit and months_checked < 6:  # Check up to 6 months
            fetched = self.fetchVideosForMonth(year, month, seen_ids, limit - len(videos))
            videos.extend(fetched)
            
            # Move to previous month
            month -= 1
            if month < 1:
                month = 12
                year -= 1
            
            months_checked += 1
        
        return videos
    
    def fetchVideosForPeriod(self, months=3):
        """Fetch videos for a specific period (in months)"""
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        videos = []
        seen_ids = set()
        
        year = current_year
        month = current_month
        
        for _ in range(months):
            fetched = self.fetchVideosForMonth(year, month, seen_ids)
            videos.extend(fetched)
            
            # Move to previous month
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        
        return videos
    
    def fetchAllAvailableVideos(self):
        """Fetch all available videos (with reasonable limits)"""
        videos = []
        seen_ids = set()
        
        # Start from current date
        now = datetime.now()
        year = now.year
        month = now.month
        
        # Go back up to 24 months or until we hit the limit
        months_checked = 0
        max_months = 24
        
        while len(videos) < self.max_total_videos and months_checked < max_months:
            print(f"Fetching videos for {year}-{month:02d}...")
            fetched = self.fetchVideosForMonth(year, month, seen_ids)
            
            if not fetched:
                # If no videos found, we might have gone back too far
                months_checked += 1
                if months_checked >= 3:  # If 3 consecutive months have no data, stop
                    break
            else:
                months_checked = 0  # Reset counter when we find videos
                videos.extend(fetched)
            
            # Move to previous month
            month -= 1
            if month < 1:
                month = 12
                year -= 1
                
                # Don't go before 2018
                if year < 2018:
                    break
        
        print(f"Total videos fetched: {len(videos)}")
        return videos
    
    def fetchVideosForMonth(self, year, month, seen_ids=None, limit=None):
        """Fetch videos for a specific month"""
        if seen_ids is None:
            seen_ids = set()
        
        videos = []
        cursor = '0'
        request_count = 0
        max_requests = 5  # Limit requests per month
        
        while request_count < max_requests:
            if limit and len(videos) >= limit:
                break
            
            api_url = self.api_url_template.format(year=year, month=month, cursor=cursor)
            
            try:
                response = self.session.get(api_url, headers=self.headers, timeout=10)
                
                # Check if request was successful
                if response.status_code != 200:
                    print(f"Error: Status code {response.status_code} for {year}-{month:02d}")
                    break
                
                raw_text = response.text
                
                # Handle empty response
                if not raw_text or raw_text.strip() == '':
                    break
                
                # Remove callback wrapper if present
                if "(" in raw_text and ")" in raw_text:
                    raw_text = raw_text[raw_text.find("(") + 1 : raw_text.rfind(")")]
                
                # Parse JSON
                try:
                    json_data = json.loads(raw_text)
                except json.JSONDecodeError:
                    print(f"JSON decode error for {year}-{month:02d}")
                    break
                
                # Check if data exists
                if "data" not in json_data or "list" not in json_data.get("data", {}):
                    break
                
                items = json_data["data"]["list"]
                
                # If no items returned, we've reached the end
                if not items:
                    break
                
                new_items_count = 0
                for item in items:
                    if limit and len(videos) >= limit:
                        break
                    
                    gid = item.get("gid", "")
                    
                    # Skip if already seen
                    if gid in seen_ids:
                        continue
                    
                    seen_ids.add(gid)
                    new_items_count += 1
                    
                    # Extract video information
                    data_section = item.get("data", {})
                    url = f"https://item.btime.com/{gid}" if gid else ""
                    title = data_section.get("title", "无标题")
                    timestamp = int(data_section.get("pdate", "0"))
                    
                    # Format date
                    if timestamp > 0:
                        beijing = timezone(timedelta(hours=8))
                        dt = datetime.fromtimestamp(timestamp, beijing)
                        date_str = dt.strftime("%Y年%m月%d日")
                    else:
                        date_str = "未知时间"
                    
                    # Get cover image
                    covers = data_section.get("covers", [])
                    cover = covers[0] if covers else ""
                    
                    # Extract description
                    desc = data_section.get("detail", "")
                    if not desc:
                        desc = data_section.get("summary", "")
                    
                    # Create video object
                    video = {
                        'vod_id': gid,
                        'vod_name': title,
                        'vod_pic': cover,
                        'vod_url': url,
                        'vod_content': desc,
                        'vod_remarks': date_str,
                        'vod_year': str(year)
                    }
                    
                    videos.append(video)
                
                # Check if we should continue
                if new_items_count == 0:
                    break
                
                # Get next cursor
                next_cursor = json_data.get("data", {}).get("cursor", None)
                if next_cursor is None or next_cursor == cursor or next_cursor == '0':
                    break
                
                cursor = next_cursor
                
            except Exception as e:
                print(f"Error fetching {year}-{month:02d} cursor {cursor}: {str(e)}")
                break
            
            request_count += 1
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.3)
        
        return videos
