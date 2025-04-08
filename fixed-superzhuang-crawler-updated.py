#!/usr/bin/env python3
# coding=utf-8
# Crawler for SuperZhuang (m.superzhuang.com)

import json
import sys
import re
import time
from urllib.parse import urljoin, quote, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.session = requests.Session()
        # Update headers for SuperZhuang API
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://m.superzhuang.com',
            'Referer': 'https://m.superzhuang.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Authorization-token': 'null',
        }
        self.session.headers.update(self.headers)
        self.api_list_url = 'https://api.superzhuangplus.com/api/stayUser/plusDecorationContentList'
        # ContentType values
        self.category_map = {
            'old_story': '22',    # 老房故事
            'past_program': '23'  # 往期节目
        }
        # Map internal IDs to display names
        self.category_names = {
            'old_story': '老房故事',
            'past_program': '往期节目'
        }
        # Detail API URL - UPDATED based on F12 data
        self.api_detail_url_template = "https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails?contentId={}"
        # Track cache of video URLs to improve performance
        self.video_url_cache = {}
        print("SuperZhuang Initialized")

    def getName(self):
        return "超级装"

    def isVideoFormat(self, url):
        # Basic check for common video extensions or known sources
        return url.endswith(('.mp4', '.m3u8', '.flv')) or 'qq.com' in url or 'aliyuncs.com' in url

    def manualVideoCheck(self):
        pass

    def destroy(self):
        self.session.close()
        print("SuperZhuang Destroyed")

    # Base Configuration
    host = 'https://m.superzhuang.com'

    def homeContent(self, filter):
        """Generate content for home page with specified categories"""
        result = {}
        classes = []
        for type_id, type_name in self.category_names.items():
             classes.append({'type_name': type_name, 'type_id': type_id})

        filters = {}  # No filters needed for now
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        """Get videos for the home page (using the first category as default)"""
        default_category_id = list(self.category_map.keys())[0]  # Use first category ID
        videos = self.fetch_videos_for_category(default_category_id, 1, limit=20)  # Fetch first page, limit items
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for a specific category"""
        if not pg:
            pg = 1
        else:
            pg = int(pg)

        # Fetch videos for the selected category and page
        videos = self.fetch_videos_for_category(tid, pg)
        total_videos = self.total_rows  # Get total count from the last API call
        page_size = 10  # As seen in the API response

        # Calculate total pages
        total_pages = (total_videos + page_size - 1) // page_size

        result = {
            'list': videos,
            'page': pg,
            'pagecount': total_pages,
            'limit': page_size,
            'total': total_videos
        }
        return result

    def detailContent(self, ids):
        """Get details for a specific video, including the actual play URL."""
        if not ids:
            return {'list': []}

        vod_id = ids[0]  # The ID comes from the list API (item['id'])
        title_placeholder = f"视频 {vod_id}"  # Placeholder title if detail fetch fails

        print(f"Fetching details for vod_id: {vod_id}")
        
        # Check if we already have this URL cached
        if vod_id in self.video_url_cache:
            cached_vod = self.video_url_cache[vod_id]
            print(f"Using cached video data for {vod_id}")
            return {'list': [cached_vod]}

        try:
            # First try the API method with the updated URL from F12 data
            detail_api_url = self.api_detail_url_template.format(vod_id)
            print(f"Fetching detail API: {detail_api_url}")
            
            response = self.session.get(detail_api_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            detail_data = response.json()
            
            if detail_data.get('code') == 200 and 'data' in detail_data:
                item_detail = detail_data['data']
                
                # Extract fields
                title = item_detail.get('contentTitle', title_placeholder)
                img_url = item_detail.get('firstImg', '')
                desc = item_detail.get('contentText', '')
                remarks = item_detail.get('createTime', '')
                
                # Look for video URL in different locations
                play_url_actual = None
                
                # NEW: Look for video links in buryUrl (per F12 data)
                bury_info = item_detail.get('buryInfo', {})
                if bury_info and isinstance(bury_info, dict):
                    bury_url = bury_info.get('buryUrl', '')
                    if bury_url and 'contentId=' in bury_url:
                        print(f"Found buryUrl: {bury_url}")
                        # Extract contentId from buryUrl, which might be useful
                        try:
                            parsed_url = urlparse(bury_url)
                            content_id_from_bury = parse_qs(parsed_url.query).get('contentId', [''])[0]
                            if content_id_from_bury:
                                print(f"Found contentId in buryUrl: {content_id_from_bury}")
                                # This could be used to fetch video details if needed
                        except:
                            pass
                
                # Look for direct video fields in content data
                video_fields = ['playUrl', 'videoUrl', 'videoPlayUrl', 'url', 'mediaUrl', 'videoMediaUrl']
                for field in video_fields:
                    if field in item_detail and item_detail[field]:
                        play_url_actual = item_detail[field]
                        print(f"Found video URL in field {field}: {play_url_actual}")
                        break
                
                # Check video info object if available
                if not play_url_actual:
                    video_info = item_detail.get('videoInfo') or {}
                    if isinstance(video_info, dict):
                        for field in video_fields:
                            if field in video_info and video_info[field]:
                                play_url_actual = video_info[field]
                                print(f"Found video URL in videoInfo.{field}: {play_url_actual}")
                                break
                
                # Check for Tencent URLs specifically (as seen in F12 data)
                if not play_url_actual:
                    # Look for qq video URLs in content text
                    content_text = item_detail.get('contentText', '')
                    if content_text:
                        qq_patterns = [
                            r'(https?://[^\s"\'<>]+\.qq\.com[^\s"\'<>]*)',
                            r'(https?://apd-vlive\.apdcdn\.tc\.qq\.com[^\s"\'<>]*)',
                            r'(https?://[^\s"\'<>]+\.mp4\?sdtfrom=v[^\s"\'<>]*)'
                        ]
                        for pattern in qq_patterns:
                            matches = re.findall(pattern, content_text)
                            if matches:
                                play_url_actual = matches[0]
                                print(f"Found Tencent video URL in content: {play_url_actual}")
                                break
                
                # If still no URL found, check for iframe or video tags in content
                if not play_url_actual and '<' in content_text:
                    soup = BeautifulSoup(content_text, 'html.parser')
                    # Check for iframe
                    iframe = soup.find('iframe')
                    if iframe and iframe.get('src'):
                        iframe_src = iframe['src']
                        play_url_actual = iframe_src
                        print(f"Found iframe URL in content: {play_url_actual}")
                    
                    # Check for video tag
                    if not play_url_actual:
                        video = soup.find('video')
                        if video:
                            if video.get('src'):
                                play_url_actual = video['src']
                                print(f"Found video tag source: {play_url_actual}")
                            elif video.find('source'):
                                source = video.find('source')
                                if source.get('src'):
                                    play_url_actual = source['src']
                                    print(f"Found video source tag: {play_url_actual}")
                
                # If API method fails, try fetching the actual detail page from web
                if not play_url_actual:
                    print("API method didn't find video URL, trying web page method")
                    web_result = self._fetch_video_from_webpage(vod_id)
                    if web_result:
                        play_url_actual = web_result
                        print(f"Found video URL from webpage: {play_url_actual}")
                
                if not play_url_actual:
                    print(f"Error: Could not find any video URL for {vod_id}")
                    play_url_actual = "无效"  # Mark as invalid
                
                # Package the video information
                vod = {
                    'vod_id': vod_id,
                    'vod_name': title,
                    'vod_pic': img_url,
                    'vod_remarks': remarks,
                    'vod_content': desc,
                    'vod_play_from': 'SuperZhuang',
                    'vod_play_url': f"{title}${play_url_actual}"
                }
                
                # Cache the result
                self.video_url_cache[vod_id] = vod
                return {'list': [vod]}
            else:
                print(f"Error: Detail API did not return success or data for {vod_id}")
                # Fall back to HTML parsing
                return self._parse_detail_page(vod_id)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching details for {vod_id}: {e}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for detail API {vod_id}: {e}")
        except Exception as e:
            print(f"Unexpected error in detailContent for {vod_id}: {e}")

        # Try the HTML parsing method as fallback
        return self._parse_detail_page(vod_id)

    def _fetch_video_from_webpage(self, vod_id):
        """NEW METHOD: Directly access the webpage to find video URL using F12 insights"""
        try:
            # Use the same URL format seen in F12 data
            page_url = f"https://m.superzhuang.com/programme?contentId={vod_id}"
            print(f"Fetching programme page: {page_url}")
            
            response = self.session.get(page_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            html_content = response.text
            
            # Look specifically for Tencent video URLs as seen in F12 data
            tencent_patterns = [
                r'(https?://apd-vlive\.apdcdn\.tc\.qq\.com[^"\'<>\s]+\.mp4[^"\'<>\s]*)',
                r'(https?://[^"\'<>\s]+\.qqvideo\.tc\.qq\.com[^"\'<>\s]+\.mp4[^"\'<>\s]*)',
                r'(https?://[^"\'<>\s]+\.mp4\?sdtfrom=v[^"\'<>\s]*)'
            ]
            
            for pattern in tencent_patterns:
                matches = re.findall(pattern, html_content)
                if matches:
                    return matches[0]
            
            # Also check for any embedded iframes with video sources
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for iframes (common for Tencent embeds)
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                if iframe.get('src') and ('v.qq.com' in iframe['src'] or 'video' in iframe['src']):
                    return iframe['src']
            
            # Look for HTML5 video elements
            videos = soup.find_all('video')
            for video in videos:
                if video.get('src'):
                    return video['src']
                # Check for source elements within video
                sources = video.find_all('source')
                for source in sources:
                    if source.get('src'):
                        return source['src']
            
            # Look for video.js or other players
            video_players = soup.find_all('div', class_=lambda c: c and ('video-js' in c or 'player' in c))
            for player in video_players:
                data_attrs = [attr for attr in player.attrs if attr.startswith('data-') and 'url' in attr]
                for attr in data_attrs:
                    if player[attr] and player[attr].startswith('http'):
                        return player[attr]
            
            # Check for script content with video URLs
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for JSON objects containing video URLs
                    data_patterns = [
                        r'videoInfo\s*[=:]\s*(\{[^;]+\})',
                        r'videoData\s*[=:]\s*(\{[^;]+\})',
                        r'player\s*[=:]\s*(\{[^;]+\})'
                    ]
                    for pattern in data_patterns:
                        match = re.search(pattern, script.string)
                        if match:
                            try:
                                json_str = match.group(1)
                                # Clean up the JSON string for parsing
                                json_str = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', json_str)
                                data = json.loads(json_str)
                                
                                # Look for video URLs in the data
                                for key in ['url', 'playUrl', 'videoUrl', 'src', 'source']:
                                    if key in data and isinstance(data[key], str) and data[key].startswith('http'):
                                        return data[key]
                            except:
                                pass
                    
                    # Also check for direct URL assignments
                    url_patterns = [
                        r'videoUrl\s*[=:]\s*[\'"]([^\'"]+(\.mp4|\.m3u8)[^\'"]*)[\'"]',
                        r'playUrl\s*[=:]\s*[\'"]([^\'"]+(\.mp4|\.m3u8)[^\'"]*)[\'"]',
                        r'src\s*[=:]\s*[\'"]([^\'"]+(\.mp4|\.m3u8)[^\'"]*)[\'"]'
                    ]
                    for pattern in url_patterns:
                        match = re.search(pattern, script.string)
                        if match:
                            return match.group(1)
            
            return None
            
        except Exception as e:
            print(f"Error in _fetch_video_from_webpage: {e}")
            return None

    def _parse_detail_page(self, vod_id):
        """Fallback method to parse the detail page HTML if API fails"""
        try:
            # Try first with the programme URL format from F12 data
            detail_page_url = f"https://m.superzhuang.com/programme?contentId={vod_id}"
            print(f"Fetching detail page: {detail_page_url}")
            
            response = self.session.get(detail_page_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            html_content = response.text
            
            # If the page seems empty or redirects, try the old URL format
            if len(html_content) < 1000 or "404" in html_content:
                detail_page_url = f"https://m.superzhuang.com/detail/{vod_id}?type=video"
                print(f"First URL failed, trying alternate detail page: {detail_page_url}")
                response = self.session.get(detail_page_url, headers=self.headers, timeout=15)
                response.raise_for_status()
                html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')

            # Look for video URL in script tags or media elements
            play_url_actual = None
            
            # Check for Tencent video URLs specifically (as seen in F12 data)
            tencent_patterns = [
                r'(https?://apd-vlive\.apdcdn\.tc\.qq\.com[^\s"\'<>]+\.mp4[^\s"\'<>]*)',
                r'(https?://[^\s"\'<>]+\.qqvideo\.tc\.qq\.com[^\s"\'<>]+\.mp4[^\s"\'<>]*)',
                r'(https?://[^\s"\'<>]+\.mp4\?sdtfrom=v[^\s"\'<>]*)'
            ]
            
            for pattern in tencent_patterns:
                matches = re.findall(pattern, html_content)
                if matches:
                    play_url_actual = matches[0]
                    print(f"Found Tencent video URL: {play_url_actual}")
                    break
            
            # If no Tencent URL found, look in script tags for more general patterns
            if not play_url_actual:
                script_tags = soup.find_all('script')
                for script in script_tags:
                    if script.string:
                        # Look for common patterns of video URL in JavaScript
                        patterns = [
                            r'playUrl\s*=\s*["\'](http[^"\']+)["\']',
                            r'playUrl:\s*["\'](http[^"\']+)["\']',
                            r'videoUrl:\s*["\'](http[^"\']+)["\']',
                            r'video[Uu]rl\s*=\s*["\'](http[^"\']+)["\']',
                            r'video_url\s*=\s*["\'](http[^"\']+)["\']',
                            r'src:\s*["\'](http[^"\']+\.(?:mp4|m3u8))["\']',
                            r'"url"\s*:\s*"(http[^"]+\.(?:mp4|m3u8)[^"]*)"',
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, script.string)
                            if match:
                                play_url_actual = match.group(1)
                                print(f"Found video URL in script: {play_url_actual}")
                                break
                        
                        if play_url_actual:
                            break
            
            # Look for iframe (e.g., Tencent Video embed)
            if not play_url_actual:
                iframes = soup.find_all('iframe')
                for iframe in iframes:
                    if iframe.get('src'):
                        iframe_src = iframe['src']
                        if 'v.qq.com' in iframe_src or 'player' in iframe_src:
                            play_url_actual = iframe_src
                            print(f"Found iframe source: {play_url_actual}")
                            break

            # Look for video tags
            if not play_url_actual:
                videos = soup.find_all('video')
                for video in videos:
                    if video.get('src'):
                        play_url_actual = video['src']
                        print(f"Found video tag source: {play_url_actual}")
                        break
                    
                    sources = video.find_all('source')
                    for source in sources:
                        if source.get('src'):
                            play_url_actual = source['src']
                            print(f"Found video source tag: {play_url_actual}")
                            break
                    
                    if play_url_actual:
                        break

            if not play_url_actual:
                print(f"Error: Could not find video URL in detail page HTML for {vod_id}")
                play_url_actual = "无效"  # Mark as invalid so playerContent can handle it

            # Extract basic info from the page
            title = None
            # Try different tag types for title
            for tag_selector in ['h1', 'h2', '.title', '.video-title', '[class*="title"]']:
                title_tag = soup.select_one(tag_selector)
                if title_tag:
                    title = title_tag.text.strip()
                    break
                    
            # Fallback to meta tags for title
            if not title:
                title_meta = soup.find('meta', {'property': 'og:title'}) or soup.find('meta', {'name': 'title'})
                if title_meta and title_meta.get('content'):
                    title = title_meta['content'].strip()
                    
            # Final fallback to page title
            if not title:
                title_tag = soup.find('title')
                title = title_tag.text.strip() if title_tag else f"视频 {vod_id}"
                
            # Extract image URL
            img_url = ""
            img_selectors = ['.video-cover img', '.cover img', '.thumbnail img', '[class*="cover"] img', '[class*="thumbnail"] img']
            for selector in img_selectors:
                img_tag = soup.select_one(selector)
                if img_tag and img_tag.get('src'):
                    img_url = img_tag['src']
                    break
                    
            # Fallback to meta image
            if not img_url:
                img_meta = soup.find('meta', {'property': 'og:image'}) or soup.find('meta', {'name': 'thumbnail'})
                if img_meta and img_meta.get('content'):
                    img_url = img_meta['content']
                
            # Extract description
            desc = ""
            desc_selectors = ['.description', '.summary', '.content', '[class*="description"]', '[class*="content"]']
            for selector in desc_selectors:
                desc_tag = soup.select_one(selector)
                if desc_tag:
                    desc = desc_tag.text.strip()
                    break
                    
            # Fallback to meta description
            if not desc:
                desc_meta = soup.find('meta', {'property': 'og:description'}) or soup.find('meta', {'name': 'description'})
                if desc_meta and desc_meta.get('content'):
                    desc = desc_meta['content']

            # Format results
            vod = {
                'vod_id': vod_id,
                'vod_name': title,
                'vod_pic': img_url,
                'vod_remarks': '',
                'vod_content': desc,
                'vod_play_from': 'SuperZhuang',
                'vod_play_url': f"{title}${play_url_actual}"
            }
            
            # Cache the result
            self.video_url_cache[vod_id] = vod
            print(f"Detail Found: {vod['vod_name']} - URL: {play_url_actual}")
            return {'list': [vod]}

        except Exception as e:
            print(f"Error in _parse_detail_page for {vod_id}: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """Search - Not implemented as there's no direct search API found yet."""
        print("Search function is not implemented for SuperZhuang.")
        return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        """Get playback information - id here is the actual video URL"""
        print(f"PlayerContent called with URL: {id}")
        
        if not id or id == "无效":
            return {'code': 404, 'msg': '视频地址解析失败'}
        
        # Clean the URL - remove any leading/trailing quotes or spaces
        id = id.strip('"\'').strip()
        
        # Rewrite any relative URLs to absolute
        if id.startswith('/'):
            id = f"https://m.superzhuang.com{id}"
        elif not id.startswith(('http://', 'https://')):
            id = f"https://{id}"
        
        # Handle special cases for Tencent Videos
        if 'qq.com' in id or 'qqvideo' in id or 'apd-vlive' in id:
            # Tencent Video needs specific handling
            # Preserve all parameters for proper playback
            print(f"Processing Tencent video URL: {id}")
            return {
                'parse': 0,  # Try direct play first for Tencent URLs from F12 logs
                'url': id,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': 'https://m.superzhuang.com/'
                }
            }
        elif 'v.qq.com' in id:
            # For v.qq.com URLs, use the parser
            print(f"Processing v.qq.com URL: {id}")
            return {
                'parse': 1,
                'jx': 1,
                'url': id,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': 'https://m.superzhuang.com/'
                }
            }
        elif id.endswith(('.mp4', '.m3u8', '.flv')):
            # Direct media URLs
            print(f"Direct media URL: {id}")
            return {
                'parse': 0,
                'url': id,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': 'https://m.superzhuang.com/'
                }
            }
        else:
            # Unknown format, try with parsing
            print(f"Unknown URL format - trying with parse=1: {id}")
            return {
                'parse': 1,
                'url': id,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': 'https://m.superzhuang.com/'
                }
            }

    def localProxy(self, param):
        # Not typically needed unless manipulating requests/responses locally
        return param

    # Helper methods
    def fetch_videos_for_category(self, category_id, page_num, limit=None):
        """Fetch videos for a specific category using the API"""
        if category_id not in self.category_map:
            print(f"Error: Unknown category_id: {category_id}")
            return []

        content_type = self.category_map[category_id]
        page_size = 10  # Default page size from observed API

        payload = {
            "areaId": "",
            "contentSort": "",
            "contentType": content_type,  # Use the mapped ID
            "contentTags": "",
            "createTime": "",
            "dataFlag": 1,  # Seems constant from web interaction
            "decorationBudget": "",
            "designerId": "",
            "floorSpace": "",
            "houseLayout": "",
            "houseStyle": "",
            "id": "",
            "labelId": "",
            "likeCountSort": "",
            "merchantId": "",
            "pageNum": page_num,
            "pageSize": page_size,
            "sort": "",
            "sortDirection": "",
            "updateTime": ""
        }

        videos = []
        try:
            print(f"Fetching category: {self.category_names.get(category_id, category_id)}, Page: {page_num}")
            
            response = self.session.post(self.api_list_url, json=payload, headers=self.headers, timeout=15)
            response.raise_for_status()
            response_json = response.json()

            if response_json.get('code') == 200 and 'data' in response_json and 'data' in response_json['data']:
                items = response_json['data']['data']
                self.total_rows = int(response_json['data'].get('totalRows', 0))  # Store total count

                for item in items:
                    vod_id = item.get('id')
                    title = item.get('contentTitle', '无标题')
                    img_url = item.get('firstImg', '')
                    # Handle potential missing images gracefully
                    if not img_url or not img_url.startswith('http'):
                        img_url = ''  # Or provide a default placeholder image URL

                    create_time = item.get('createTime', '')  # Use as remarks

                    video_item = {
                        'vod_id': vod_id,
                        'vod_name': title,
                        'vod_pic': img_url,
                        'vod_remarks': create_time,  # Show creation time as remark
                    }
                    videos.append(video_item)

                print(f"Fetched {len(videos)} items for {self.category_names.get(category_id, category_id)} page {page_num}.")
                if limit:
                    return videos[:limit]
                return videos
            else:
                print(f"API Error: Code {response_json.get('code')}, Message: {response_json.get('message')}")
                self.total_rows = 0
                return []

        except requests.exceptions.RequestException as e:
            print(f"Network Error fetching category {category_id}: {e}")
            self.total_rows = 0
            return []
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error fetching category {category_id}: {e}")
            print(f"Response text