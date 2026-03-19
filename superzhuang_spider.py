#!/usr/bin/env python3
# coding=utf-8
# 超级装 视频爬虫 for TVBox
# 网站: https://m.superzhuang.com/owner?typecode=video

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
        self.session.headers.update(self.headers)
        print("SuperZhuang spider initialized")
        return

    def getName(self):
        return "SuperZhuang"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        self.session.close()

    # ─── 基础配置 ────────────────────────────────────────────────
    host = 'https://m.superzhuang.com'

    # 分类定义：对应网站 Tab
    categories = [
        {'type_id': 'video',    'type_name': '往期节目'},
        {'type_id': 'case',     'type_name': '精选案例'},
        {'type_id': 'strategy', 'type_name': '装修攻略'},
        {'type_id': 'story',    'type_name': '老房故事'},
    ]

    # typecode → API 参数映射（根据实际接口调整）
    type_map = {
        'video':    'video',
        'case':     'case',
        'strategy': 'strategy',
        'story':    'story',
    }

    # 列表 API（手机端）
    list_api = 'https://m.superzhuang.com/owner?typecode={typecode}&page={page}'

    # 内容详情页
    detail_url = 'https://m.superzhuang.com/programme?contentId={content_id}'

    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
                      'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                      'Version/16.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.superzhuang.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    page_size = 20

    # ─── 首页 ────────────────────────────────────────────────────
    def homeContent(self, filter):
        result = {}
        result['class'] = self.categories
        result['filters'] = {}
        return result

    def homeVideoContent(self):
        videos = self._fetch_list('video', 1)
        return {'list': videos}

    # ─── 分类内容 ─────────────────────────────────────────────────
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1
        typecode = self.type_map.get(tid, 'video')
        videos = self._fetch_list(typecode, pg)

        result = {
            'list': videos,
            'page': pg,
            'pagecount': 999,   # 网站未暴露总数，设置较大值
            'limit': self.page_size,
            'total': 999,
        }
        return result

    # ─── 详情 ─────────────────────────────────────────────────────
    def detailContent(self, ids):
        if not ids:
            return {'list': []}

        vid = ids[0]  # 格式: contentId
        detail_page = self.detail_url.format(content_id=vid)

        try:
            resp = self.session.get(detail_page, headers=self.headers, timeout=15)
            resp.raise_for_status()
            html = resp.text

            soup = BeautifulSoup(html, 'html.parser')

            # 尝试获取标题
            title = ''
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True).replace(' - 超级装', '').strip()

            # 尝试获取描述
            desc = ''
            desc_tag = soup.find('meta', {'name': 'description'})
            if desc_tag:
                desc = desc_tag.get('content', '')

            # 尝试获取封面图
            img = ''
            og_img = soup.find('meta', {'property': 'og:image'})
            if og_img:
                img = og_img.get('content', '')

            # 从页面脚本中提取腾讯视频 vid
            tx_vid = self._extract_tx_vid(html)

            if tx_vid:
                # 通过腾讯视频API获取真实播放地址
                play_url = self._resolve_tencent_video(tx_vid)
            else:
                # 备用：直接返回详情页给解析器处理
                play_url = detail_page

            vod = {
                'vod_id': vid,
                'vod_name': title or f'视频 {vid}',
                'vod_pic': img,
                'vod_content': desc,
                'vod_remarks': '',
                'vod_play_from': 'SuperZhuang',
                'vod_play_url': f'{title or vid}${play_url}',
            }

            return {'list': [vod]}

        except Exception as e:
            print(f"[detailContent] Error: {e}")
            return {'list': [{
                'vod_id': vid,
                'vod_name': vid,
                'vod_play_from': 'SuperZhuang',
                'vod_play_url': f'视频${detail_page}',
            }]}

    # ─── 搜索 ─────────────────────────────────────────────────────
    def searchContent(self, key, quick, pg="1"):
        # 网站未提供搜索API，在已抓取内容中本地过滤
        results = []
        for cat in self.type_map.keys():
            videos = self._fetch_list(cat, 1)
            for v in videos:
                if key.lower() in v.get('vod_name', '').lower():
                    results.append(v)
        return {'list': results, 'page': 1, 'pagecount': 1, 'limit': 50, 'total': len(results)}

    # ─── 播放 ─────────────────────────────────────────────────────
    def playerContent(self, flag, id, vipFlags):
        """
        id 可能是:
          1. 直接 mp4 URL (已解析好)
          2. 腾讯视频详情页 URL → 需要再次解析
          3. 腾讯视频 vid → 调用API解析
        """
        if id.endswith('.mp4') or 'smtcdns.com' in id or 'qqvideo' in id:
            # 已经是真实 mp4 地址
            return {
                'parse': 0,
                'url': id,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': 'https://v.qq.com/',
                }
            }

        if 'm.superzhuang.com/programme' in id:
            # 详情页，需解析
            try:
                resp = self.session.get(id, headers=self.headers, timeout=15)
                html = resp.text
                tx_vid = self._extract_tx_vid(html)
                if tx_vid:
                    real_url = self._resolve_tencent_video(tx_vid)
                    if real_url:
                        return {
                            'parse': 0,
                            'url': real_url,
                            'header': {
                                'User-Agent': self.headers['User-Agent'],
                                'Referer': 'https://v.qq.com/',
                            }
                        }
            except Exception as e:
                print(f"[playerContent] resolve error: {e}")

        # 兜底：交给TVBox解析器处理
        return {'parse': 1, 'url': id, 'header': self.headers}

    def localProxy(self, param):
        return param

    # ─── 内部方法 ─────────────────────────────────────────────────
    def _fetch_list(self, typecode, page):
        """抓取列表页，解析视频卡片"""
        url = self.list_api.format(typecode=typecode, page=page)
        videos = []

        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')

            # ── 方案1: 从 __NUXT__ 或 window.__INITIAL_STATE__ 等 JS 变量提取 JSON ──
            videos = self._parse_from_script(html)
            if videos:
                return videos

            # ── 方案2: 直接解析 HTML 卡片 ──
            videos = self._parse_from_html(soup, typecode)

        except Exception as e:
            print(f"[_fetch_list] Error fetching {url}: {e}")

        return videos

    def _parse_from_script(self, html):
        """从页面内联 JS 数据提取视频列表"""
        videos = []

        # 尝试提取 Nuxt.js 的 __NUXT__ 数据
        patterns = [
            r'window\.__NUXT__\s*=\s*(\{.*?\});?\s*</script>',
            r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*</script>',
            r'"contentList"\s*:\s*(\[.*?\])',
            r'"list"\s*:\s*(\[.*?\])',
        ]

        for pat in patterns:
            match = re.search(pat, html, re.DOTALL)
            if match:
                try:
                    raw = match.group(1)
                    data = json.loads(raw)
                    # 递归查找含 contentId 的列表
                    items = self._find_content_list(data)
                    if items:
                        for item in items:
                            v = self._parse_item(item)
                            if v:
                                videos.append(v)
                        if videos:
                            return videos
                except Exception as e:
                    print(f"[_parse_from_script] JSON parse error: {e}")
                    continue

        return videos

    def _find_content_list(self, data, depth=0):
        """递归查找包含 contentId 的列表"""
        if depth > 8:
            return []

        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict) and (
                'contentId' in data[0] or 'content_id' in data[0] or 'id' in data[0]
            ):
                return data

        if isinstance(data, dict):
            for key in ['contentList', 'list', 'data', 'result', 'items', 'records']:
                if key in data:
                    result = self._find_content_list(data[key], depth + 1)
                    if result:
                        return result

        return []

    def _parse_item(self, item):
        """将 JSON item 转换为 TVBox vod 格式"""
        if not isinstance(item, dict):
            return None

        # 尝试多种字段名
        content_id = (item.get('contentId') or item.get('content_id') or
                      item.get('id') or item.get('articleId') or '')
        if not content_id:
            return None

        title = (item.get('title') or item.get('name') or
                 item.get('contentTitle') or f'视频 {content_id}')

        # 封面图
        cover = (item.get('coverImg') or item.get('cover') or
                 item.get('thumbnail') or item.get('imgUrl') or
                 item.get('coverUrl') or '')

        # 取第一张图（有时是列表）
        if isinstance(cover, list) and cover:
            cover = cover[0]

        desc = (item.get('description') or item.get('desc') or
                item.get('summary') or '')

        remarks = item.get('publishTime') or item.get('createTime') or ''
        if remarks and len(str(remarks)) == 13:
            # 毫秒时间戳
            try:
                from datetime import datetime
                remarks = datetime.fromtimestamp(int(remarks) / 1000).strftime('%Y-%m-%d')
            except:
                pass

        return {
            'vod_id': str(content_id),
            'vod_name': str(title),
            'vod_pic': str(cover),
            'vod_content': str(desc),
            'vod_remarks': str(remarks),
        }

    def _parse_from_html(self, soup, typecode):
        """直接解析 HTML 中的视频卡片（备用方案）"""
        videos = []

        # 常见的卡片选择器
        card_selectors = [
            'a[href*="contentId"]',
            'a[href*="programme"]',
            '.video-item',
            '.content-item',
            '.card-item',
            'li[data-id]',
            '.item-card',
        ]

        cards = []
        for sel in card_selectors:
            cards = soup.select(sel)
            if cards:
                break

        for card in cards:
            try:
                href = card.get('href', '')
                # 提取 contentId
                cid_match = re.search(r'contentId=(\d+)', href)
                if not cid_match:
                    cid_match = re.search(r'contentId=([A-Za-z0-9_-]+)', href)
                if not cid_match:
                    continue

                content_id = cid_match.group(1)

                # 标题
                title_tag = card.find(['h2', 'h3', 'p', 'span', '.title', '.name'])
                title = title_tag.get_text(strip=True) if title_tag else f'视频 {content_id}'

                # 封面
                img_tag = card.find('img')
                cover = ''
                if img_tag:
                    cover = (img_tag.get('src') or img_tag.get('data-src') or
                             img_tag.get('data-original') or '')

                videos.append({
                    'vod_id': content_id,
                    'vod_name': title,
                    'vod_pic': cover,
                    'vod_content': '',
                    'vod_remarks': typecode,
                })
            except Exception as e:
                print(f"[_parse_from_html] card parse error: {e}")
                continue

        return videos

    def _extract_tx_vid(self, html):
        """从页面 HTML 中提取腾讯视频的 vid"""
        patterns = [
            r'"vid"\s*:\s*"([A-Za-z0-9]+)"',
            r"'vid'\s*:\s*'([A-Za-z0-9]+)'",
            r'vid\s*=\s*["\']([A-Za-z0-9]{8,15})["\']',
            r'v\.qq\.com/x/cover/[^/]+/([A-Za-z0-9]+)\.html',
            r'v\.qq\.com/x/page/([A-Za-z0-9]+)\.html',
            r'"fileId"\s*:\s*"([A-Za-z0-9]+)"',
            # 腾讯视频播放器初始化参数
            r'txplayer.*?vid["\'\s:]+([A-Za-z0-9]{8,15})',
        ]

        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
            if m:
                return m.group(1)

        return None

    def _resolve_tencent_video(self, vid):
        """
        通过腾讯视频API获取真实播放地址
        注意：腾讯视频的vkey有时效性，需要实时获取
        """
        try:
            # 腾讯视频信息API
            info_url = (
                f'https://vd.l.qq.com/proxyhttp?'
                f'buid=vinfoad&output=json&video_id={vid}'
                f'&platform=10901&charge=0&guid=76dd34894279343eb209c5309b8d8059'
                f'&flowid=&otype=json&defnpayver=0'
                f'&informal_idc=1&logintoken='
            )

            resp = self.session.get(info_url, timeout=10,
                headers={**self.headers, 'Referer': 'https://v.qq.com/'})

            data = resp.json()
            # 从返回数据中找 mp4 URL
            url = self._extract_url_from_vinfo(data)
            if url:
                return url

        except Exception as e:
            print(f"[_resolve_tencent_video] vd.l.qq.com error: {e}")

        try:
            # 备用API
            api_url = (
                f'https://pc.video.qq.com/webcgi/video/info?'
                f'vids={vid}&platform=10901&charge=0'
            )
            resp = self.session.get(api_url, timeout=10,
                headers={**self.headers, 'Referer': 'https://v.qq.com/'})
            data = resp.json()
            url = self._extract_url_from_vinfo(data)
            if url:
                return url

        except Exception as e:
            print(f"[_resolve_tencent_video] pc.video.qq.com error: {e}")

        # 最终备用：返回腾讯视频播放页，让TVBox解析器处理
        return f'https://v.qq.com/x/page/{vid}.html'

    def _extract_url_from_vinfo(self, data):
        """从腾讯视频API响应中提取mp4地址"""
        if not isinstance(data, dict):
            return None

        # 递归查找 .mp4 URL
        def find_mp4(obj, depth=0):
            if depth > 10:
                return None
            if isinstance(obj, str):
                if obj.endswith('.mp4') and ('qqvideo' in obj or 'smtcdns' in obj
                                              or 'ugchsy' in obj or 'cdn' in obj):
                    return obj
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    result = find_mp4(v, depth + 1)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = find_mp4(item, depth + 1)
                    if result:
                        return result
            return None

        return find_mp4(data)
