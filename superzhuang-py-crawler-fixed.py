#!/usr/bin/env python3
# coding=utf-8
# 超级装视频爬虫 - 修复版 by Claude

import sys
import requests
import re
import json
import time
import base64
from urllib.parse import quote, unquote

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
        """获取视频播放信息 - 修复版"""
        headers = self.headers.copy()
        
        # 如果ID已经是完整URL，直接使用
        if id.startswith(('http://', 'https://')):
            print(f"正在解析URL: {id}")
            
            try:
                # 1. 发送请求获取页面内容
                response = self.session.get(id, headers=headers, timeout=10)
                response.raise_for_status()
                html_content = response.text
                
                # 2. 提取视频ID和模板信息
                # 多种提取方法，应对可能的变化
                
                # 方法1: 直接寻找腾讯视频链接
                tc_qq_matches = re.findall(r'(https?://[^\'"\s]*?\.tc\.qq\.com[^\'"\s]*?\.mp4[^\'"\s]*)', html_content)
                if tc_qq_matches and len(tc_qq_matches) > 0:
                    video_url = tc_qq_matches[0].replace('\\/', '/').replace('\\u002F', '/')
                    print(f"方法1成功: {video_url[:100]}...")
                    return {'parse': 0, 'url': video_url, 'header': headers}
                
                # 方法2: 查找vid和视频模板
                vid_match = re.search(r'vid\s*[=:]\s*[\'"]([^\'"]+)[\'"]', html_content)
                template_match = re.search(r'templatePath\s*[=:]\s*[\'"]([^\'"]+)[\'"]', html_content)
                
                if vid_match and template_match:
                    vid = vid_match.group(1)
                    template = template_match.group(1)
                    video_url = f"https://v.qq.com/x/page/{vid}.html"
                    print(f"方法2成功: VID={vid}, Template={template}")
                    # 返回腾讯视频页面，让TVBox的解析器处理
                    return {'parse': 1, 'url': video_url, 'header': headers}
                
                # 方法3: 寻找video标签
                video_match = re.search(r'<video[^>]*src=[\'"]([^\'"]+)[\'"]', html_content)
                if video_match:
                    video_url = video_match.group(1)
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    print(f"方法3成功: {video_url[:100]}...")
                    return {'parse': 0, 'url': video_url, 'header': headers}
                
                # 方法4: 查找播放器初始化代码
                player_match = re.search(r'new\s+Player\s*\(\s*\{\s*url\s*:\s*[\'"]([^\'"]+)[\'"]', html_content)
                if player_match:
                    video_url = player_match.group(1)
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    print(f"方法4成功: {video_url[:100]}...")
                    return {'parse': 0, 'url': video_url, 'header': headers}
                
                # 方法5: 查找iframe嵌入
                iframe_match = re.search(r'<iframe[^>]*src=[\'"]([^\'"]+)[\'"]', html_content)
                if iframe_match:
                    iframe_url = iframe_match.group(1)
                    if iframe_url.startswith('//'):
                        iframe_url = 'https:' + iframe_url
                    
                    # 如果是腾讯视频的iframe
                    if 'v.qq.com' in iframe_url:
                        print(f"方法5成功: 找到腾讯视频iframe - {iframe_url}")
                        return {'parse': 1, 'url': iframe_url, 'header': headers}
                
                # 方法6: 通用搜索所有可能的视频链接
                video_urls = re.findall(r'(https?://[^\'"\s]*?(?:\.mp4|\.m3u8)[^\'"\s]*)', html_content)
                if video_urls and len(video_urls) > 0:
                    video_url = video_urls[0].replace('\\/', '/').replace('\\u002F', '/')
                    print(f"方法6成功: {video_url[:100]}...")
                    return {'parse': 0, 'url': video_url, 'header': headers}
                
                # 最终的后备方案：将原始URL传递给通用解析器
                print("未发现直接可用的视频URL，使用通用解析")
                return {'parse': 1, 'url': id, 'header': headers}
                
            except Exception as e:
                print(f"解析出错: {e}")
                # 出错时使用通用解析
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
                img = parts[2].strip() if len(parts) > 2 else ''
                
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
