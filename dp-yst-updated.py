#!/usr/bin/env python3
# coding=utf-8
# 最终优化版 - 集成API直连与数据缓存

import json
import sys
import re
import time
from urllib.parse import urljoin
import requests
from datetime import datetime, timezone, timedelta

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        print("Btime 爬虫初始化成功")
        return

    def getName(self):
        return "Btime影视"

    # 核心配置
    host = 'https://www.btime.com'
    api_base = 'https://pc.api.btime.com/btimeweb/infoFlow'
    cache = {}
    current_year = str(datetime.now().year)
    
    # 请求头增强
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': f'{host}/btv/btvws_yst',
        'Accept-Encoding': 'gzip, deflate',
        'X-Requested-With': 'XMLHttpRequest'
    }

    def homeContent(self, filter):
        years = [str(y) for y in range(2018, datetime.now().year+1)][::-1]
        return {
            'class': [{'type_name': f"{y}年", 'type_id': y} for y in years],
            'filters': {}
        }

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        videos = self._fetch_year_data(tid)
        per_page = 20
        
        return {
            'list': videos[(page-1)*per_page : page*per_page],
            'page': page,
            'pagecount': (len(videos)+per_page-1)//per_page,
            'limit': per_page,
            'total': len(videos)
        }

    def detailContent(self, ids):
        video_id = ids[0]
        year, gid = video_id.split('_', 1) if '_' in video_id else (self.current_year, video_id)
        
        for item in self._fetch_year_data(year):
            if item['vod_id'] == video_id:
                return {'list': [{
                    **item,
                    'vod_play_url': f"{item['vod_name']}${item['vod_url']}"
                }]}
        return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        results = []
        for year in self._get_available_years():
            results.extend([
                item for item in self._fetch_year_data(year)
                if key.lower() in item['vod_name'].lower()
            ])
        return {'list': results}

    def playerContent(self, flag, id, vipFlags):
        return {'parse': 0, 'url': id, 'header': self.headers}

    # 核心数据获取方法
    def _fetch_year_data(self, year):
        if year in self.cache:
            return self.cache[year]
        
        data = []
        months = 3 if year == self.current_year else 12
        
        for month in range(1, months+1):
            try:
                params = {
                    'list_id': f'btv_08da67cea600bf3c78973427bfaba12d_s0_{year}_{month:02d}',
                    'refresh': 1,
                    'count': 31
                }
                resp = self.session.get(self.api_base, params=params, timeout=15)
                resp.raise_for_status()
                
                # 处理JSONP响应
                raw_data = resp.text.strip()
                if raw_data.startswith('callback('):
                    raw_data = raw_data[8:-1]
                
                for item in json.loads(raw_data)['data']['list']:
                    gid = item['gid']
                    video_data = {
                        'vod_id': f"{year}_{gid}",
                        'vod_name': item['data'].get('title', '无标题'),
                        'vod_pic': item['data'].get('covers', [''])[0],
                        'vod_year': year,
                        'vod_remarks': self._format_time(item['data'].get('pdate')),
                        'vod_url': f"https://item.btime.com/{gid}",
                        'vod_content': item['data'].get('detail') or item['data'].get('summary', '')
                    }
                    data.append(video_data)
            
            except Exception as e:
                print(f"[数据获取异常] 年份：{year} 月份：{month} 错误：{str(e)}")
                continue
        
        self.cache[year] = sorted(data, key=lambda x: x['vod_remarks'], reverse=True)
        return self.cache[year]

    # 辅助方法
    def _format_time(self, timestamp):
        if not timestamp:
            return "未知时间"
        return datetime.fromtimestamp(
            int(timestamp), 
            timezone(timedelta(hours=8))
        ).strftime("%Y-%m-%d %H:%M")

    def _get_available_years(self):
        return [str(y) for y in range(2018, datetime.now().year+1)]

if __name__ == '__main__':
    # 测试用例
    spider = Spider()
    
    print("== 首页分类测试 ==")
    print(json.dumps(spider.homeContent({}), indent=2)
    
    print("\n== 2023年数据测试 ==")
    print(json.dumps(spider.categoryContent("2023", 1, {}, {}), indent=2))
    
    print("\n== 播放地址测试 ==")
    test_id = next((v['vod_id'] for v in spider._fetch_year_data("2023")[:1]), None)
    print(json.dumps(spider.detailContent([test_id]), indent=2))