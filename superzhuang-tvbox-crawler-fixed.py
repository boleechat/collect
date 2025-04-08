#!/usr/bin/env python3
# coding=utf-8
# SuperZhuang TVBox crawler - Fixed version

import json
import sys
import re
import time
from urllib.parse import urljoin, quote, urlparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import base64

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update(self.mobile_headers)
        print("SuperZhuang initialized with mobile user agent")
        return

    def getName(self):
        return "SuperZhuang"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # Base Configuration
    host = 'https://m.superzhuang.com'
    base_url = 'https://m.superzhuang.com/programme'
    api_url = 'https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails'
    
    # API URL for fetching all video content
    content_list_api = 'https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails?contentId=1217840147335688192'
    
    # Mobile Headers for requests - Simulating iPhone browser
    mobile_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.superzhuang.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Origin': 'https://m.superzhuang.com',
        'Connection': 'keep-alive'
    }
    
    # PC Headers for some requests
    pc_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://www.superzhuang.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Origin': 'https://www.superzhuang.com',
        'Connection': 'keep-alive'
    }
    
    # Cache for fetched data to reduce API calls
    data_cache = {}
    
    # Debug flag
    debug = True

    def homeContent(self, filter):
        """Generate content for home page"""
        result = {}
        
        # Debug log
        if self.debug:
            print("Fetching home content")
        
        # Simple categories by content type
        classes = [
            {'type_name': '全部视频', 'type_id': 'all'},
            {'type_name': '家居装修', 'type_id': 'home'},
            {'type_name': '设计案例', 'type_id': 'design'}
        ]
        
        # No filters for now
        filters = {}
        
        result['class'] = classes
        result['filters'] = filters
        return result
    
    def homeVideoContent(self):
        """Get videos for the home page"""
        # Debug log
        if self.debug:
            print("Fetching home video content")
        
        videos = self.fetchAllVideos(limit=30)
        
        # Debug log
        if self.debug:
            print(f"Home videos fetched: {len(videos)}")
            if videos:
                print(f"First video: {videos[0]['vod_name']}")
        
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for a specific category"""
        if pg == '1':  # First page
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
        
        # Debug log
        if self.debug:
            print(f"Fetching category content for {tid}, page {pg}")
        
        # Fetch all videos
        all_videos = self.fetchAllVideos()
        
        # Filter by category if needed (placeholder for now)
        filtered_videos = all_videos
        
        # Implement pagination
        videos_per_page = 20
        start_idx = (self.currentPg - 1) * videos_per_page
        end_idx = start_idx + videos_per_page
        
        # Calculate total pages
        total_pages = max(1, (len(filtered_videos) + videos_per_page - 1) // videos_per_page)
        
        # Get videos for current page
        current_page_videos = filtered_videos[start_idx:end_idx] if start_idx < len(filtered_videos) else []
        
        # Debug log
        if self.debug:
            print(f"Category videos fetched: {len(current_page_videos)} of {len(filtered_videos)} total")
        
        result = {
            'list': current_page_videos,
            'page': pg,
            'pagecount': total_pages,
            'limit': videos_per_page,
            'total': len(filtered_videos)
        }
        
        return result
    
    def detailContent(self, ids):
        """Get details for a specific video"""
        if not ids:
            return {'list': []}
        
        content_id = ids[0]
        
        # Debug log
        if self.debug:
            print(f"Fetching detail content for ID: {content_id}")
        
        # First, check our cache of videos
        all_videos = self.fetchAllVideos()
        
        video_info = None
        for item in all_videos:
            if item.get('vod_id') == content_id:
                video_info = item
                break
        
        # If not found in cache, try to fetch directly
        if not video_info:
            # Fetch detailed info for this content
            detail_info = self.fetchVideoDetail(content_id)
            
            if detail_info:
                title = detail_info.get('contentTitle', f"视频 {content_id}")
                cover_img = detail_info.get('firstImg', '')
                desc = detail_info.get('contentDesc', '')
                
                # Create video object
                video_info = {
                    'vod_id': content_id,
                    'vod_name': title,
                    'vod_pic': cover_img,
                    'vod_url': content_id,
                    'vod_content': desc,
                    'vod_remarks': ''
                }
        
        if not video_info:
            # Debug log
            if self.debug:
                print(f"Video not found for ID: {content_id}")
            return {'list': [{'vod_name': '未找到视频', 'vod_play_from': 'SuperZhuang', 'vod_play_url': '未找到$' + content_id}]}
        
        # Extract details from video_info
        title = video_info.get('vod_name', f"视频 {content_id}")
        img_url = video_info.get('vod_pic', '')
        desc = video_info.get('vod_content', '')
        remarks = video_info.get('vod_remarks', '')
        
        # Create play URL - Just use the content ID, we'll build the full URL in playerContent
        play_url = f"{title}${content_id}"
        
        vod = {
            'vod_id': content_id,
            'vod_name': title,
            'vod_pic': img_url,
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': remarks,
            'vod_actor': '',
            'vod_director': '',
            'vod_content': desc,
            'vod_play_from': 'SuperZhuang',
            'vod_play_url': play_url
        }
        
        # Debug log
        if self.debug:
            print(f"Detail content prepared for: {title}")
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword"""
        results = []
        
        # Debug log
        if self.debug:
            print(f"Searching for: {key}")
        
        # Search in all videos
        all_videos = self.fetchAllVideos()
        
        for item in all_videos:
            # Check if the keyword is in the title or description
            title = item.get('vod_name', '')
            desc = item.get('vod_content', '')
            
            if key.lower() in title.lower() or key.lower() in desc.lower():
                # Avoid duplicates
                if not any(r['vod_id'] == item['vod_id'] for r in results):
                    results.append(item)
        
        # Debug log
        if self.debug:
            print(f"Search results: {len(results)} videos")
        
        return {'list': results, 'page': pg, 'pagecount': 1, 'limit': 50, 'total': len(results)}
    
    def playerContent(self, flag, id, vipFlags):
        """Get playback information for TVBox to sniff video URL"""
        # Debug log
        if self.debug:
            print(f"Getting player content for ID: {id}")
        
        # Generate the mobile play URL with contentId
        play_url = f"{self.base_url}?tfcode=baidu_free&contentId={id}"
        
        # Mobile playback headers - include specific headers needed for video sniffing
        playback_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.superzhuang.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Debug log
        if self.debug:
            print(f"Player URL: {play_url}")
        
        return {'parse': 1, 'url': play_url, 'header': playback_headers}
    
    def localProxy(self, param):
        return param
    
    # Helper methods
    def fetchAllVideos(self, limit=None):
        """Fetch all videos from the API"""
        # Check if data is already in cache
        if 'all_videos' in self.data_cache:
            videos = self.data_cache['all_videos']
            return videos[:limit] if limit else videos
        
        videos = []
        
        try:
            # Debug log
            if self.debug:
                print(f"Fetching all videos from API: {self.content_list_api}")
            
            # Try with both mobile and PC headers
            response = None
            try:
                response = self.session.get(
                    self.content_list_api, 
                    headers=self.mobile_headers, 
                    timeout=10
                )
                response.raise_for_status()
            except Exception as e:
                if self.debug:
                    print(f"Mobile fetch failed: {e}, trying with PC headers")
                response = requests.get(
                    self.content_list_api,
                    headers=self.pc_headers,
                    timeout=10
                )
                response.raise_for_status()
            
            # Parse JSON response
            raw_text = response.text
            
            # Debug: Save raw response
            if self.debug:
                with open('/tmp/superzhuang_response.txt', 'w', encoding='utf-8') as f:
                    f.write(raw_text)
                    
                print(f"Response length: {len(raw_text)} bytes")
                print(f"Response preview: {raw_text[:200]}...")
            
            data = json.loads(raw_text)
            
            if data.get('code') == 0 and 'data' in data:
                content_list = data['data'].get('contentList', [])
                
                if self.debug:
                    print(f"Found {len(content_list)} videos in API response")
                
                for idx, item in enumerate(content_list):
                    content_id = item.get('contentId', '')
                    if not content_id:
                        continue
                    
                    title = item.get('contentTitle', '无标题')
                    cover_img = item.get('firstImg', '')
                    
                    # Extract season and episode numbers
                    season_num = str(item.get('videoSeasons', ''))
                    episode_num = str(item.get('videoEpisodes', ''))
                    
                    # Format remarks to show season and episode
                    remarks = ''
                    if season_num and episode_num:
                        remarks = f"第{season_num}季 第{episode_num}集"
                    elif season_num:
                        remarks = f"第{season_num}季"
                    elif episode_num:
                        remarks = f"第{episode_num}集"
                    
                    # Extract description
                    desc = item.get('contentDesc', '')
                    
                    # Create video object
                    video = {
                        'vod_id': content_id,
                        'vod_name': title,
                        'vod_pic': cover_img,
                        'vod_url': content_id,  # We'll use contentId as URL and resolve it in playerContent
                        'vod_content': desc,
                        'vod_remarks': remarks,
                        'season_num': season_num,
                        'episode_num': episode_num
                    }
                    
                    videos.append(video)
                    
                    # Debug log for first few videos
                    if self.debug and idx < 3:
                        print(f"Video {idx+1}: {title} (ID: {content_id})")
            else:
                if self.debug:
                    print(f"API returned non-success code: {data.get('code')}")
                    print(f"API message: {data.get('message', 'No message')}")
            
            # Cache the results
            self.data_cache['all_videos'] = videos
            print(f"Total: Fetched {len(videos)} videos")
            
        except Exception as e:
            import traceback
            print(f"Error fetching videos: {e}")
            if self.debug:
                traceback.print_exc()
        
        # Add a few fallback videos if none were found
        if not videos:
            # Add some fallback videos if API fails
            fallback_ids = ["1113819501245706240", "1118516111175106560", "1126129329008463872"]
            for i, fid in enumerate(fallback_ids):
                videos.append({
                    'vod_id': fid,
                    'vod_name': f"样本视频 {i+1}",
                    'vod_pic': "",
                    'vod_url': fid,
                    'vod_content': "API获取失败时的示例视频",
                    'vod_remarks': "示例"
                })
            
            if self.debug:
                print("Added fallback videos due to API failure")
        
        return videos[:limit] if limit else videos
        
    def fetchVideoDetail(self, content_id):
        """Fetch detailed info for a specific video"""
        # Debug log
        if self.debug:
            print(f"Fetching video detail for ID: {content_id}")
            
        try:
            # API endpoint for single video details
            detail_api = f"{self.api_url}?contentId={content_id}"
            
            # Try with mobile headers first
            response = None
            try:
                response = self.session.get(
                    detail_api, 
                    headers=self.mobile_headers, 
                    timeout=10
                )
                response.raise_for_status()
            except Exception as e:
                if self.debug:
                    print(f"Mobile detail fetch failed: {e}, trying with PC headers")
                response = requests.get(
                    detail_api,
                    headers=self.pc_headers,
                    timeout=10
                )
                response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 0 and 'data' in data:
                return data['data']
                
        except Exception as e:
            print(f"Error fetching video detail for {content_id}: {e}")
            
        return None
