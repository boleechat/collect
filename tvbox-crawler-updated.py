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
        videos = self.extractVideos(soup, limit=30)  # Increased limit to show more videos
        
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
        
        # If no sections with class, try to look for sections by heading content
        if not category_sections:
            # Look for headings that might contain category names
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for heading in headings:
                if tid in heading.get_text(strip=True):
                    category_sections.append(heading.parent)
        
        # If still no sections found, look for list items with links
        if not category_sections:
            list_items = soup.find_all('li')
            for item in list_items:
                if item.find('a'):
                    all_videos.extend(self.extractVideosFromListItem(item))
        else:
            # Process category sections
            for section in category_sections:
                title_elem = section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if title_elem and tid in title_elem.get_text(strip=True):
                    # Found the category, extract videos
                    list_items = section.find_all('li')
                    for item in list_items:
                        all_videos.extend(self.extractVideosFromListItem(item))
                    
                    # If no list items, try to extract from links directly
                    if not list_items:
                        video_items = section.find_all('a', href=True)
                        for item in video_items:
                            video = self.extractVideoFromLink(item)
                            if video:
                                all_videos.append(video)
                    break
        
        # If no videos found in sections, try general extraction
        if not all_videos:
            all_videos = self.extractVideos(soup, category=tid, limit=100)
        
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
        
        # Try to find more information
        info = {}
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', html)
        if date_match:
            info['year'] = date_match.group(1)
        else:
            # Default to current year
            info['year'] = time.strftime("%Y", time.localtime())
        
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
        
        vod['vod_pic'] = img_url
        
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
            
            # Check if it's a list item with image
            list_item = link.find_parent('li')
            if list_item:
                videos = self.extractVideosFromListItem(list_item)
                if videos:
                    for video in videos:
                        if key in video.get('vod_name', ''):
                            # Avoid duplicates
                            if not any(r['vod_id'] == video['vod_id'] for r in results):
                                results.append(video)
            else:
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
        
        # First try to extract from the navigation menu if available
        nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=lambda x: x and ('nav' in x or 'menu' in x))
        for nav in nav_elements:
            links = nav.find_all('a')
            for link in links:
                text = link.get_text(strip=True)
                if text and len(text) < 15:  # Reasonable length for a category name
                    categories.append(text)
        
        # If no categories found from nav, try section headings
        if not categories:
            section_headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
            for heading in section_headings:
                text = heading.get_text(strip=True)
                if text and len(text) < 15:  # Reasonable length for a category name
                    categories.append(text)
        
        # If still no categories found, check for patterns in content
        if not categories:
            # Try to find category labels in the page structure
            possible_categories = ["推荐", "电视剧", "电影", "综艺", "动漫", "纪录片", "教育"]
            for category in possible_categories:
                if category in html:
                    categories.append(category)
        
        # If no categories found, use default ones
        if not categories:
            categories = ["推荐", "电视剧", "电影", "综艺", "动漫", "纪录片", "教育"]
        
        return categories
    
    def extractVideosFromListItem(self, list_item):
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
        
        # Extract date if available
        date_text = ''
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', list_item.get_text())
        if date_match:
            date_text = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        
        # Create video object
        videos.append({
            'vod_id': video_id,
            'vod_name': title,
            'vod_pic': img_url,
            'vod_remarks': date_text,
            'vod_year': date_match.group(1) if date_match else time.strftime("%Y", time.localtime())
        })
        
        return videos
    
    def extractVideoFromLink(self, link):
        """Extract video information from a link element"""
        if not link.has_attr('href'):
            return None
            
        # Extract video ID
        video_id = self.extract_id_from_url(link['href'])
        if not video_id:
            return None
            
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
        
        # Extract date if available
        date_text = ''
        parent_text = link.parent.get_text() if link.parent else ''
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', parent_text)
        if date_match:
            date_text = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        
        # Create video object
        return {
            'vod_id': video_id,
            'vod_name': title,
            'vod_pic': img_url,
            'vod_remarks': date_text,
            'vod_year': date_match.group(1) if date_match else time.strftime("%Y", time.localtime())
        }
    
    def extractVideos(self, soup, category=None, limit=None):
        """Extract videos from the HTML content"""
        videos = []
        
        # First try to extract from list items
        list_items = soup.find_all('li')
        for item in list_items:
            link = item.find('a', href=True)
            if link:
                # If category is specified, check if this item belongs to it
                if category:
                    # Look for category headings above this item
                    heading = None
                    for elem in item.previous_siblings:
                        if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            heading = elem
                            break
                    
                    if heading and category not in heading.get_text(strip=True):
                        continue
                
                # Extract videos from list item
                item_videos = self.extractVideosFromListItem(item)
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
                if video_id and any(v['vod_id'] == video_id for v in videos):
                    continue
                
                # Extract video from link
                video = self.extractVideoFromLink(link)
                if video:
                    # If category is specified, check if this item belongs to it
                    if category:
                        # Look for category headings above this link
                        heading = None
                        current = link
                        while current and heading is None:
                            for elem in current.previous_siblings:
                                if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                    heading = elem
                                    break
                            if heading:
                                break
                            current = current.parent
                        
                        if heading and category not in heading.get_text(strip=True):
                            continue
                    
                    videos.append(video)
                
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
