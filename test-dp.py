#!/usr/bin/env python3
# coding=utf-8
# by boleechat

import json
import sys
import re
import time
import os
from datetime import datetime, timezone, timedelta
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

    # API配置
    api_url = "https://pc.api.btime.com/btimeweb/infoFlow"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.btime.com/'
    }

    # 年份配置（2018-2025）
    year_range = list(range(2018, 2026))
    current_year = datetime.now().year

    def homeContent(self, filter):
        """生成按年份分类的首页"""
        result = {}
        classes = [{
            'type_name': f"{year}年",
            'type_id': str(year)
        } for year in self.year_range]
        
        result['class'] = classes
        result['filters'] = {}
        return result

    def categoryContent(self, tid, pg, filter, extend):
        """按年份获取视频列表"""
        year = int(tid)
        all_videos = self.fetch_year_data(year)
        
        # 分页逻辑
        page = int(pg)
        per_page = 20
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'list': all_videos[start:end],
            'page': page,
            'pagecount': (len(all_videos) + per_page - 1) // per_page,
            'limit': per_page,
            'total': len(all_videos)
        }

    def detailContent(self, ids):
        """视频详情（直接使用API数据）"""
        vid = ids[0]
        for year in self.year_range:
            videos = self.fetch_year_data(year)
            for vod in videos:
                if vod['vod_id'] == vid:
                    return {'list': [vod]}
        return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """全局搜索"""
        results = []
        for year in self.year_range:
            videos = self.fetch_year_data(year)
            results.extend([
                v for v in videos
                if key.lower() in v['vod_name'].lower()
            ])
        return {
            'list': results,
            'page': 1,
            'pagecount': 1,
            'limit': 50,
            'total': len(results)
        }

    def playerContent(self, flag, id, vipFlags):
        """播放地址"""
        return {'parse': 1, 'url': id, 'header': self.headers}

    # 核心数据获取方法
    def fetch_year_data(self, year):
        """获取指定年份的所有视频数据"""
        cache_key = f"btime_{year}_cache"
        if not hasattr(self, cache_key):
            # 动态生成list_id（根据Btime的规律）
            list_id = f"btv_08da67cea600bf3c78973427bfaba12d_s0_{year}_"
            
            # 抓取所有月份数据（2025年只抓3个月）
            months = 3 if year == 2025 else 12
            all_items = []
            
            for month in range(1, months+1):
                params = {
                    "list_id": f"{list_id}{month:02d}",
                    "refresh": 1,
                    "count": 31  # 每月最多31条
                }
                try:
                    response = self.session.get(
                        self.api_url,
                        params=params,
                        headers=self.headers,
                        timeout=10
                    )
                    data = response.json()
                    all_items.extend(data.get('data', {}).get('list', []))
                except Exception as e:
                    print(f"抓取{year}年{month}月数据失败: {e}")
            
            # 转换为TVBox格式
            videos = []
            beijing_tz = timezone(timedelta(hours=8))
            for item in all_items:
                gid = item.get("gid", "")
                data = item.get("data", {})
                
                # 视频ID使用唯一标识
                vod_id = f"{year}_{gid}"
                
                # 时间戳转换
                pdate = data.get("pdate", 0)
                if pdate:
                    date_str = datetime.fromtimestamp(pdate, beijing_tz).strftime("%Y-%m-%d")
                else:
                    date_str = "未知时间"
                
                # 封面图处理
                covers = data.get("covers", [])
                cover = covers[0] if covers else ""
                
                videos.append({
                    'vod_id': vod_id,
                    'vod_name': data.get("title", "无标题"),
                    'vod_pic': cover,
                    'vod_year': str(year),
                    'vod_remarks': date_str,
                    'vod_play_from': 'Btime',
                    'vod_play_url': f"{data.get('title', '')}${self.generate_play_url(gid)}"
                })
            
            # 缓存结果
            setattr(self, cache_key, videos)
        
        return getattr(self, cache_key)

    def generate_play_url(self, gid):
        """生成播放地址（根据Btime实际页面规律）"""
        return f"https://item.btime.com/{gid}"

if __name__ == '__main__':
    # 测试代码
    spider = Spider()
    print(json.dumps(spider.homeContent({}), indent=2)
    print(json.dumps(spider.categoryContent("2025", 1, {}, {}), indent=2)