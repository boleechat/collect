#!/usr/bin/env python3
# coding=utf-8
# by boleechat - modified and combined version

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
        print("Btime initialized")
        return

    def getName(self):
        return "Btime"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # Base Configuration
    host = 'https://www.btime.com'
    base_url = 'https://www.btime.com/btv/btvws_yst'
    
    # Available years for content
    available_years = ['2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018']
    
    # Current year for default content
    current_year = '2025'
    
    # API URL templates - Using cursor-based pagination
    api_url_template = "https://pc.api.btime.com/btimeweb/infoFlow?list_id=btv_08da67cea600bf3c78973427bfaba12d_s0_{year}_{month:02d}&refresh=1&count=50&cursor={cursor}"
    
    # Headers for requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://www.btime.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # Cache for fetched data to reduce API calls
    data_cache = {}
    
    # Maximum number of requests per month
    max_requests_per_month = 10

    def homeContent(self, filter):
        """Generate content for home page with year-based categories"""
        result = {}
        
        # Create year-based categories
        classes = [{'type_name': year, 'type_id': year} for year in self.available_years]
        
        # No filters for now, could be expanded later
        filters = {}
        
        result['class'] = classes
        result['filters'] = filters
        return result
    
    def homeVideoContent(self):
        """Get videos for the home page (using the most recent year)"""
        # Use default year for home page
        videos = self.fetchVideosForYear(self.current_year, limit=30)
        
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for a specific year category"""
        if pg == '1':  # First page
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
        
        # Verify the tid is a valid year
        if tid not in self.available_years:
            tid = self.current_year
            
        # Fetch videos for the selected year
        all_videos = self.fetchVideosForYear(tid)
        
        # Implement pagination
        videos_per_page = 20
        start_idx = (self.currentPg - 1) * videos_per_page
        end_idx = start_idx + videos_per_page
        
        # Calculate total pages
        total_pages = max(1, (len(all_videos) + videos_per_page - 1) // videos_per_page)
        
        result = {
            'list': all_videos[start_idx:end_idx] if start_idx < len(all_videos) else [],
            'page': pg,
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
        
        # Parse the year and original ID from the video ID
        year, original_id = self.extract_year_and_id(vid)
        if not year:
            year = self.current_year
            original_id = vid
            
        # Find the specific video info in the year's data
        year_data = self.fetchDataForYear(year)
        
        video_info = None
        for item in year_data:
            if item.get('vod_id') == vid or (original_id and item.get('original_id') == original_id):
                video_info = item
                break
        
        if not video_info:
            return {'list': [{'vod_name': '未找到视频', 'vod_play_from': 'Btime', 'vod_play_url': '未找到$' + vid}]}
        
        # Extract details from video_info
        title = video_info.get('vod_name', f"视频 {vid}")
        url = video_info.get('vod_url', '')
        img_url = video_info.get('vod_pic', '')
        desc = video_info.get('vod_content', '')
        remarks = video_info.get('vod_remarks', f"{year}年视频")
        
        # Create play URL
        play_url = f"{title}${url}"
        
        vod = {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': img_url,
            'vod_year': year,
            'vod_area': '',
            'vod_remarks': remarks,
            'vod_actor': '',
            'vod_director': '',
            'vod_content': desc,
            'vod_play_from': 'Btime',
            'vod_play_url': play_url
        }
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword across all years"""
        results = []
        
        # Search in each year's data
        for year in self.available_years:
            year_data = self.fetchDataForYear(year)
            
            for item in year_data:
                # Check if the keyword is in the title
                title = item.get('vod_name', '')
                if key.lower() in title.lower():
                    # Avoid duplicates
                    if not any(r['vod_id'] == item['vod_id'] for r in results):
                        results.append(item)
        
        return {'list': results, 'page': pg, 'pagecount': 1, 'limit': 50, 'total': len(results)}
    
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
    def fetchDataForYear(self, year):
        """Fetch data for a specific year from API and cache it"""
        # Check if data is already in cache
        if year in self.data_cache:
            return self.data_cache[year]
        
        data = []
        # Track seen IDs to prevent duplicates
        seen_ids = set()
        
        # For current year, fetch only available months
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Determine how many months to fetch
        months_to_fetch = current_month if int(year) == current_year else 12
        
        for month in range(months_to_fetch, 0, -1):
            cursor = '0'  # Initial cursor
            request_count = 0
            
            while cursor is not None and request_count < self.max_requests_per_month:
                api_url = self.api_url_template.format(year=year, month=month, cursor=cursor)
                
                try:
                    response = self.session.get(api_url, headers=self.headers, timeout=10)
                    response.raise_for_status()
                    raw_text = response.text
                    
                    # Remove callback wrapper if present
                    if "(" in raw_text and ")" in raw_text:
                        raw_text = raw_text[raw_text.find("(") + 1 : raw_text.rfind(")")]
                    
                    json_data = json.loads(raw_text)
                    
                    # Get next cursor for pagination
                    next_cursor = json_data.get("data", {}).get("cursor", None)
                    
                    if "data" in json_data and "list" in json_data["data"]:
                        items = json_data["data"]["list"]
                        
                        # If no items returned or we're getting duplicates, we've hit the end
                        if not items:
                            break
                            
                        new_items_count = 0
                        for item in items:
                            gid = item.get("gid", "")
                            
                            # Skip if we've already seen this ID
                            if gid in seen_ids:
                                continue
                                
                            seen_ids.add(gid)
                            new_items_count += 1
                            
                            url = f"https://item.btime.com/{gid}" if gid else ""
                            title = item.get("data", {}).get("title", "无标题")
                            timestamp = int(item.get("data", {}).get("pdate", "0"))
                            
                            # Format date
                            if timestamp > 0:
                                beijing = timezone(timedelta(hours=8))
                                date_str = datetime.fromtimestamp(timestamp, beijing).strftime("%Y年%m月%d日")
                            else:
                                date_str = "未知时间"
                            
                            # Get cover image
                            cover = item.get("data", {}).get("covers", [""])[0]
                            
                            # Extract description if available
                            desc = item.get("data", {}).get("detail", "")
                            if not desc:
                                desc = item.get("data", {}).get("summary", "")
                            
                            # Create video object
                            video = {
                                'vod_id': f"{year}_{gid}",
                                'original_id': gid,
                                'vod_name': title,
                                'vod_pic': cover,
                                'vod_url': url,
                                'vod_content': desc,
                                'vod_remarks': date_str,
                                'vod_year': year
                            }
                            
                            data.append(video)
                        
                        # If we didn't get any new items, or we don't have a next cursor, stop fetching
                        if new_items_count == 0 or next_cursor is None or next_cursor == cursor:
                            break
                            
                        cursor = next_cursor
                    else:
                        # No data available
                        break
                
                except Exception as e:
                    print(f"Error fetching data for {year}-{month} cursor {cursor}: {e}")
                    break
                    
                request_count += 1
                
                # Add a short delay to avoid overwhelming the API
                time.sleep(0.5)
            
            print(f"Fetched {sum(1 for item in data if item['vod_year'] == year and f'月{month:02d}日' in item.get('vod_remarks', ''))} videos for {year}-{month:02d}")
        
        # Cache the results
        self.data_cache[year] = data
        print(f"Total: Fetched {len(data)} videos for year {year}")
        return data
    
    def fetchVideosForYear(self, year, limit=None):
        """Fetch videos for a specific year"""
        data = self.fetchDataForYear(year)
        
        if limit:
            return data[:limit]
        
        return data
    
    def extract_year_and_id(self, video_id):
        """Extract year and original ID from a combined video ID"""
        if '_' in video_id:
            parts = video_id.split('_', 1)
            if parts[0] in self.available_years:
                return parts[0], parts[1]
        return None, video_id
