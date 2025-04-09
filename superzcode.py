#!/usr/bin/env python3
# coding=utf-8
# Spider for SuperZhuang using pre-compiled data and iframe extraction

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
    # URL to the raw text file containing video data
    data_source_url = 'https://raw.githubusercontent.com/boleechat/collect/refs/heads/main/superzhuang.txt'
    video_data = [] # Cache for parsed data
    data_loaded = False

    def init(self, extend=""):
        self.session = requests.Session()
        # !!! Use a Mobile User-Agent !!!
        mobile_user_agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1'
        self.headers = {
            'User-Agent': mobile_user_agent,
            # Accept header for fetching HTML detail pages
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://m.superzhuang.com/', # Referer might still be useful
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(self.headers)
        print("SuperZhuang Initialized (Data Source: GitHub TXT, Mobile UA)")

    def getName(self):
        return "超级装 (TXT源)" # Updated name

    def isVideoFormat(self, url):
        # Checks if the URL looks like the Tencent iframe
        return 'v.qq.com/txp/iframe/player.html' in url

    def manualVideoCheck(self):
        pass

    def destroy(self):
        self.session.close()
        print("SuperZhuang Destroyed")

    def load_data_from_github(self):
        """Fetches and parses the video data from the GitHub TXT file."""
        if self.data_loaded:
            return True
        print(f"Fetching data from {self.data_source_url}")
        try:
            # Use standard session headers initially, but User-Agent is important
            response = self.session.get(self.data_source_url, timeout=20)
            response.raise_for_status()
            response.encoding = 'utf-8' # Assume UTF-8 encoding
            lines = response.text.strip().split('\n')
            parsed_data = []
            for line in lines:
                parts = line.strip().split('\t') # Split by tab
                if len(parts) == 3:
                    detail_url, title, img_url = parts
                    if detail_url.startswith('http') and title and img_url.startswith('http'):
                         # Use the detail URL as the unique ID
                        parsed_data.append({
                            'vod_id': detail_url,
                            'vod_name': title,
                            'vod_pic': img_url,
                            'vod_remarks': '点击查看详情' # Simple remark
                        })
                    else:
                        print(f"Skipping invalid line: {line}")
                else:
                    print(f"Skipping line with incorrect format: {line}")

            self.video_data = parsed_data
            self.data_loaded = True
            print(f"Loaded {len(self.video_data)} items from GitHub.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from GitHub: {e}")
            self.data_loaded = False
            return False
        except Exception as e:
            print(f"Error parsing data from GitHub: {e}")
            self.data_loaded = False
            return False

    def homeContent(self, filter):
        """Provide categories (only one in this case)."""
        if not self.load_data_from_github():
             return {'class': [], 'filters': {}} # Return empty if data load fails

        result = {}
        # Single category
        classes = [{'type_name': "全部视频", 'type_id': "all"}]
        filters = {}
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        """Get initial videos for the home page."""
        if not self.load_data_from_github():
            return {'list': []}
        # Return the first page of videos (e.g., 20 items)
        limit = 20
        return {'list': self.video_data[:limit]}

    def categoryContent(self, tid, pg, filter, extend):
        """Get videos for the 'all' category with pagination."""
        if not self.load_data_from_github():
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 20, 'total': 0}

        if tid != "all": # Should only be 'all'
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 20, 'total': 0}

        try:
            pg = int(pg)
        except:
            pg = 1

        page_size = 20 # Videos per page
        total_videos = len(self.video_data)
        total_pages = max(1, (total_videos + page_size - 1) // page_size)
        pg = min(pg, total_pages) # Ensure page number is valid

        start_idx = (pg - 1) * page_size
        end_idx = start_idx + page_size

        paginated_list = self.video_data[start_idx:end_idx]

        result = {
            'list': paginated_list,
            'page': pg,
            'pagecount': total_pages,
            'limit': page_size,
            'total': total_videos
        }
        return result

    def detailContent(self, ids):
        """Fetch detail page, find iframe src, return details for playback."""
        if not ids:
            return {'list': []}

        detail_page_url = ids[0] # The ID is the detail page URL
        print(f"Fetching details for URL: {detail_page_url}")

        # Find the original item data (title, pic) from our loaded list
        original_item = next((item for item in self.video_data if item['vod_id'] == detail_page_url), None)
        if not original_item:
             print(f"Error: Could not find original item for ID {detail_page_url} in loaded data.")
             # Fallback: Try to scrape title from page, use placeholder image
             original_item = {'vod_name': '加载中...', 'vod_pic': ''}


        try:
            # Fetch the detail page HTML using the mobile User-Agent
            response = self.session.get(detail_page_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding # Try to detect encoding
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find the Tencent iframe
            iframe_tag = soup.find('iframe', {'src': re.compile(r'v\.qq\.com/txp/iframe/player\.html\?vid=')})

            if iframe_tag and 'src' in iframe_tag.attrs:
                iframe_url = iframe_tag['src']
                # Ensure the URL has a scheme (http/https)
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                elif not iframe_url.startswith('http'):
                    # Try to resolve relative URL (less likely for cross-domain iframe)
                    iframe_url = urljoin(detail_page_url, iframe_url)

                print(f"Found iframe src: {iframe_url}")

                # Try to get a better title from the page if possible
                page_title_tag = soup.find('title')
                title = page_title_tag.text.strip() if page_title_tag else original_item['vod_name']

                # Try to get description
                desc_tag = soup.find('meta', attrs={'name': 'description'})
                desc = desc_tag['content'].strip() if desc_tag and 'content' in desc_tag.attrs else title

                # Construct the play URL in 'Name$URL' format for TVBox
                play_url_formatted = f"{title}${iframe_url}"

                vod = {
                    'vod_id': detail_page_url, # Keep the original detail page URL as ID
                    'vod_name': title,
                    'vod_pic': original_item['vod_pic'], # Use image from the TXT file
                    'vod_remarks': '来源: 腾讯视频', # Update remarks
                    'vod_content': desc,
                    'vod_play_from': 'SuperZhuang',
                    'vod_play_url': play_url_formatted
                }
                return {'list': [vod]}
            else:
                print(f"Error: Could not find Tencent iframe in detail page: {detail_page_url}")
                return {'list': []}

        except requests.exceptions.RequestException as e:
            print(f"Error fetching detail page {detail_page_url}: {e}")
        except Exception as e:
            print(f"Unexpected error processing detail page {detail_page_url}: {e}")

        # Fallback if error occurs
        return {'list': [{'vod_name': f"无法加载详情 - {original_item['vod_name']}", 'vod_play_from': 'SuperZhuang', 'vod_play_url': f"无效${detail_page_url}"}]}


    def searchContent(self, key, quick, pg="1"):
        """Basic search within the loaded data."""
        if not self.load_data_from_github():
            return {'list': []}

        results = []
        for item in self.video_data:
            if key.lower() in item['vod_name'].lower():
                results.append(item)

        # Simple pagination for search results (optional)
        page_size = 20
        total_results = len(results)
        total_pages = max(1, (total_results + page_size - 1) // page_size)
        try:
            pg = int(pg)
        except:
            pg = 1
        pg = min(pg, total_pages)
        start_idx = (pg - 1) * page_size
        end_idx = start_idx + page_size

        return {'list': results[start_idx:end_idx], 'page': pg, 'pagecount': total_pages, 'limit': page_size, 'total': total_results}

    def playerContent(self, flag, id, vipFlags):
        """Instruct TVBox to handle the iframe URL."""
        # 'id' here is the iframe_url extracted by detailContent
        print(f"PlayerContent called with iframe URL: {id}")
        if not self.isVideoFormat(id):
             print(f"Warning: URL passed to playerContent is not the expected iframe URL: {id}")
             return {'parse': 0, 'url': ''} # Return empty if URL is invalid

        # Tell TVBox player to parse/handle the iframe source URL directly
        # Pass mobile User-Agent header as it might be needed by the player when resolving the iframe
        return {'parse': 1, 'url': id, 'header': self.headers}

    def localProxy(self, param):
        return param