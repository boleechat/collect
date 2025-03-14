#!/usr/bin/env python3
# coding=utf-8
# by boleechat

import json
import sys
import re
import time
from urllib.parse import urljoin, quote, urlparse
import requests
from bs4 import BeautifulSoup
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

    # Base URL for Btime
    host = 'https://www.btime.com'
    
    # Year-based categories
    years = ['2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018']
    
    # Default year to use
    current_year = '2025'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    def homeContent(self, filter):
        """Generate content for home page with year-based categories"""
        result = {}
        
        # Create year-based categories
        classes = [{'type_name': year, 'type_id': year} for year in self.years]
        
        # No filters for now, could be expanded later
        filters = {}
        
        result['class'] = classes
        result['filters'] = filters
        return result
    
    def homeVideoContent(self):
        """Get videos for the home page (using the most recent year)"""
        # Use default year for home page
        videos = self.fetchYearData(self.current_year)
        
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for a specific year category"""
        if pg == '1':  # First page
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
        
        # Verify the tid is a valid year
        if tid not in self.years:
            tid = self.current_year
            
        # Fetch data for the selected year
        all_videos = self.fetchYearData(tid)
        
        # Implement pagination
        videos_per_page = 20
        start_idx = (self.currentPg - 1) * videos_per_page
        end_idx = start_idx + videos_per_page
        
        # Calculate total pages
        total_pages = max(1, (len(all_videos) + videos_per_page - 1) // videos_per_page)
        
        result = {
            'list': all_videos[start_idx:end_idx],
            'page': pg,
            'pagecount': total_pages,
            'limit': videos_per_page,
            'total': len(all_videos)
        }
        
        return result
    
    def fetchYearData(self, year):
        """Fetch and parse video data for a specific year"""
        url = f"{self.host}/year/{year}"
        response = self.session.get(url)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        videos = []
        
        for item in soup.find_all('div', class_='video-item'):
            title = item.find('h3').get_text(strip=True)
            link = item.find('a')['href']
            img = item.find('img')['src']
            date = item.find('span', class_='date').get_text(strip=True)
            
            video = {
                'vod_id': link.split('/')[-1],
                'vod_name': title,
                'vod_pic': img,
                'vod_year': year,
                'vod_area': '',
                'vod_remarks': date,
                'vod_actor': '',
                'vod_director': '',
                'vod_content': '',
                'vod_play_from': 'Btime',
                'vod_play_url': f"{title}${self.host}{link}"
            }
            
            videos.append(video)
        
        return videos
    
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
            
        videos = self.fetchYearData(year)
        
        for video in videos:
            if video['vod_id'] == original_id:
                return {'list': [video]}
        
        return {'list': [{'vod_name': '未找到视频', 'vod_play_from': 'Btime', 'vod_play_url': '未找到$' + vid}]}
    
    def extract_year_and_id(self, vid):
        """Extract year and original ID from video ID"""
        parts = vid.split('_')
        if len(parts) == 2:
            return parts[0], parts[1]
        return None, vid
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword across all years"""
        results = []
        for year in self.years:
            videos = self.fetchYearData(year)
            for video in videos:
                if key.lower() in video['vod_name'].lower():
                    results.append(video)
        
        # Implement pagination
        videos_per_page = 20
        start_idx = (int(pg) - 1) * videos_per_page
        end_idx = start_idx + videos_per_page
        
        # Calculate total pages
        total_pages = max(1, (len(results) + videos_per_page - 1) // videos_per_page)
        
        result = {
            'list': results[start_idx:end_idx],
            'page': pg,
            'pagecount': total_pages,
            'limit': videos_per_page,
            'total': len(results)
        }
        
        return result