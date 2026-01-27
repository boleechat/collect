#!/usr/bin/env python3
# coding=utf-8
# TVBox养生堂爬虫 - 完全修复版

import json
import sys
import re
import time
from urllib.parse import urljoin, quote, urlparse
import requests
from datetime import datetime, timezone, timedelta

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        """初始化爬虫"""
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        print("[养生堂] Spider initialized successfully")
        pass  # TVBox要求不返回任何值或返回pass

    def getName(self):
        return "养生堂"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # 基础配置
    host = 'https://www.btime.com'
    base_url = 'https://www.btime.com/btv/btvws_yst'
    
    # API模板
    api_url_template = "https://pc.api.btime.com/btimeweb/infoFlow?list_id=btv_08da67cea600bf3c78973427bfaba12d_s0_{year}_{month:02d}&refresh=1&count=50&cursor={cursor}"
    
    # 请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'https://www.btime.com/',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive'
    }
    
    # 缓存
    _cache = {}
    _cache_time = {}
    _cache_duration = 1800  # 30分钟

    def homeContent(self, filter):
        """首页分类"""
        try:
            result = {}
            
            # 创建分类
            classes = [
                {'type_name': '最新', 'type_id': 'latest'},
                {'type_name': '本月', 'type_id': 'month1'},
                {'type_name': '近3月', 'type_id': 'month3'},
                {'type_name': '全部', 'type_id': 'all'}
            ]
            
            result['class'] = classes
            result['filters'] = {}
            
            print(f"[养生堂] homeContent返回 {len(classes)} 个分类")
            return result
            
        except Exception as e:
            print(f"[养生堂] homeContent错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'class': [], 'filters': {}}
    
    def homeVideoContent(self):
        """首页视频列表"""
        try:
            print("[养生堂] 获取首页视频...")
            videos = self._getVideos(limit=30)
            print(f"[养生堂] 首页返回 {len(videos)} 个视频")
            
            return {
                'list': videos,
                'page': 1,
                'pagecount': 1,
                'limit': 30,
                'total': len(videos)
            }
            
        except Exception as e:
            print(f"[养生堂] homeVideoContent错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    def categoryContent(self, tid, pg, filter, extend):
        """分类内容"""
        try:
            page = int(pg) if pg else 1
            print(f"[养生堂] 获取分类 {tid}, 页码 {page}")
            
            # 根据分类获取视频
            if tid == 'latest':
                all_videos = self._getVideos(limit=100)
            elif tid == 'month1':
                all_videos = self._getVideos(months=1)
            elif tid == 'month3':
                all_videos = self._getVideos(months=3)
            elif tid == 'all':
                all_videos = self._getVideos(months=12)
            else:
                all_videos = self._getVideos(limit=100)
            
            print(f"[养生堂] 分类 {tid} 共获取 {len(all_videos)} 个视频")
            
            # 分页
            page_size = 20
            start = (page - 1) * page_size
            end = start + page_size
            
            page_videos = all_videos[start:end] if start < len(all_videos) else []
            total_pages = max(1, (len(all_videos) + page_size - 1) // page_size)
            
            return {
                'list': page_videos,
                'page': page,
                'pagecount': total_pages,
                'limit': page_size,
                'total': len(all_videos)
            }
            
        except Exception as e:
            print(f"[养生堂] categoryContent错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'list': [], 'page': 1, 'pagecount': 1}
    
    def detailContent(self, ids):
        """视频详情"""
        try:
            if not ids:
                return {'list': []}
            
            vid = ids[0]
            print(f"[养生堂] 获取详情: {vid}")
            
            # 从缓存中查找
            all_videos = self._getAllCachedVideos()
            video_info = None
            
            for item in all_videos:
                if item.get('vod_id') == vid:
                    video_info = item
                    break
            
            if not video_info:
                print(f"[养生堂] 未找到视频: {vid}")
                return {'list': []}
            
            # 构建播放链接
            play_url = f"{video_info['vod_name']}${video_info['vod_url']}"
            
            vod = {
                'vod_id': vid,
                'vod_name': video_info['vod_name'],
                'vod_pic': video_info.get('vod_pic', ''),
                'vod_year': video_info.get('vod_year', ''),
                'vod_area': '健康养生',
                'vod_remarks': video_info.get('vod_remarks', ''),
                'vod_actor': '',
                'vod_director': '',
                'vod_content': video_info.get('vod_content', ''),
                'vod_play_from': '养生堂',
                'vod_play_url': play_url
            }
            
            return {'list': [vod]}
            
        except Exception as e:
            print(f"[养生堂] detailContent错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        """搜索"""
        try:
            print(f"[养生堂] 搜索关键词: {key}")
            
            all_videos = self._getAllCachedVideos()
            results = []
            
            key_lower = key.lower()
            for item in all_videos:
                title = item.get('vod_name', '').lower()
                if key_lower in title:
                    results.append(item)
            
            print(f"[养生堂] 搜索到 {len(results)} 个结果")
            
            return {
                'list': results[:50],
                'page': 1,
                'pagecount': 1,
                'limit': 50,
                'total': len(results)
            }
            
        except Exception as e:
            print(f"[养生堂] searchContent错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        """播放器"""
        try:
            print(f"[养生堂] 播放: {id}")
            
            # 直接返回URL
            if id.startswith(('http://', 'https://')):
                url = id
            else:
                url = id if id.startswith('/') else f"/{id}"
                url = f"{self.host}{url}"
            
            return {
                'parse': 1,
                'url': url,
                'header': self.headers
            }
            
        except Exception as e:
            print(f"[养生堂] playerContent错误: {str(e)}")
            return {'parse': 1, 'url': id}
    
    def localProxy(self, param):
        return [200, "video/MP2T", action, ""]

    # ==================== 内部方法 ====================
    
    def _getVideos(self, months=None, limit=None):
        """获取视频列表"""
        try:
            now = datetime.now()
            videos = []
            seen_ids = set()
            
            # 确定获取月份数
            if months:
                max_months = months
            elif limit:
                max_months = 6  # 限制数量时最多查6个月
            else:
                max_months = 12
            
            year = now.year
            month = now.month
            
            for i in range(max_months):
                if limit and len(videos) >= limit:
                    break
                
                month_videos = self._fetchMonth(year, month, seen_ids)
                videos.extend(month_videos)
                
                # 如果没获取到数据，继续下一个月
                if not month_videos and i > 0:
                    print(f"[养生堂] {year}-{month:02d} 无数据")
                
                # 前一个月
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1
                
                # 不早于2018年
                if year < 2018:
                    break
            
            # 如果设置了limit，截取
            if limit and len(videos) > limit:
                videos = videos[:limit]
            
            print(f"[养生堂] 共获取 {len(videos)} 个视频")
            return videos
            
        except Exception as e:
            print(f"[养生堂] _getVideos错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetchMonth(self, year, month, seen_ids):
        """获取指定月份的视频"""
        cache_key = f"{year}_{month:02d}"
        
        # 检查缓存
        if cache_key in self._cache:
            cache_time = self._cache_time.get(cache_key, 0)
            if time.time() - cache_time < self._cache_duration:
                print(f"[养生堂] 使用缓存: {cache_key}")
                return self._cache[cache_key]
        
        print(f"[养生堂] 正在获取 {year}-{month:02d}...")
        
        videos = []
        cursor = '0'
        max_tries = 3
        
        for attempt in range(max_tries):
            try:
                api_url = self.api_url_template.format(
                    year=year,
                    month=month,
                    cursor=cursor
                )
                
                response = self.session.get(
                    api_url,
                    headers=self.headers,
                    timeout=15
                )
                
                if response.status_code != 200:
                    print(f"[养生堂] HTTP {response.status_code}")
                    break
                
                text = response.text.strip()
                if not text:
                    print(f"[养生堂] 空响应")
                    break
                
                # 移除JSONP包装
                if text.startswith('(') or '(' in text[:50]:
                    start = text.find('(')
                    end = text.rfind(')')
                    if start != -1 and end != -1:
                        text = text[start+1:end]
                
                data = json.loads(text)
                
                if 'data' not in data or 'list' not in data['data']:
                    print(f"[养生堂] 数据格式错误")
                    break
                
                items = data['data']['list']
                if not items:
                    break
                
                # 解析视频
                for item in items:
                    try:
                        gid = item.get('gid', '')
                        if not gid or gid in seen_ids:
                            continue
                        
                        seen_ids.add(gid)
                        
                        item_data = item.get('data', {})
                        title = item_data.get('title', '无标题')
                        
                        # 时间戳
                        timestamp = int(item_data.get('pdate', 0))
                        if timestamp > 0:
                            tz = timezone(timedelta(hours=8))
                            dt = datetime.fromtimestamp(timestamp, tz)
                            date_str = dt.strftime('%Y年%m月%d日')
                        else:
                            date_str = f"{year}年{month:02d}月"
                        
                        # 封面
                        covers = item_data.get('covers', [])
                        pic = covers[0] if covers else ''
                        
                        # 描述
                        desc = item_data.get('detail', '')
                        if not desc:
                            desc = item_data.get('summary', '')
                        
                        # URL
                        url = f"https://item.btime.com/{gid}"
                        
                        video = {
                            'vod_id': gid,
                            'vod_name': title,
                            'vod_pic': pic,
                            'vod_url': url,
                            'vod_content': desc,
                            'vod_remarks': date_str,
                            'vod_year': str(year)
                        }
                        
                        videos.append(video)
                        
                    except Exception as e:
                        print(f"[养生堂] 解析视频错误: {e}")
                        continue
                
                print(f"[养生堂] {year}-{month:02d} 获取 {len(videos)} 个视频")
                
                # 检查是否还有更多
                next_cursor = data['data'].get('cursor')
                if not next_cursor or next_cursor == cursor:
                    break
                
                cursor = next_cursor
                break  # 成功后跳出重试循环
                
            except Exception as e:
                print(f"[养生堂] 获取失败 (尝试 {attempt+1}/{max_tries}): {e}")
                if attempt < max_tries - 1:
                    time.sleep(1)
                continue
        
        # 缓存结果
        if videos:
            self._cache[cache_key] = videos
            self._cache_time[cache_key] = time.time()
        
        return videos
    
    def _getAllCachedVideos(self):
        """获取所有缓存的视频"""
        all_videos = []
        for videos in self._cache.values():
            all_videos.extend(videos)
        
        # 如果缓存为空，获取一些数据
        if not all_videos:
            all_videos = self._getVideos(months=3)
        
        return all_videos
