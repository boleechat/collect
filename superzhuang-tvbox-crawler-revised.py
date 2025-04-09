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
    
    # API URL for video details - this contains all videos
    api_url = "https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails"
    
    # Sample content ID to get full list of videos (as seen in your example)
    sample_content_id = "1222913635461312512"
    
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
        # Fetch all videos and return the first 30
        videos = self.getAllVideos()
        return {'list': videos[:30] if len(videos) > 30 else videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for the category with pagination"""
        if pg == '1':  # First page
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
        
        # Get all videos
        all_videos = self.getAllVideos()
        
        # Implement pagination
        videos_per_page = 20
        start_idx = (self.currentPg - 1) * videos_per_page
        end_idx = start_idx + videos_per_page
        
        # Get videos for the current page
        page_videos = all_videos[start_idx:end_idx] if start_idx < len(all_videos) else []
        
        # Calculate total pages
        total_pages = max(1, (len(all_videos) + videos_per_page - 1) // videos_per_page)
        
        result = {
            'list': page_videos,
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
        
        # Get all videos
        all_videos = self.getAllVideos()
        
        # Find the video with the matching content ID
        video_info = None
        for video in all_videos:
            if video.get('vod_id') == content_id:
                video_info = video
                break
        
        if not video_info:
            return {'list': [{'vod_name': '未找到视频', 'vod_play_from': 'SuperZhuang', 'vod_play_url': '未找到$' + content_id}]}
        
        # Get the video URL for the content ID
        video_url = self.getVideoUrl(content_id)
        
        # Extract vid parameter for Tencent video player if available
        vid = ''
        if 'vid=' in video_url:
            vid_match = re.search(r'vid=([^&]+)', video_url)
            vid = vid_match.group(1) if vid_match else ''
        
        # If we couldn't extract the vid, use the content ID as a fallback
        play_url = self.video_player_template.format(vid) if vid else f"https://m.superzhuang.com/programme?contentId={content_id}"
        
        # Create play URL
        formatted_play_url = f"{video_info.get('vod_name')}${play_url}"
        
        vod = {
            'vod_id': content_id,
            'vod_name': video_info.get('vod_name', ''),
            'vod_pic': video_info.get('vod_pic', ''),
            'vod_year': video_info.get('vod_year', ''),
            'vod_area': '中国',
            'vod_remarks': video_info.get('vod_remarks', ''),
            'vod_actor': '',
            'vod_director': '',
            'vod_content': video_info.get('vod_content', ''),
            'vod_play_from': 'SuperZhuang',
            'vod_play_url': formatted_play_url
        }
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword"""
        results = []
        
        # Get all videos
        all_videos = self.getAllVideos()
        
        for item in all_videos:
            # Check if the keyword is in the title
            title = item.get('vod_name', '')
            if key.lower() in title.lower():
                results.append(item)
        
        return {'list': results, 'page': pg, 'pagecount': 1, 'limit': 50, 'total': len(results)}
    
    def playerContent(self, flag, id, vipFlags):
        """Get playback information"""
        # For Tencent Video player URLs
        if 'v.qq.com' in id:
            return {'parse': 1, 'url': id, 'header': self.headers}
        
        # For direct URLs
        if id.startswith(('http://', 'https://')):
            return {'parse': 1, 'url': id, 'header': self.headers}
        
        # For content ID URLs
        if 'contentId=' in id:
            return {'parse': 1, 'url': id, 'header': self.headers}
        
        # Otherwise, construct full URL
        full_url = f"{self.host}/{id}" if not id.startswith('/') else f"{self.host}{id}"
        
        return {'parse': 1, 'url': full_url, 'header': self.headers}
    
    def localProxy(self, param):
        return param
    
    # Helper methods
    def getAllVideos(self):
        """Get all videos from the API"""
        # Check if data is already in cache
        cache_key = "all_videos"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        try:
            # Build parameters for the API request
            params = {
                'contentId': self.sample_content_id
            }
            
            response = self.session.get(self.api_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            json_data = response.json()
            
            videos = []
            
            if json_data.get('code') == 200 and 'data' in json_data:
                main_data = json_data['data']
                
                # Check if the data contains recommendContent which has all videos
                if 'recommendContent' in main_data and isinstance(main_data['recommendContent'], list):
                    for item in main_data['recommendContent']:
                        content_id = item.get('contentId', '')
                        title = item.get('contentTitle', '无标题')
                        cover_img = item.get('firstImg', '')
                        
                        # Get season and episode info
                        season = item.get('videoSeasons', '')
                        episode = item.get('videoEpisodes', '')
                        
                        remarks = ""
                        if season and episode:
                            remarks = f"第{season}季 第{episode}集"
                        elif season:
                            remarks = f"第{season}季"
                        elif episode:
                            remarks = f"第{episode}集"
                        
                        # Create video object
                        video = {
                            'vod_id': content_id,
                            'vod_name': title,
                            'vod_pic': cover_img,
                            'vod_remarks': remarks,
                            'vod_year': '',  # Year is not available in the data
                            'vod_area': '中国',
                            'vod_content': ''  # Content is not available in the recommendation list
                        }
                        
                        videos.append(video)
            
            # Cache the results
            self.data_cache[cache_key] = videos
            print(f"Fetched {len(videos)} videos in total")
            return videos
            
        except Exception as e:
            print(f"Error fetching all videos: {e}")
            return []
    
    def getVideoUrl(self, content_id):
        """Get video URL for a specific content ID"""
        try:
            # First try to get from cache
            cache_key = f"video_url_{content_id}"
            if cache_key in self.data_cache:
                return self.data_cache[cache_key]
            
            # Build the programme page URL
            programme_url = f"{self.host}/programme?contentId={content_id}"
            
            # Fetch the page content
            response = self.session.get(programme_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML to find the video URL
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for script tags that might contain the video URL
            scripts = soup.find_all('script')
            
            video_url = ''
            for script in scripts:
                script_text = script.string
                if script_text and 'vid=' in script_text:
                    # Find all occurrences of "vid="
                    vid_matches = re.findall(r'vid=([^&"\']+)', script_text)
                    if vid_matches:
                        # Use the first match
                        vid = vid_matches[0]
                        video_url = self.video_player_template.format(vid)
                        break
            
            # If we couldn't find the video URL in scripts, check for iframe
            if not video_url:
                iframe = soup.find('iframe')
                if iframe and 'src' in iframe.attrs:
                    iframe_src = iframe['src']
                    if 'vid=' in iframe_src:
                        vid_match = re.search(r'vid=([^&]+)', iframe_src)
                        if vid_match:
                            vid = vid_match.group(1)
                            video_url = self.video_player_template.format(vid)
            
            # Cache the result
            if video_url:
                self.data_cache[cache_key] = video_url
            
            return video_url
            
        except Exception as e:
            print(f"Error getting video URL for content ID {content_id}: {e}")
            return f"{self.host}/programme?contentId={content_id}"
