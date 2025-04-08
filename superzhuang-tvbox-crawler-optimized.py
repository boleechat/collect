#!/usr/bin/env python3
# coding=utf-8
# SuperZhuang TVBox crawler - Optimized version

import json
import sys
import re
import time
import os
from urllib.parse import urljoin, quote, urlparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update(self.mobile_headers)
        print("SuperZhuang initialized with mobile user agent")
        
        # Try to fetch videos on initialization
        try:
            self.fetchAllVideos(force_refresh=True)
        except Exception as e:
            print(f"Initial fetch failed: {e}")
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
    
    # Multiple API URLs for content - first one that works will be used
    content_apis = [
        'https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails?contentId=1217840147335688192',
        'https://api.superzhuangplus.com/api/stayUser/getContentList?pageNo=1&pageSize=100',
        'https://api.superzhuangplus.com/api/stayUser/getSectionContent?sectionId=1217840147335688192'
    ]
    
    # Mobile Headers for requests - Simulating iPhone browser
    mobile_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.superzhuang.com/',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Origin': 'https://m.superzhuang.com',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    # PC Headers for requests
    pc_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://www.superzhuang.com/',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Origin': 'https://www.superzhuang.com',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    # Cache for fetched data to reduce API calls
    data_cache = {}
    
    # Debug flag
    debug = True
    
    # Log file path - write to /tmp which exists on most systems
    log_file = '/tmp/superzhuang_tvbox.log'

    def log(self, message):
        """Write log message if debug is enabled"""
        if not self.debug:
            return
            
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + "\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")

    def homeContent(self, filter):
        """Generate content for home page"""
        result = {}
        
        self.log("Fetching home content")
        
        # Simple categories
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
        self.log("Fetching home video content")
        
        # Force refresh of videos
        videos = self.fetchAllVideos(force_refresh=True, limit=30)
        
        self.log(f"Home videos fetched: {len(videos)}")
        if videos:
            self.log(f"First video: {videos[0]['vod_name'] if 'vod_name' in videos[0] else 'unnamed'}")
        
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for a specific category"""
        if pg == '1':  # First page
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
        
        self.log(f"Fetching category content for {tid}, page {pg}")
        
        # Fetch all videos (no force refresh to avoid too many API calls)
        all_videos = self.fetchAllVideos()
        
        # Apply simple category filtering
        if tid == 'home':
            filtered_videos = [v for v in all_videos if '装修' in v.get('vod_name', '') or '家居' in v.get('vod_name', '')]
        elif tid == 'design':
            filtered_videos = [v for v in all_videos if '设计' in v.get('vod_name', '') or '案例' in v.get('vod_name', '')]
        else:  # 'all' or any other category
            filtered_videos = all_videos
        
        # Implement pagination
        videos_per_page = 20
        start_idx = (self.currentPg - 1) * videos_per_page
        end_idx = start_idx + videos_per_page
        
        # Calculate total pages
        total_pages = max(1, (len(filtered_videos) + videos_per_page - 1) // videos_per_page)
        
        # Get videos for current page
        current_page_videos = filtered_videos[start_idx:end_idx] if start_idx < len(filtered_videos) else []
        
        self.log(f"Category videos fetched: {len(current_page_videos)} of {len(filtered_videos)} total")
        
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
        
        self.log(f"Fetching detail content for ID: {content_id}")
        
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
                
                # Extract season and episode if available
                season_num = str(detail_info.get('videoSeasons', ''))
                episode_num = str(detail_info.get('videoEpisodes', ''))
                
                # Format remarks
                remarks = ''
                if season_num and episode_num:
                    remarks = f"第{season_num}季 第{episode_num}集"
                elif season_num:
                    remarks = f"第{season_num}季"
                elif episode_num:
                    remarks = f"第{episode_num}集"
                
                # Create video object
                video_info = {
                    'vod_id': content_id,
                    'vod_name': title,
                    'vod_pic': cover_img,
                    'vod_url': content_id,
                    'vod_content': desc,
                    'vod_remarks': remarks
                }
        
        if not video_info:
            self.log(f"Video not found for ID: {content_id}")
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
        
        self.log(f"Detail content prepared for: {title}")
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword"""
        results = []
        
        self.log(f"Searching for: {key}")
        
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
        
        self.log(f"Search results: {len(results)} videos")
        
        return {'list': results, 'page': pg, 'pagecount': 1, 'limit': 50, 'total': len(results)}
    
    def playerContent(self, flag, id, vipFlags):
        """Get playback information for TVBox to sniff video URL"""
        self.log(f"Getting player content for ID: {id}")
        
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
        
        self.log(f"Player URL: {play_url}")
        
        return {'parse': 1, 'url': play_url, 'header': playback_headers}
    
    def localProxy(self, param):
        return param
    
    # Helper methods
    def fetchAllVideos(self, force_refresh=False, limit=None):
        """Fetch all videos from the API"""
        # Check if data is already in cache and not forcing refresh
        if not force_refresh and 'all_videos' in self.data_cache:
            videos = self.data_cache['all_videos']
            return videos[:limit] if limit else videos
        
        videos = []
        api_success = False
        
        # Try each API URL until one works
        for api_url in self.content_apis:
            if api_success:
                break
                
            self.log(f"Trying API URL: {api_url}")
            
            try:
                # Try with mobile headers first
                response = None
                try:
                    response = self.session.get(
                        api_url, 
                        headers=self.mobile_headers, 
                        timeout=15
                    )
                    response.raise_for_status()
                except Exception as e:
                    self.log(f"Mobile fetch failed: {e}, trying with PC headers")
                    response = requests.get(
                        api_url,
                        headers=self.pc_headers,
                        timeout=15
                    )
                    response.raise_for_status()
                
                # Parse JSON response
                raw_text = response.text
                
                # Debug: Save raw response
                if self.debug:
                    try:
                        with open('/tmp/superzhuang_response.txt', 'w', encoding='utf-8') as f:
                            f.write(raw_text)
                    except Exception as e:
                        self.log(f"Error saving response: {e}")
                        
                self.log(f"Response length: {len(raw_text)} bytes")
                self.log(f"Response preview: {raw_text[:100]}...")
                
                data = json.loads(raw_text)
                
                # Process response based on API structure
                if data.get('code') == 0 and 'data' in data:
                    # Determine the structure of the response
                    if 'contentList' in data['data']:
                        content_list = data['data']['contentList']
                    elif 'list' in data['data']:
                        content_list = data['data']['list']
                    elif isinstance(data['data'], list):
                        content_list = data['data']
                    else:
                        content_list = []
                        # Check if data['data'] itself is a content item
                        if 'contentId' in data['data']:
                            content_list = [data['data']]
                            
                    self.log(f"Found {len(content_list)} videos in API response")
                    
                    if content_list:
                        for idx, item in enumerate(content_list):
                            # Different APIs may use different field names
                            content_id = item.get('contentId', '')
                            if not content_id:
                                # Try alternative field names
                                content_id = item.get('id', '')
                                
                            if not content_id:
                                continue
                            
                            # Different APIs may use different field names
                            title_fields = ['contentTitle', 'title', 'name']
                            title = '无标题'
                            for field in title_fields:
                                if field in item and item[field]:
                                    title = item[field]
                                    break
                            
                            # Different APIs may use different field names for images
                            cover_fields = ['firstImg', 'cover', 'coverImg', 'image', 'thumb']
                            cover_img = ''
                            for field in cover_fields:
                                if field in item and item[field]:
                                    cover_img = item[field]
                                    break
                            
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
                            
                            # Extract description - try different field names
                            desc_fields = ['contentDesc', 'description', 'desc', 'introduce', 'summary']
                            desc = ''
                            for field in desc_fields:
                                if field in item and item[field]:
                                    desc = item[field]
                                    break
                            
                            # Create video object
                            video = {
                                'vod_id': content_id,
                                'vod_name': title,
                                'vod_pic': cover_img,
                                'vod_url': content_id,
                                'vod_content': desc,
                                'vod_remarks': remarks,
                                'season_num': season_num,
                                'episode_num': episode_num
                            }
                            
                            videos.append(video)
                            
                            # Debug log for first few videos
                            if idx < 3:
                                self.log(f"Video {idx+1}: {title} (ID: {content_id})")
                        
                        # If we got videos, mark API as successful
                        if videos:
                            api_success = True
                            break
                    else:
                        self.log("No videos found in content list")
                else:
                    self.log(f"API returned non-success code: {data.get('code')}")
                    self.log(f"API message: {data.get('message', 'No message')}")
                    
            except Exception as e:
                import traceback
                self.log(f"Error fetching videos from {api_url}: {e}")
                if self.debug:
                    traceback.print_exc()
        
        # Add fallback videos if none were found
        if not videos:
            # These are known to work
            fallback_videos = [
                {
                    'vod_id': "1113819501245706240",
                    'vod_name': "徐汇42㎡住俩人：妥妥地够住！",
                    'vod_pic': "https://img.superzhuangplus.com/hyCrm-images/20230601/63328304-4890-4034-97df-07fb3e44b458.jpg",
                    'vod_url': "1113819501245706240",
                    'vod_content': "小户型装修案例",
                    'vod_remarks': "第17季 第14集"
                },
                {
                    'vod_id': "1118516111175106560",
                    'vod_name': "【装修奇葩说】第7季 丨 超级装修分享",
                    'vod_pic': "",
                    'vod_url': "1118516111175106560",
                    'vod_content': "装修分享视频",
                    'vod_remarks': "第7季"
                },
                {
                    'vod_id': "1126129329008463872",
                    'vod_name': "金色阿尔法装修记|日式家装",
                    'vod_pic': "",
                    'vod_url': "1126129329008463872",
                    'vod_content': "日式家装案例",
                    'vod_remarks': "设计案例"
                }
            ]
            videos.extend(fallback_videos)
            self.log("Added fallback videos due to API failure")
        
        # Cache the results
        self.data_cache['all_videos'] = videos
        self.log(f"Total: Fetched {len(videos)} videos")
        
        return videos[:limit] if limit else videos
        
    def fetchVideoDetail(self, content_id):
        """Fetch detailed info for a specific video"""
        self.log(f"Fetching video detail for ID: {content_id}")
            
        try:
            # API endpoint for single video details
            detail_api = f"{self.api_url}?contentId={content_id}"
            
            # Try with mobile headers first
            response = None
            try:
                response = self.session.get(
                    detail_api, 
                    headers=self.mobile_headers, 
                    timeout=15
                )
                response.raise_for_status()
            except Exception as e:
                self.log(f"Mobile detail fetch failed: {e}, trying with PC headers")
                response = requests.get(
                    detail_api,
                    headers=self.pc_headers,
                    timeout=15
                )
                response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 0 and 'data' in data:
                self.log(f"Successfully fetched details for ID: {content_id}")
                return data['data']
                
        except Exception as e:
            self.log(f"Error fetching video detail for {content_id}: {e}")
            
        return None
