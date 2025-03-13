#!/usr/bin/env python3
# coding=utf-8
# by boleechat

import json
import sys
import re
import time
from urllib.parse import urljoin, quote
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

    source_url = 'https://raw.githubusercontent.com/boleechat/collect/refs/heads/main/2025-01-03.html'
    host = 'https://raw.githubusercontent.com'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    def homeContent(self, filter):
        """Generate content for home page with categories"""
        result = {}
        
        # Get source data
        html = self.fetchSourceData()
        
        # Parse categories
        categories = self.extractCategories(html)
        classes = [{'type_name': cate, 'type_id': cate} for cate in categories]
        
        # No filters for now, could be expanded later
        filters = {}
        
        result['class'] = classes
        result['filters'] = filters
        return result
    
    def homeVideoContent(self):
        """Get videos for the home page"""
        html = self.fetchSourceData()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract featured videos
        videos = self.extractVideos(soup, limit=12)
        
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for a specific category"""
        if pg == '1':  # First page
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
            
        html = self.fetchSourceData()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract videos for the category
        all_videos = []
        
        # Find the category section
        category_sections = soup.find_all('div', class_=lambda x: x and 'section' in x)
        for section in category_sections:
            title_elem = section.find(['h2', 'h3'])
            if title_elem and tid in title_elem.text:
                # Found the category, extract videos
                video_items = section.find_all('a', href=True)
                for item in video_items:
                    title = item.get_text(strip=True)
                    if not title:
                        title_elem = item.find(['h3', 'h4', 'div', 'span'])
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                    
                    link = item['href']
                    # Extract ID from the link
                    video_id = self.extract_id_from_url(link)
                    
                    # Find image
                    img_elem = item.find('img')
                    img_url = ''
                    if img_elem and img_elem.has_attr('src'):
                        img_url = img_elem['src']
                    elif img_elem and img_elem.has_attr('data-src'):
                        img_url = img_elem['data-src']
                    
                    # Find description or remarks
                    desc_elem = item.find(['p', 'div'], class_=lambda x: x and ('desc' in x or 'info' in x))
                    desc = desc_elem.get_text(strip=True) if desc_elem else ''
                    
                    if title and video_id:
                        all_videos.append({
                            'vod_id': video_id,
                            'vod_name': title,
                            'vod_pic': img_url,
                            'vod_remarks': desc,
                            'vod_year': time.strftime("%Y", time.localtime())
                        })
                break
        
        # If no videos found in sections, try general extraction
        if not all_videos:
            all_videos = self.extractVideos(soup, category=tid)
        
        # Implement pagination
        videos_per_page = 20
        start_idx = (self.currentPg - 1) * videos_per_page
        end_idx = start_idx + videos_per_page
        
        result = {
            'list': all_videos[start_idx:end_idx],
            'page': pg,
            'pagecount': max(1, (len(all_videos) + videos_per_page - 1) // videos_per_page),
            'limit': videos_per_page,
            'total': len(all_videos)
        }
        
        return result
    
    def detailContent(self, ids):
        """Get details for a specific video"""
        if not ids:
            return {'list': []}
        
        vid = ids[0]
        html = self.fetchSourceData()
        
        # Find the specific video info
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try to find the video by ID in all links
        links = soup.find_all('a', href=lambda href: href and vid in href)
        
        if not links:
            # Fallback to search by id substring
            links = soup.find_all('a', href=lambda href: href and self.extract_id_from_url(href) == vid)
        
        if not links:
            return {'list': [{'vod_name': '未找到视频', 'vod_play_from': 'Btime', 'vod_play_url': '未找到$' + vid}]}
        
        link = links[0]
        title = link.get_text(strip=True)
        if not title:
            title_elem = link.find(['h3', 'h4', 'div', 'span'])
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                title = f"视频 {vid}"
        
        # Try to find a description
        desc = ""
        desc_elem = link.find_next(['p', 'div'], class_=lambda x: x and ('desc' in x or 'info' in x))
        if desc_elem:
            desc = desc_elem.get_text(strip=True)
        
        # Try to find more information
        info = {}
        info_elems = soup.find_all(['div', 'span'], class_=lambda x: x and ('info' in x or 'meta' in x))
        for elem in info_elems:
            text = elem.get_text(strip=True)
            if '导演' in text:
                info['director'] = text.split('导演')[-1].strip()
            if '演员' in text or '主演' in text:
                info['actor'] = text.split('演员')[-1].split('主演')[-1].strip()
            if '类型' in text:
                info['type'] = text.split('类型')[-1].strip()
            if '年份' in text:
                info['year'] = text.split('年份')[-1].strip()
        
        # Create play URL
        play_url = f"{title}${link['href']}"
        
        vod = {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': '',
            'vod_year': info.get('year', ''),
            'vod_area': '',
            'vod_remarks': '',
            'vod_actor': info.get('actor', ''),
            'vod_director': info.get('director', ''),
            'vod_content': desc,
            'vod_play_from': 'Btime',
            'vod_play_url': play_url
        }
        
        # Try to find image
        img_elem = link.find('img')
        if img_elem:
            if img_elem.has_attr('src'):
                vod['vod_pic'] = img_elem['src']
            elif img_elem.has_attr('data-src'):
                vod['vod_pic'] = img_elem['data-src']
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword"""
        html = self.fetchSourceData()
        soup = BeautifulSoup(html, 'html.parser')
        
        results = []
        
        # Find all elements that might contain the search term
        elements = soup.find_all(text=lambda text: text and key in text)
        
        for elem in elements:
            # Find the parent link or container
            link = elem.find_parent('a')
            if not link:
                continue
                
            if not link.has_attr('href'):
                continue
                
            # Extract video ID
            video_id = self.extract_id_from_url(link['href'])
            if not video_id:
                continue
                
            # Get title
            title = elem.get_text(strip=True)
            if not title:
                title_elem = link.find(['h3', 'h4', 'div', 'span'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    title = f"视频 {video_id}"
            
            # Find image
            img_elem = link.find('img')
            img_url = ''
            if img_elem and img_elem.has_attr('src'):
                img_url = img_elem['src']
            elif img_elem and img_elem.has_attr('data-src'):
                img_url = img_elem['data-src']
            
            # Find description
            desc_elem = link.find_next(['p', 'div'], class_=lambda x: x and ('desc' in x or 'info' in x))
            desc = desc_elem.get_text(strip=True) if desc_elem else ''
            
            # Avoid duplicates
            if not any(r['vod_id'] == video_id for r in results):
                results.append({
                    'vod_id': video_id,
                    'vod_name': title,
                    'vod_pic': img_url,
                    'vod_remarks': desc,
                    'vod_year': time.strftime("%Y", time.localtime())
                })
        
        return {'list': results, 'page': pg, 'pagecount': 1, 'limit': 20, 'total': len(results)}
    
    def playerContent(self, flag, id, vipFlags):
        """Get playback information"""
        return {'parse': 1, 'url': id, 'header': ''}
    
    def localProxy(self, param):
        return param
    
    # Helper methods
    def fetchSourceData(self):
        """Fetch the source data from the specified URL"""
        try:
            response = self.session.get(self.source_url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching source data: {e}")
            return ""
    
    def extractCategories(self, html):
        """Extract categories from the HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        categories = []
        
        # Try to find categories from section headings
        section_headings = soup.find_all(['h2', 'h3', 'h4'])
        for heading in section_headings:
            text = heading.get_text(strip=True)
            if text and len(text) < 15:  # Reasonable length for a category name
                categories.append(text)
        
        # If no categories found, use default ones
        if not categories:
            categories = ["电视剧", "电影", "综艺", "动漫", "纪录片", "教育"]
        
        return categories
    
    def extractVideos(self, soup, category=None, limit=None):
        """Extract videos from the HTML content"""
        videos = []
        
        # Find all links that might be videos
        links = soup.find_all('a', href=True)
        
        for link in links:
            # Skip links without href or those that are likely navigation
            if not link['href'] or '#' in link['href'] or 'javascript:' in link['href']:
                continue
                
            # Extract video ID
            video_id = self.extract_id_from_url(link['href'])
            if not video_id:
                continue
            
            # Get title
            title = link.get_text(strip=True)
            if not title:
                title_elem = link.find(['h3', 'h4', 'div', 'span'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    continue  # Skip items without title
            
            # If category is specified, check if this item belongs to it
            if category:
                parent_section = link.find_parent(['div', 'section'])
                if parent_section:
                    section_heading = parent_section.find(['h2', 'h3', 'h4'])
                    if section_heading and category not in section_heading.get_text(strip=True):
                        continue
            
            # Find image
            img_elem = link.find('img')
            img_url = ''
            if img_elem and img_elem.has_attr('src'):
                img_url = img_elem['src']
            elif img_elem and img_elem.has_attr('data-src'):
                img_url = img_elem['data-src']
            
            # Find description or remarks
            desc_elem = link.find_next(['p', 'div'], class_=lambda x: x and ('desc' in x or 'info' in x))
            desc = desc_elem.get_text(strip=True) if desc_elem else ''
            
            # Avoid duplicates
            if not any(v['vod_id'] == video_id for v in videos):
                videos.append({
                    'vod_id': video_id,
                    'vod_name': title,
                    'vod_pic': img_url,
                    'vod_remarks': desc,
                    'vod_year': time.strftime("%Y", time.localtime())
                })
            
            if limit and len(videos) >= limit:
                break
        
        return videos
    
    def extract_id_from_url(self, url):
        """Extract a unique ID from a URL"""
        # Try to find common patterns for video IDs
        patterns = [
            r'/([a-zA-Z0-9_-]+)\.html$',
            r'id=([a-zA-Z0-9_-]+)',
            r'/([a-zA-Z0-9_-]+)/$',
            r'video/([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no pattern matches, use the whole URL as a hash
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()
