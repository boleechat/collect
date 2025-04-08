#!/usr/bin/env python3
# coding=utf-8
# SuperZhuang TVBox crawler - Mobile browser mode

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
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.superzhuang.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Origin': 'https://m.superzhuang.com',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site'
    }
    
    # Cache for fetched data to reduce API calls
    data_cache = {}
    
    # Categories based on seasons
    default_season = '全部'

    def homeContent(self, filter):
        """Generate content for home page with season-based categories"""
        result = {}
        
        # Fetch all videos to analyze seasons
        videos = self.fetchAllVideos()
        
        # Extract unique seasons
        seasons = set()
        for video in videos:
            season = video.get('season_num', '未知')
            if season and season != '未知':
                seasons.add(f"第{season}季")
        
        # Convert to sorted list and add default "All" category
        season_list = sorted(list(seasons), key=lambda x: int(re.sub(r'\D', '', x) or 0))
        season_list.insert(0, self.default_season)
        
        # Create categories
        classes = [{'type_name': season, 'type_id': season} for season in season_list]
        
        # No filters for now, could be expanded later
        filters = {}
        
        result['class'] = classes
        result['filters'] = filters
        return result
    
    def homeVideoContent(self):
        """Get videos for the home page"""
        videos = self.fetchAllVideos(limit=30)
        
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for a specific season category"""
        if pg == '1':  # First page
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
        
        # Fetch all videos
        all_videos = self.fetchAllVideos()
        
        # Filter by season if not "全部"
        if tid != self.default_season:
            # Extract season number from category name
            season_num = re.sub(r'\D', '', tid)
            all_videos = [v for v in all_videos if v.get('season_num') == season_num]
        
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
        
        content_id = ids[0]
        
        # Find the specific video info in the cached data
        all_videos = self.fetchAllVideos()
        
        video_info = None
        for item in all_videos:
            if item.get('vod_id') == content_id:
                video_info = item
                break
        
        if not video_info:
            return {'list': [{'vod_name': '未找到视频', 'vod_play_from': 'SuperZhuang', 'vod_play_url': '未找到$' + content_id}]}
        
        # Extract details from video_info
        title = video_info.get('vod_name', f"视频 {content_id}")
        url = video_info.get('vod_url', '')
        img_url = video_info.get('vod_pic', '')
        desc = video_info.get('vod_content', '')
        remarks = video_info.get('vod_remarks', '')
        
        # Create play URL
        play_url = f"{title}${url}"
        
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
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword"""
        results = []
        
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
        
        return {'list': results, 'page': pg, 'pagecount': 1, 'limit': 50, 'total': len(results)}
    
    def playerContent(self, flag, id, vipFlags):
        """Get playback information for TVBox to sniff video URL"""
        # Generate the mobile play URL with contentId
        play_url = f"{self.base_url}?tfcode=baidu_free&contentId={id}"
        
        # Mobile playback headers - include specific headers needed for video sniffing
        playback_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.superzhuang.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        
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
            # Fetch video list from API with mobile headers
            response = self.session.get(
                self.content_list_api, 
                headers=self.headers, 
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('code') == 0 and 'data' in data:
                content_list = data['data'].get('contentList', [])
                
                for item in content_list:
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
            
            # Cache the results
            self.data_cache['all_videos'] = videos
            print(f"Total: Fetched {len(videos)} videos")
            
        except Exception as e:
            print(f"Error fetching videos: {e}")
        
        return videos[:limit] if limit else videos
        
    def fetchVideoDetail(self, content_id):
        """Fetch detailed info for a specific video if needed"""
        try:
            # API endpoint for single video details
            detail_api = f"{self.api_url}?contentId={content_id}"
            
            response = self.session.get(
                detail_api, 
                headers=self.headers, 
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 0 and 'data' in data:
                return data['data']
                
        except Exception as e:
            print(f"Error fetching video detail for {content_id}: {e}")
            
        return None
