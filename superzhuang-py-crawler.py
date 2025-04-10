#!/usr/bin/env python3
# coding=utf-8
# 超级装视频爬虫 by Claude

import sys
import requests
import re
import json
import time
from urllib.parse import quote

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        print("超级装 initialized")
        return

    def getName(self):
        return "超级装"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    # 基础配置
    source_url = 'https://raw.githubusercontent.com/boleechat/collect/refs/heads/main/superzhuang.txt'
    
    # 请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://m.superzhuang.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive'
    }
    
    # 缓存抓取的数据
    data_cache = None

    def homeContent(self, filter):
        """生成首页内容"""
        result = {}
        
        # 只有一个分类
        classes = [{'type_name': '超级装', 'type_id': 'all'}]
        
        # 无过滤器
        filters = {}
        
        result['class'] = classes
        result['filters'] = filters
        return result
    
    def homeVideoContent(self):
        """获取首页视频内容"""
        # 抓取前30个视频
        videos = self.fetchVideos(limit=30)
        
        return {'list': videos}
    
    def categoryContent(self, tid, pg, filter, extend):
        """获取分类内容"""
        if pg == '1':  # 第一页
            self.currentPg = 1
        else:
            self.currentPg = int(pg)
        
        # 获取所有视频
        all_videos = self.fetchVideos()
        
        # 实现分页
        videos_per_page = 20
        start_idx = (self.currentPg - 1) * videos_per_page
        end_idx = start_idx + videos_per_page
        
        # 计算总页数
        total_pages = max(1, (len(all_videos) + videos_per_page - 1) // videos_per_page)
        
        result = {
            'list': all_videos[start_idx:end_idx] if start_idx < len(all_videos) else [],
            'page': pg,
            'pagecount': total_pages,
            'limit': videos_per_page,
            'total': len(all_videos)
        }
        
        return result
    
    def detailContent(self, ids):
        """获取视频详情"""
        if not ids:
            return {'list': []}
        
        vid = ids[0]
        
        # 获取所有视频数据
        all_videos = self.fetchVideos()
        
        video_info = None
        for item in all_videos:
            if item.get('vod_id') == vid:
                video_info = item
                break
        
        if not video_info:
            return {'list': [{'vod_name': '未找到视频', 'vod_play_from': '超级装', 'vod_play_url': '未找到$' + vid}]}
        
        # 从video_info提取详情
        title = video_info.get('vod_name', f"视频 {vid}")
        url = video_info.get('vod_url', '')
        img_url = video_info.get('vod_pic', '')
        desc = video_info.get('vod_content', '')
        
        # 创建播放URL
        play_url = f"{title}${url}"
        
        vod = {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': img_url,
            'vod_year': '',
            'vod_area': '装修',
            'vod_remarks': '超级装',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': desc,
            'vod_play_from': '超级装',
            'vod_play_url': play_url
        }
        
        return {'list': [vod]}
    
    def searchContent(self, key, quick, pg="1"):
        """通过关键字搜索视频"""
        results = []
        
        # 获取所有视频
        all_videos = self.fetchVideos()
        
        for item in all_videos:
            # 检查关键字是否在标题中
            title = item.get('vod_name', '')
            if key.lower() in title.lower():
                results.append(item)
        
        return {'list': results, 'page': pg, 'pagecount': 1, 'limit': 50, 'total': len(results)}
    
    def playerContent(self, flag, id, vipFlags):
        """获取视频播放信息"""
        headers = self.headers.copy()
        
        # 如果ID已经是完整URL，直接使用
        if id.startswith(('http://', 'https://')):
            # 获取实际视频URL
            try:
                # 发送请求获取页面内容
                response = self.session.get(id, headers=headers, timeout=10)
                response.raise_for_status()
                html_content = response.text
                
                # 尝试提取tc.qq.com的视频URL
                video_url_match = re.search(r'(https?://[^"]*\.tc\.qq\.com[^"]*\.mp4[^"]*)', html_content)
                if video_url_match:
                    video_url = video_url_match.group(1)
                    
                    # 额外处理：有些URL可能需要解码
                    video_url = video_url.replace('\\u002F', '/')
                    return {'parse': 0, 'url': video_url, 'header': headers}
            except Exception as e:
                print(f"Error extracting video URL: {e}")
                # 如果提取失败，尝试使用web解析
                return {'parse': 1, 'url': id, 'header': headers}
        
        return {'parse': 1, 'url': id, 'header': headers}
    
    def localProxy(self, param):
        return param
    
    # 辅助方法
    def fetchVideos(self, limit=None):
        """获取视频列表"""
        # 检查缓存中是否已有数据
        if self.data_cache is not None:
            if limit:
                return self.data_cache[:limit]
            return self.data_cache
        
        videos = []
        
        try:
            # 获取视频列表文本文件
            response = self.session.get(self.source_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            content = response.text
            
            # 解析每一行
            lines = content.strip().split('\n')
            for idx, line in enumerate(lines):
                if not line.strip():
                    continue
                
                parts = line.split(' , ')
                if len(parts) < 3:
                    continue
                
                url = parts[0].strip()
                title = parts[1].strip()
                img = parts[2].strip()
                
                # 从URL中提取contentId
                content_id_match = re.search(r'contentId=(\d+)', url)
                content_id = content_id_match.group(1) if content_id_match else f"id_{idx}"
                
                # 创建视频对象
                video = {
                    'vod_id': content_id,
                    'vod_name': title,
                    'vod_pic': img,
                    'vod_url': url,
                    'vod_content': f"超级装修案例: {title}",
                    'vod_remarks': '超级装'
                }
                
                videos.append(video)
        
        except Exception as e:
            print(f"Error fetching videos: {e}")
        
        # 缓存结果
        self.data_cache = videos
        print(f"总共获取到 {len(videos)} 个超级装视频")
        
        if limit:
            return videos[:limit]
        
        return videos
