#!/usr/bin/env python3
# coding=utf-8
# Crawler for SuperZhuang (m.superzhuang.com)

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
        # Update headers for SuperZhuang API
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://m.superzhuang.com',
            'Referer': 'https://m.superzhuang.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Authorization-token': 'null',  # Based on the request headers in document 2
        }
        self.session.headers.update(self.headers)
        self.api_list_url = 'https://api.superzhuangplus.com/api/stayUser/plusDecorationContentList'
        # ContentType values should be determined from inspecting the actual API calls
        # For now using placeholders that should be replaced with actual values
        self.category_map = {
            'old_story': '22',    # Placeholder ID for 老房故事, replace with actual value
            'past_program': '23'  # Placeholder ID for 往期节目, replace with actual value
        }
        # Map internal IDs to display names
        self.category_names = {
            'old_story': '老房故事',
            'past_program': '往期节目'
        }
        # Detail API URL from document 2
        self.api_detail_url_template = "https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails?contentId={}"
        print("SuperZhuang Initialized")

    def getName(self):
        return "超级装"

    def isVideoFormat(self, url):
        # Basic check for common video extensions or known sources
        return url.endswith(('.mp4', '.m3u8', '.flv')) or 'v.qq.com' in url or 'aliyuncs.com' in url

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

        try:
            # Using the detail API from document 2
            detail_api_url = self.api_detail_url_template.format(vod_id)
            response = self.session.get(detail_api_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            detail_data = response.json()
            
            if detail_data.get('code') == 200 and 'data' in detail_data:
                item_detail = detail_data['data']
                # Extract the video URL - field names may need adjustment based on actual response
                play_url_actual = item_detail.get('playUrl') or item_detail.get('videoUrl') or item_detail.get('videoPlayUrl')
                title = item_detail.get('contentTitle', title_placeholder)
                img_url = item_detail.get('firstImg', '')
                desc = item_detail.get('contentText', '')
                remarks = item_detail.get('createTime', '')

                if not play_url_actual:
                    # Check if there's a video info object
                    video_info = item_detail.get('videoInfo') or {}
                    play_url_actual = video_info.get('url')

                if not play_url_actual:
                    print(f"Error: Video URL not found in detail API response for {vod_id}")
                    # Fall back to HTML parsing if API doesn't have the URL
                    return self._parse_detail_page(vod_id)

                play_url_formatted = f"{title}${play_url_actual}"

                vod = {
                    'vod_id': vod_id,
                    'vod_name': title,
                    'vod_pic': img_url,
                    'vod_remarks': remarks,
                    'vod_content': desc,
                    'vod_play_from': 'SuperZhuang',
                    'vod_play_url': play_url_formatted
                }
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

    def _parse_detail_page(self, vod_id):
        """Fallback method to parse the detail page HTML if API fails"""
        try:
            detail_page_url = f"https://m.superzhuang.com/detail/{vod_id}?type=video"
            print(f"Fetching detail page: {detail_page_url}")
            response = self.session.get(detail_page_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            # Look for video URL in script tags
            play_url_actual = None
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    # Look for common patterns of video URL in JavaScript
                    patterns = [
                        r'playUrl:\s*["\'](http[^"\']+)["\']',
                        r'videoUrl:\s*["\'](http[^"\']+)["\']',
                        r'video[Uu]rl\s*=\s*["\'](http[^"\']+)["\']',
                        r'video_url\s*=\s*["\'](http[^"\']+)["\']',
                        r'src:\s*["\'](http[^"\']+\.(?:mp4|m3u8))["\']'
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
                iframe = soup.find('iframe')
                if iframe and iframe.get('src'):
                    iframe_src = iframe['src']
                    if 'v.qq.com' in iframe_src or 'player' in iframe_src:
                        play_url_actual = iframe_src
                        print(f"Found iframe source: {play_url_actual}")

            # Look for video tag as last resort
            if not play_url_actual:
                video_tag = soup.find('video')
                if video_tag and video_tag.get('src'):
                    play_url_actual = video_tag['src']
                    print(f"Found video tag source: {play_url_actual}")

            if not play_url_actual:
                print(f"Error: Could not find video URL in detail page HTML for {vod_id}")
                return {'list': []}

            # Extract basic info from the page
            title = None
            title_tag = soup.find('h1') or soup.find('h2') or soup.find('title')
            if title_tag:
                title = title_tag.text.strip()
            if not title:
                title = soup.find('meta', {'property': 'og:title'})
                title = title['content'] if title else title_placeholder
                
            img_url = ""
            img_meta = soup.find('meta', {'property': 'og:image'})
            if img_meta and img_meta.get('content'):
                img_url = img_meta['content']
                
            desc = ""
            desc_meta = soup.find('meta', {'name': 'description'})
            if desc_meta and desc_meta.get('content'):
                desc = desc_meta['content']

            play_url_formatted = f"{title}${play_url_actual}"

            vod = {
                'vod_id': vod_id,
                'vod_name': title,
                'vod_pic': img_url,
                'vod_remarks': '',
                'vod_content': desc,
                'vod_play_from': 'SuperZhuang',
                'vod_play_url': play_url_formatted
            }
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
            
        # The 'id' passed here should be the actual video URL extracted by detailContent
        if not self.isVideoFormat(id):
            # Maybe it's an iframe URL or needs special handling
            if 'v.qq.com' in id:
                # For Tencent Videos, often parse=1 is needed for the app to handle it
                print("Handling Tencent Video URL")
                return {'parse': 1, 'url': id, 'header': self.headers}
            else:
                print(f"Unknown URL format for player: {id}")
                # Default to parse=1, let the app try to handle it
                return {'parse': 1, 'url': id, 'header': self.headers}

        # For direct MP4/M3U8
        return {'parse': 0, 'url': id, 'header': {
            'User-Agent': self.headers['User-Agent'],
            'Referer': 'https://m.superzhuang.com/'
        }}

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
            print(f"Response text that failed: {response.text[:500]}")  # Log part of the failing response
            self.total_rows = 0
            return []
        except Exception as e:
            print(f"Unexpected Error in fetch_videos_for_category {category_id}: {e}")
            self.total_rows = 0
            return []
