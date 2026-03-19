#!/usr/bin/env python3
# coding=utf-8

import json
import sys
import requests
from datetime import datetime

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.session = requests.Session()
        print("SuperZhuang initialized")

    def getName(self):
        return "超级装"

    # API 地址
    api_base = "https://api.superzhuang.com/hy-crm"
    list_api = f"{api_base}/content/queryContentList"
    detail_api = f"{api_base}/programme/getProgrammeDetail"

    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.superzhuang.com/',
        'Content-Type': 'application/json'
    }

    def homeContent(self, filter):
        result = {}
        # 定义分类，根据网站上的页签
        classes = [
            {'type_name': '往期节目', 'type_id': 'video'},
            {'type_name': '精选案例', 'type_id': 'case'},
            {'type_name': '装修攻略', 'type_id': 'strategy'},
            {'type_name': '老房故事', 'type_id': 'old_house'}
        ]
        result['class'] = classes
        return result

    def homeVideoContent(self):
        # 首页默认展示“往期节目”
        return self.categoryContent('video', '1', False, {})

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        payload = {
            "typeCode": tid,
            "pageNo": int(pg),
            "pageSize": 20
        }
        
        try:
            res = self.session.post(self.list_api, json=payload, headers=self.headers)
            res_json = res.json()
            
            videos = []
            if res_json.get('code') == 200:
                item_list = res_json.get('data', {}).get('list', [])
                for item in item_list:
                    videos.append({
                        'vod_id': item.get('id'),
                        'vod_name': item.get('title'),
                        'vod_pic': item.get('coverImg'),
                        'vod_remarks': item.get('createTime', '').split(' ')[0]
                    })
            
            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 99  # 简单处理分页
            result['limit'] = 20
            result['total'] = 999
        except Exception as e:
            print(f"Error in categoryContent: {e}")
            
        return result

    def detailContent(self, ids):
        if not ids: return {'list': []}
        vid = ids[0]
        
        try:
            # 获取详情
            params = {'contentId': vid}
            res = self.session.get(self.detail_api, params=params, headers=self.headers)
            data = res.json().get('data', {})
            
            vod = {
                'vod_id': vid,
                'vod_name': data.get('title'),
                'vod_pic': data.get('coverImg'),
                'vod_type': "家居装修",
                'vod_content': data.get('summary') or data.get('title'),
                'vod_play_from': '超级装',
                'vod_play_url': f"播放${vid}"
            }
            return {'list': [vod]}
        except:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        # 这里的 id 就是 contentId
        try:
            params = {'contentId': id}
            res = self.session.get(self.detail_api, params=params, headers=self.headers)
            data = res.json().get('data', {})
            
            # 关键：从接口直接提取视频播放地址
            video_url = data.get('videoUrl')
            
            # 如果是腾讯视频的插件地址，TVBox 的 sniffer (parse:1) 会尝试解析
            # 如果接口直接返回 mp4，parse:0 即可直接播放
            return {
                'parse': 0,
                'url': video_url,
                'header': self.headers
            }
        except:
            return {'parse': 0, 'url': ''}

    def searchContent(self, key, quick, pg="1"):
        return {'list': []}

    def localProxy(self, param):
        return param