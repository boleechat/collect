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

    # Base URL for GitHub raw content
    host = 'https://raw.githubusercontent.com'
    base_url = 'https://raw.githubusercontent.com/boleechat/collect/refs/heads/main'
    
    # Year-based categories with corresponding HTML files
    year_files = {
        '2025': 'yst2025-01-03.html',
        '2024': 'yst2024-01-12.html',
        '2023': 'yst2023-01-12.html',
        '2022': 'yst2022-01-12.html',
        '2021': 'yst2021-01-12.html',
        '2020': 'yst2020-01-12.html',
        '2019': 'yst2019-01-12.html',
        '2018': 'yst2018-01-12.html'
    }
    
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
        classes = [{'type_name': year, 'type_id': year} for year in self.year_files.keys()]
        
        # No filters for now, could be expanded later
        filters = {}
        
        result['class'] = classes
        result['filters'] = filters
        return result
    
    def homeVideoContent(self):
        """Get videos for the home page (using the most recent year)"""
        # Use default year for home page
        html = self.fetchSourceData(self.current_year)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract featured videos
        videos = self.extractVideos(soup, year=self.current_year, limit=30)
        
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for a specific year category"""
        if pg == '1':  # First page
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
        
        # Verify the tid is a valid year
        if tid not in self.year_files:
            tid = self.current_year
            
        # Fetch data for the selected year
        html = self.fetchSourceData(tid)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract videos for the specific year
        all_videos = self.extractVideos(soup, year=tid, limit=100)
        
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
            
        html = self.fetchSourceData(year)
        
        # Find the specific video info
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try to find the video by ID in all links
        links = soup.find_all('a', href=lambda href: href and original_id in href)
        
        if not links:
            # Fallback to search by id substring
            links = soup.find_all('a', href=lambda href: href and self.extract_id_from_url(href) == original_id)
        
        if not links:
            return {'list': [{'vod_name': '未找到视频', 'vod_play_from': 'Btime', 'vod_play_url': '未找到$' + vid}]}
        
        link = links[0]
        list_item = link.find_parent('li')
        
        title = link.get_text(strip=True)
        if not title:
            title_elem = link.find(['h3', 'h4', 'div', 'span'])
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                title = f"视频 {vid}"
        
        # Try to find a description
        desc = ""
        if list_item:
            # Try to extract text that follows the link but isn't part of another element
            for content in list_item.contents:
                if isinstance(content, str) and content.strip():
                    desc += content.strip() + " "
        
        if not desc:
            # Try other methods to find description
            desc_elem = link.find_next(['p', 'div'], class_=lambda x: x and ('desc' in x or 'info' in x))
            if desc_elem:
                desc = desc_elem.get_text(strip=True)
        
        # Fix the URL if it's relative
        url = link['href']
        
        # If the URL is relative, make it absolute using the base URL for the specific year
        if not url.startswith(('http://', 'https://')):
            parsed_base = urlparse(self.base_url)
            # Check if it starts with a slash
            if url.startswith('/'):
                url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
            else:
                # Get the directory part of the year's HTML file
                year_file = self.year_files[year]
                year_file_dir = '/'.join(year_file.split('/')[:-1])
                if year_file_dir:
                    year_file_dir += '/'
                url = f"{self.base_url}/{year_file_dir}{url}"
        
        # Create play URL
        play_url = f"{title}${url}"
        
        vod = {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': '',
            'vod_year': year,
            'vod_area': '',
            'vod_remarks': f"{year}年视频",
            'vod_actor': '',
            'vod_director': '',
            'vod_content': desc,
            'vod_play_from': 'Btime',
            'vod_play_url': play_url
        }
        
        # Try to find image
        img_url = ''
        if list_item:
            img_elem = list_item.find('img')
            if img_elem:
                if img_elem.has_attr('src'):
                    img_url = img_elem['src']
                elif img_elem.has_attr('data-src'):
                    img_url = img_elem['data-src']
        
        if not img_url:
            img_elem = link.find('img')
            if img_elem:
                if img_elem.has_attr('src'):
                    img_url = img_elem['src']
                elif img_elem.has_attr('data-src'):
                    img_url = img_elem['data-src']
                    
        # If still no image, look for img tag near the link
        if not img_url:
            if list_item:
                next_img = list_item.find_next('img')
                if next_img and next_img.has_attr('src'):
                    img_url = next_img['src']
        
        # Fix image URL if it's relative
        if img_url and not img_url.startswith(('http://', 'https://')):
            parsed_base = urlparse(self.base_url)
            # Check if it starts with a slash
            if img_url.startswith('/'):
                img_url = f"{parsed_base.scheme}://{parsed_base.netloc}{img_url}"
            else:
                # Get the directory part of the year's HTML file
                year_file = self.year_files[year]
                year_file_dir = '/'.join(year_file.split('/')[:-1])
                if year_file_dir:
                    year_file_dir += '/'
                img_url = f"{self.base_url}/{year_file_dir}{img_url}"
        
        vod['vod_pic'] = img_url
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """Search for videos by keyword across all years"""
        results = []
        
        # Search in each year's data
        for year in self.year_files.keys():
            html = self.fetchSourceData(year)
            soup = BeautifulSoup(html, 'html.parser')
            
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
                
                # Add year information to the video ID to help with later lookups
                video_id = f"{year}_{video_id}"
                    
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
                
                # Fix image URL if it's relative
                if img_url and not img_url.startswith(('http://', 'https://')):
                    parsed_base = urlparse(self.base_url)
                    # Check if it starts with a slash
                    if img_url.startswith('/'):
                        img_url = f"{parsed_base.scheme}://{parsed_base.netloc}{img_url}"
                    else:
                        # Get the directory part of the year's HTML file
                        year_file = self.year_files[year]
                        year_file_dir = '/'.join(year_file.split('/')[:-1])
                        if year_file_dir:
                            year_file_dir += '/'
                        img_url = f"{self.base_url}/{year_file_dir}{img_url}"
                
                # Find description
                desc_elem = link.find_next(['p', 'div'], class_=lambda x: x and ('desc' in x or 'info' in x))
                desc = desc_elem.get_text(strip=True) if desc_elem else ''
                
                # Avoid duplicates
                if not any(r['vod_id'] == video_id for r in results):
                    results.append({
                        'vod_id': video_id,
                        'vod_name': title,
                        'vod_pic': img_url,
                        'vod_remarks': f"{year}年",
                        'vod_year': year
                    })
        
        return {'list': results, 'page': pg, 'pagecount': 1, 'limit': 50, 'total': len(results)}
    
    def playerContent(self, flag, id, vipFlags):
        """Get playback information"""
        # If ID looks like a full URL, use it directly
        if id.startswith(('http://', 'https://')):
            return {'parse': 1, 'url': id, 'header': self.headers}
        
        # Otherwise, treat as a relative path and construct full URL
        if not id.startswith('/'):
            id = '/' + id
            
        parsed_base = urlparse(self.base_url)
        full_url = f"{parsed_base.scheme}://{parsed_base.netloc}{id}"
        
        return {'parse': 1, 'url': full_url, 'header': self.headers}
    
    def localProxy(self, param):
        return param
    
    # Helper methods
    def fetchSourceData(self, year=None):
        """Fetch the source data for a specific year"""
        if not year or year not in self.year_files:
            year = self.current_year
            
        # Build the source URL for the specified year
        source_url = f"{self.base_url}/{self.year_files[year]}"
        
        try:
            response = self.session.get(source_url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching source data for {year}: {e}")
            return ""
    
    def extractVideos(self, soup, year=None, limit=None):
        """Extract videos from the HTML content"""
        videos = []
        
        # First try to extract from list items
        list_items = soup.find_all('li')
        for item in list_items:
            link = item.find('a', href=True)
            if link:
                # Extract videos from list item
                item_videos = self.extractVideosFromListItem(item, year)
                videos.extend(item_videos)
                
                if limit and len(videos) >= limit:
                    break
        
        # If not enough videos found, look for links directly
        if not videos or (limit and len(videos) < limit):
            # Find all links that might be videos
            links = soup.find_all('a', href=True)
            
            for link in links:
                # Skip links without href or those that are likely navigation
                if not link['href'] or '#' in link['href'] or 'javascript:' in link['href']:
                    continue
                    
                # If we already have this link from list items, skip
                video_id = self.extract_id_from_url(link['href'])
                if year:
                    video_id = f"{year}_{video_id}"
                    
                if video_id and any(v['vod_id'] == video_id for v in videos):
                    continue
                
                # Extract video from link
                video = self.extractVideoFromLink(link, year)
                if video:
                    videos.append(video)
                
                if limit and len(videos) >= limit:
                    break
        
        return videos
    
    def extractVideosFromListItem(self, list_item, year=None):
        """Extract video information from a list item element"""
        videos = []
        
        # Find the link
        link = list_item.find('a', href=True)
        if not link:
            return videos
            
        # Extract video ID
        video_id = self.extract_id_from_url(link['href'])
        if not video_id:
            return videos
            
        # Add year to video ID if provided
        if year:
            video_id = f"{year}_{video_id}"
            
        # Get title
        title = link.get_text(strip=True)
        if not title:
            title_elem = link.find(['h3', 'h4', 'div', 'span'])
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                return videos  # Skip items without title
        
        # Find image
        img_elem = list_item.find('img')
        img_url = ''
        if img_elem:
            if img_elem.has_attr('src'):
                img_url = img_elem['src']
            elif img_elem.has_attr('data-src'):
                img_url = img_elem['data-src']
        
        # Fix image URL if it's relative
        if img_url and not img_url.startswith(('http://', 'https://')):
            parsed_base = urlparse(self.base_url)
            # Check if it starts with a slash
            if img_url.startswith('/'):
                img_url = f"{parsed_base.scheme}://{parsed_base.netloc}{img_url}"
            else:
                # Get the directory part of the year's HTML file
                if year:
                    year_file = self.year_files[year]
                    year_file_dir = '/'.join(year_file.split('/')[:-1])
                    if year_file_dir:
                        year_file_dir += '/'
                    img_url = f"{self.base_url}/{year_file_dir}{img_url}"
                else:
                    img_url = f"{self.base_url}/{img_url}"
        
        # Extract date if available
        date_text = ''
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', list_item.get_text())
        if date_match:
            date_text = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        
        # Use provided year or extracted year
        display_year = year if year else (date_match.group(1) if date_match else time.strftime("%Y", time.localtime()))
        
        # Create video object
        videos.append({
            'vod_id': video_id,
            'vod_name': title,
            'vod_pic': img_url,
            'vod_remarks': f"{display_year}年" if display_year else date_text,
            'vod_year': display_year
        })
        
        return videos
    
    def extractVideoFromLink(self, link, year=None):
        """Extract video information from a link element"""
        if not link.has_attr('href'):
            return None
            
        # Extract video ID
        video_id = self.extract_id_from_url(link['href'])
        if not video_id:
            return None
            
        # Add year to video ID if provided
        if year:
            video_id = f"{year}_{video_id}"
            
        # Get title
        title = link.get_text(strip=True)
        if not title:
            title_elem = link.find(['h3', 'h4', 'div', 'span'])
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                return None  # Skip items without title
        
        # Find image
        img_elem = link.find('img')
        img_url = ''
        if img_elem:
            if img_elem.has_attr('src'):
                img_url = img_elem['src']
            elif img_elem.has_attr('data-src'):
                img_url = img_elem['data-src']
                
        # If no image in link, look for nearby img
        if not img_url:
            parent = link.parent
            if parent:
                img_elem = parent.find('img')
                if img_elem and img_elem.has_attr('src'):
                    img_url = img_elem['src']
        
        # Fix image URL if it's relative
        if img_url and not img_url.startswith(('http://', 'https://')):
            parsed_base = urlparse(self.base_url)
            # Check if it starts with a slash
            if img_url.startswith('/'):
                img_url = f"{parsed_base.scheme}://{parsed_base.netloc}{img_url}"
            else:
                # Get the directory part of the year's HTML file
                if year:
                    year_file = self.year_files[year]
                    year_file_dir = '/'.join(year_file.split('/')[:-1])
                    if year_file_dir:
                        year_file_dir += '/'
                    img_url = f"{self.base_url}/{year_file_dir}{img_url}"
                else:
                    img_url = f"{self.base_url}/{img_url}"
        
        # Extract date if available
        date_text = ''
        parent_text = link.parent.get_text() if link.parent else ''
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', parent_text)
        if date_match:
            date_text = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        
        # Use provided year or extracted year
        display_year = year if year else (date_match.group(1) if date_match else time.strftime("%Y", time.localtime()))
        
        # Create video object
        return {
            'vod_id': video_id,
            'vod_name': title,
            'vod_pic': img_url,
            'vod_remarks': f"{display_year}年" if display_year else date_text,
            'vod_year': display_year
        }
    
    def extract_id_from_url(self, url):
        """Extract a unique ID from a URL"""
        # Try to find common patterns for video IDs
        patterns = [
            r'/([a-zA-Z0-9_-]+)\.html$',
            r'id=([a-zA-Z0-9_-]+)',
            r'/([a-zA-Z0-9_-]+)/$',
            r'video/([a-zA-Z0-9_-]+)',
            r'item\.btime\.com/([a-zA-Z0-9]+)',
            r'item\.btime\.com.*?([a-zA-Z0-9]{32})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no pattern matches, use the whole URL as a hash
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()
        
    def extract_year_and_id(self, video_id):
        """Extract year and original ID from a combined video ID"""
        if '_' in video_id:
            parts = video_id.split('_', 1)
            if parts[0] in self.year_files:
                return parts[0], parts[1]
        return None, video_id
