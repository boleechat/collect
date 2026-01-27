#!/usr/bin/env python3
# coding=utf-8
# TVBox养生堂爬虫 - 根据实际API响应修复版

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
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        print("[养生堂] 爬虫初始化成功")
        pass

    def getName(self):
        return "养生堂"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # ==================== 配置 ====================
    host = 'https://www.btime.com'
    
    # API URL - 注意2026改为动态年份
    api_url_template = "https://pc.api.btime.com/btimeweb/infoFlow?callback=jQuery&list_id=btv_08da67cea600bf3c78973427bfaba12d_s0_{year}&refresh=1&count=50&expands=pageinfo"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'https://www.btime.com/btv/btvws_yst',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive'
    }
    
    # 缓存
    _all_videos = []
    _cache_time = 0
    _cache_duration = 1800  # 30分钟

    # ==================== TVBox接口 ====================
    
    def homeContent(self, filter):
        """首页分类"""
        try:
            classes = [
                {'type_name': '全部', 'type_id': 'all'}
            ]
            
            print(f"[养生堂] homeContent: 返回{len(classes)}个分类")
            return {'class': classes, 'filters': {}}
            
        except Exception as e:
            print(f"[养生堂] homeContent错误: {e}")
            import traceback
            traceback.print_exc()
            return {'class': [], 'filters': {}}
    
    def homeVideoContent(self):
        """首页视频"""
        try:
            print("[养生堂] homeVideoContent: 开始获取首页视频")
            videos = self._fetchAllVideos()
            
            # 只返回前30个
            result_videos = videos[:30] if len(videos) > 30 else videos
            
            print(f"[养生堂] homeVideoContent: 返回{len(result_videos)}个视频")
            
            return {
                'list': result_videos,
                'page': 1,
                'pagecount': 1,
                'limit': 30,
                'total': len(result_videos)
            }
            
        except Exception as e:
            print(f"[养生堂] homeVideoContent错误: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    def categoryContent(self, tid, pg, filter, extend):
        """分类内容"""
        try:
            page = int(pg) if pg else 1
            print(f"[养生堂] categoryContent: tid={tid}, page={page}")
            
            # 获取所有视频
            all_videos = self._fetchAllVideos()
            
            # 分页
            page_size = 20
            start = (page - 1) * page_size
            end = start + page_size
            
            page_videos = all_videos[start:end] if start < len(all_videos) else []
            total_pages = max(1, (len(all_videos) + page_size - 1) // page_size)
            
            print(f"[养生堂] categoryContent: 第{page}页，返回{len(page_videos)}个视频")
            
            return {
                'list': page_videos,
                'page': page,
                'pagecount': total_pages,
                'limit': page_size,
                'total': len(all_videos)
            }
            
        except Exception as e:
            print(f"[养生堂] categoryContent错误: {e}")
            import traceback
            traceback.print_exc()
            return {'list': [], 'page': 1, 'pagecount': 1}
    
    def detailContent(self, ids):
        """视频详情"""
        try:
            if not ids:
                return {'list': []}
            
            vid = ids[0]
            print(f"[养生堂] detailContent: vid={vid}")
            
            # 从缓存中查找
            all_videos = self._fetchAllVideos()
            video_info = None
            
            for item in all_videos:
                if item.get('vod_id') == vid:
                    video_info = item
                    break
            
            if not video_info:
                print(f"[养生堂] detailContent: 未找到视频{vid}")
                return {'list': []}
            
            # 构建播放URL
            play_url = f"{video_info['vod_name']}${video_info['vod_url']}"
            
            vod = {
                'vod_id': vid,
                'vod_name': video_info['vod_name'],
                'vod_pic': video_info.get('vod_pic', ''),
                'vod_year': video_info.get('vod_year', ''),
                'vod_area': '健康',
                'vod_remarks': video_info.get('vod_remarks', ''),
                'vod_actor': '',
                'vod_director': '',
                'vod_content': video_info.get('vod_content', ''),
                'vod_play_from': '养生堂',
                'vod_play_url': play_url
            }
            
            return {'list': [vod]}
            
        except Exception as e:
            print(f"[养生堂] detailContent错误: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    def searchContent(self, key, quick, pg="1"):
        """搜索"""
        try:
            print(f"[养生堂] searchContent: 关键词={key}")
            
            all_videos = self._fetchAllVideos()
            results = []
            
            key_lower = key.lower()
            for item in all_videos:
                title = item.get('vod_name', '').lower()
                if key_lower in title:
                    results.append(item)
            
            print(f"[养生堂] searchContent: 找到{len(results)}个结果")
            
            return {
                'list': results[:50],
                'page': 1,
                'pagecount': 1,
                'limit': 50,
                'total': len(results)
            }
            
        except Exception as e:
            print(f"[养生堂] searchContent错误: {e}")
            import traceback
            traceback.print_exc()
            return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        """播放"""
        try:
            print(f"[养生堂] playerContent: id={id}")
            
            # 如果是完整URL直接返回
            if id.startswith('http'):
                url = id
            else:
                # 否则构建完整URL
                url = id if id.startswith('/') else f"/{id}"
                url = f"{self.host}{url}"
            
            return {
                'parse': 1,
                'url': url,
                'header': self.headers
            }
            
        except Exception as e:
            print(f"[养生堂] playerContent错误: {e}")
            return {'parse': 1, 'url': id}
    
    def localProxy(self, param):
        return [200, "video/MP2T", action, ""]

    # ==================== 内部方法 ====================
    
    def _fetchAllVideos(self):
        """获取所有视频（带缓存）"""
        now = time.time()
        
        # 检查缓存
        if self._all_videos and (now - self._cache_time) < self._cache_duration:
            print(f"[养生堂] 使用缓存，共{len(self._all_videos)}个视频")
            return self._all_videos
        
        print("[养生堂] 开始获取视频列表...")
        
        videos = []
        seen_ids = set()
        
        # 获取当前年份和月份
        now_dt = datetime.now()
        current_year = now_dt.year
        
        # 从当前年份开始，往前找3年
        for year in range(current_year, current_year - 3, -1):
            print(f"[养生堂] 正在获取{year}年的视频...")
            
            year_videos = self._fetchYear(year, seen_ids)
            videos.extend(year_videos)
            
            print(f"[养生堂] {year}年获取到{len(year_videos)}个视频")
            
            # 如果已经有足够多的视频，可以停止
            if len(videos) >= 500:
                break
        
        # 更新缓存
        self._all_videos = videos
        self._cache_time = now
        
        print(f"[养生堂] 总共获取{len(videos)}个视频")
        return videos
    
    def _fetchYear(self, year, seen_ids):
        """获取指定年份的视频"""
        videos = []
        
        # 构建API URL
        api_url = self.api_url_template.format(year=year)
        
        print(f"[养生堂] API请求: {api_url}")
        
        try:
            # 发送请求
            response = self.session.get(
                api_url,
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"[养生堂] HTTP错误: {response.status_code}")
                return videos
            
            text = response.text.strip()
            if not text:
                print(f"[养生堂] 空响应")
                return videos
            
            print(f"[养生堂] 响应长度: {len(text)}")
            
            # 移除JSONP包装
            # 格式: jQuery36004838241714640312_1769480157489({...})
            if text.startswith('jQuery') or '(' in text[:100]:
                start_idx = text.find('(')
                end_idx = text.rfind(')')
                if start_idx != -1 and end_idx != -1:
                    text = text[start_idx + 1:end_idx]
                    print(f"[养生堂] 移除JSONP包装后长度: {len(text)}")
            
            # 解析JSON
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                print(f"[养生堂] JSON解析错误: {e}")
                print(f"[养生堂] 前100字符: {text[:100]}")
                return videos
            
            # 检查数据结构
            if 'data' not in data:
                print(f"[养生堂] 响应中没有data字段")
                print(f"[养生堂] 响应keys: {list(data.keys())}")
                return videos
            
            if 'list' not in data['data']:
                print(f"[养生堂] data中没有list字段")
                print(f"[养生堂] data.keys: {list(data['data'].keys())}")
                return videos
            
            items = data['data']['list']
            print(f"[养生堂] 获取到{len(items)}个item")
            
            # 解析每个视频
            for idx, item in enumerate(items):
                try:
                    # 获取gid（唯一ID）
                    gid = item.get('gid', '')
                    if not gid:
                        print(f"[养生堂] Item {idx} 没有gid")
                        continue
                    
                    # 检查是否已存在
                    if gid in seen_ids:
                        continue
                    
                    seen_ids.add(gid)
                    
                    # 获取数据部分
                    item_data = item.get('data', {})
                    
                    # 标题
                    title = item_data.get('title', '无标题')
                    
                    # URL
                    url = item.get('url', '') or f"https://item.btime.com/{gid}"
                    
                    # 封面图
                    covers = item_data.get('covers', [])
                    pic = covers[0] if covers else ''
                    
                    # 时长
                    duration = item_data.get('duration', '')
                    
                    # 日期
                    pdate_str = item_data.get('pdate_ymd', '')
                    if not pdate_str:
                        # 从pdate时间戳转换
                        pdate = item_data.get('pdate', '')
                        if pdate:
                            try:
                                timestamp = int(pdate)
                                dt = datetime.fromtimestamp(timestamp)
                                pdate_str = dt.strftime('%Y-%m-%d')
                            except:
                                pdate_str = str(year)
                    
                    # 角标（期数）
                    corner_text = ''
                    corner = item_data.get('corner', [])
                    if corner and len(corner) > 0:
                        corner_text = corner[0].get('text', '')
                    
                    # 备注（显示期数或日期）
                    remarks = corner_text if corner_text else pdate_str
                    
                    # 简介
                    summary = item_data.get('summary', '')
                    
                    # 来源
                    source = item_data.get('source', '养生堂')
                    
                    # 构建视频对象
                    video = {
                        'vod_id': gid,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_url': url,
                        'vod_remarks': remarks,
                        'vod_year': str(year),
                        'vod_area': '健康',
                        'vod_content': summary or f"{source} - {title}",
                        'vod_duration': duration
                    }
                    
                    videos.append(video)
                    
                    if idx < 3:  # 只打印前3个
                        print(f"[养生堂] 视频{idx+1}: {title} ({remarks})")
                
                except Exception as e:
                    print(f"[养生堂] 解析item {idx}错误: {e}")
                    continue
            
            print(f"[养生堂] 成功解析{len(videos)}个视频")
            
        except Exception as e:
            print(f"[养生堂] 获取{year}年数据错误: {e}")
            import traceback
            traceback.print_exc()
        
        return videos
