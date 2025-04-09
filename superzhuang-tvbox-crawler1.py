#!/usr/bin/env python3
# coding=utf-8
# Modified for SuperZhuang website

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
        print("SuperZhuang initialized")
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
    api_host = 'https://api.superzhuangplus.com'
    base_url = 'https://m.superzhuang.com/owner/?typecode=video'
    
    # API URL templates
    api_url = "https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails"
    video_list_api = "https://api.superzhuangplus.com/api/stayUser/getApiDecorationContent"
    
    # Video player template
    video_player_template = "https://v.qq.com/txp/iframe/player.html?vid={}"
    
    # Headers for requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.superzhuang.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive'
    }
    
    # Cache for fetched data to reduce API calls
    data_cache = {}
    
    def homeContent(self, filter):
        """Generate content for home page"""
        result = {}
        
        # Create categories - for now we only have one category
        classes = [{'type_name': '过往节目', 'type_id': 'video'}]
        
        # No filters for now
        filters = {}
        
        result['class'] = classes
        result['filters'] = filters
        return result
    
    def homeVideoContent(self):
        """Get videos for the home page"""
        # Fetch first page of videos
        videos = self.fetchVideosForPage(1, 20)
        
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for the category with pagination"""
        if pg == '1':  # First page
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
        
        # Fetch videos for the selected page
        videos = self.fetchVideosForPage(self.currentPg, 20)
        
        # Get total count for pagination
        total_count = self.getTotalCount()
        
        # Calculate total pages
        page_size = 20
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        
        result = {
            'list': videos,
            'page': pg,
            'pagecount': total_pages,
            'limit': page_size,
            'total': total_count
        }
        
        return result
    
    def detailContent(self, ids):
        """Get details for a specific video"""
        if not ids:
            return {'list': []}
        
        content_id = ids[0]
        
        # Get detailed info for this video
        video_info = self.fetchVideoDetail(content_id)
        
        if not video_info:
            return {'list': [{'vod_name': '未找到视频', 'vod_play_from': 'SuperZhuang', 'vod_play_url': '未找到$' + content_id}]}
        
        # Extract video ID for Tencent video player
        vid = video_info.get('vid', '')
        
        # Create play URL
        play_url = f"{video_info.get('vod_name')}${self.video_player_template.format(vid)}"
        
        vod = {
            'vod_id': content_id,
            'vod_name': video_info.get('vod_name', ''),
            'vod_pic': video_info.get('vod_pic', ''),
            'vod_year': video_info.get('vod_year', ''),
            'vod_area': video_info.get('vod_area', ''),
            'vod_remarks': video_info.get('vod_remarks', ''),
            'vod_actor': video_info.get('vod_actor', ''),
            'vod_director': video_info.get('vod_director', ''),
            'vod_content': video_info.get('vod_content', ''),
            'vod_play_from': 'SuperZhuang',
            'vod_play_url': play_url
        }
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword"""
        results = []
        
        # Search in the list of videos
        all_videos = self.getAllVideos()
        
        for item in all_videos:
            # Check if the keyword is in the title
            title = item.get('vod_name', '')
            if key.lower() in title.lower():
                results.append(item)
        
        return {'list': results, 'page': pg, 'pagecount': 1, 'limit': 50, 'total': len(results)}
    
    def playerContent(self, flag, id, vipFlags):
        """Get playback information"""
        # Handle Tencent Video player URLs
        if 'v.qq.com' in id:
            # Return URL for TVBox to handle extraction
            return {'parse': 1, 'url': id, 'header': self.headers}
        
        # For direct URLs
        if id.startswith(('http://', 'https://')):
            return {'parse': 0, 'url': id, 'header': self.headers}
        
        # Otherwise, construct full URL
        full_url = f"{self.host}/{id}" if not id.startswith('/') else f"{self.host}{id}"
        
        return {'parse': 1, 'url': full_url, 'header': self.headers}
    
    def localProxy(self, param):
        return param
    
    # Helper methods
    def fetchVideosForPage(self, page, page_size):
        """Fetch videos for a specific page"""
        # Check if data is already in cache
        cache_key = f"page_{page}_{page_size}"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        try:
            # Build parameters for the API request
            params = {
                'page': page,
                'size': page_size,
                'flag': 'video',
                'appid': 'decorate'
            }
            
            response = self.session.get(self.video_list_api, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            json_data = response.json()
            
            if json_data.get('code') == 200 and 'data' in json_data:
                data = json_data['data'].get('records', [])
                
                videos = []
                for item in data:
                    content_id = item.get('contentId', '')
                    title = item.get('title', '无标题')
                    cover = item.get('coverUrl', '')
                    upload_time = item.get('createTime', '')
                    
                    # Format date if available
                    if upload_time:
                        try:
                            # Convert timestamp to datetime
                            date_str = datetime.fromtimestamp(int(upload_time) / 1000).strftime("%Y-%m-%d")
                        except:
                            date_str = "未知时间"
                    else:
                        date_str = "未知时间"
                    
                    # Get season and episode info
                    season = item.get('seasonNo', '')
                    episode = item.get('episodeNo', '')
                    
                    remarks = ""
                    if season and episode:
                        remarks = f"第{season}季 第{episode}集"
                    elif season:
                        remarks = f"第{season}季"
                    elif episode:
                        remarks = f"第{episode}集"
                    
                    if date_str != "未知时间":
                        remarks = f"{remarks} {date_str}" if remarks else date_str
                    
                    # Create video object
                    video = {
                        'vod_id': content_id,
                        'vod_name': title,
                        'vod_pic': cover,
                        'vod_remarks': remarks,
                        'vod_year': date_str.split('-')[0] if date_str != "未知时间" else '',
                        'vod_area': '中国',
                        'vod_content': item.get('summary', '')
                    }
                    
                    videos.append(video)
                
                # Cache the results
                self.data_cache[cache_key] = videos
                print(f"Fetched {len(videos)} videos for page {page}")
                return videos
            
            return []
            
        except Exception as e:
            print(f"Error fetching videos for page {page}: {e}")
            return []
    
    def fetchVideoDetail(self, content_id):
        """Fetch detailed information for a specific video"""
        # Check if data is already in cache
        cache_key = f"detail_{content_id}"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        try:
            # Build parameters for the API request
            params = {
                'contentId': content_id
            }
            
            response = self.session.get(self.api_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            json_data = response.json()
            
            if json_data.get('code') == 200 and 'data' in json_data:
                data = json_data['data']
                
                # Extract Tencent video ID from the videoUrl field
                video_url = data.get('videoUrl', '')
                vid_match = re.search(r'vid=([^&]+)', video_url)
                vid = vid_match.group(1) if vid_match else ''
                
                # Format date if available
                upload_time = data.get('createTime', '')
                if upload_time:
                    try:
                        # Convert timestamp to datetime
                        date_str = datetime.fromtimestamp(int(upload_time) / 1000).strftime("%Y-%m-%d")
                    except:
                        date_str = "未知时间"
                else:
                    date_str = "未知时间"
                
                # Get season and episode info
                season = data.get('seasonNo', '')
                episode = data.get('episodeNo', '')
                
                remarks = ""
                if season and episode:
                    remarks = f"第{season}季 第{episode}集"
                elif season:
                    remarks = f"第{season}季"
                elif episode:
                    remarks = f"第{episode}集"
                
                if date_str != "未知时间":
                    remarks = f"{remarks} {date_str}" if remarks else date_str
                
                # Create video detail object
                video_detail = {
                    'vod_id': content_id,
                    'vod_name': data.get('title', '无标题'),
                    'vod_pic': data.get('coverUrl', ''),
                    'vod_year': date_str.split('-')[0] if date_str != "未知时间" else '',
                    'vod_area': '中国',
                    'vod_remarks': remarks,
                    'vod_actor': data.get('author', ''),
                    'vod_director': '',
                    'vod_content': data.get('summary', ''),
                    'vid': vid
                }
                
                # Cache the results
                self.data_cache[cache_key] = video_detail
                print(f"Fetched details for video {content_id}")
                return video_detail
            
            return None
            
        except Exception as e:
            print(f"Error fetching video details for {content_id}: {e}")
            return None
    
    def getTotalCount(self):
        """Get total count of videos"""
        try:
            # Build parameters for the API request
            params = {
                'page': 1,
                'size': 1,
                'flag': 'video',
                'appid': 'decorate'
            }
            
            response = self.session.get(self.video_list_api, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            json_data = response.json()
            
            if json_data.get('code') == 200 and 'data' in json_data:
                return json_data['data'].get('total', 0)
            
            return 0
            
        except Exception as e:
            print(f"Error fetching total count: {e}")
            return 0
    
    def getAllVideos(self):
        """Get all videos for search functionality"""
        # Get total count
        total_count = self.getTotalCount()
        
        if total_count <= 0:
            return []
        
        # Calculate number of pages needed
        page_size = 50
        total_pages = (total_count + page_size - 1) // page_size
        
        all_videos = []
        
        # Fetch all pages
        for page in range(1, total_pages + 1):
            videos = self.fetchVideosForPage(page, page_size)
            all_videos.extend(videos)
            
            # Add a short delay to avoid overwhelming the API
            time.sleep(0.5)
        
        return all_videos
