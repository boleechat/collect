#!/usr/bin/env python3
# coding=utf-8
# 最小测试爬虫 - 用于验证TVBox是否能加载爬虫

import sys
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        pass
    
    def getName(self):
        return "养生堂测试"
    
    def isVideoFormat(self, url):
        pass
    
    def manualVideoCheck(self):
        pass
    
    def destroy(self):
        pass
    
    def homeContent(self, filter):
        """返回一个测试分类"""
        return {
            'class': [
                {'type_name': '测试分类', 'type_id': 'test'}
            ],
            'filters': {}
        }
    
    def homeVideoContent(self):
        """返回硬编码的测试视频"""
        return {
            'list': [
                {
                    'vod_id': 'test001',
                    'vod_name': '✅ 测试视频1 - 如果你能看到这个，说明爬虫加载成功！',
                    'vod_pic': 'https://p2.ssl.cdn.btime.com/t11a477708fefdb2d65cf8088a0.jpg',
                    'vod_url': 'https://item.btime.com/test001',
                    'vod_remarks': '测试中',
                    'vod_year': '2026',
                    'vod_area': '测试',
                    'vod_content': '这是一个测试视频，用于验证TVBox是否能正确加载和显示爬虫内容。'
                },
                {
                    'vod_id': 'test002',
                    'vod_name': '✅ 测试视频2 - 爬虫工作正常',
                    'vod_pic': 'https://p1.ssl.cdn.btime.com/t11a477708f786507f03ec5c7c5.jpg',
                    'vod_url': 'https://item.btime.com/test002',
                    'vod_remarks': '测试中',
                    'vod_year': '2026',
                    'vod_area': '测试',
                    'vod_content': '如果能看到这两个测试视频，说明爬虫基本功能正常，问题可能在网络请求或数据解析部分。'
                }
            ],
            'page': 1,
            'pagecount': 1,
            'limit': 2,
            'total': 2
        }
    
    def categoryContent(self, tid, pg, filter, extend):
        """分类内容也返回测试数据"""
        return self.homeVideoContent()
    
    def detailContent(self, ids):
        """详情"""
        if not ids:
            return {'list': []}
        
        return {
            'list': [{
                'vod_id': ids[0],
                'vod_name': '测试视频详情',
                'vod_pic': 'https://p2.ssl.cdn.btime.com/t11a477708fefdb2d65cf8088a0.jpg',
                'vod_url': 'https://item.btime.com/test',
                'vod_remarks': '测试',
                'vod_year': '2026',
                'vod_area': '测试',
                'vod_content': '测试视频的详细内容',
                'vod_play_from': '测试源',
                'vod_play_url': '测试视频$https://item.btime.com/test'
            }]
        }
    
    def searchContent(self, key, quick, pg="1"):
        """搜索"""
        return {
            'list': [{
                'vod_id': 'search001',
                'vod_name': f'搜索测试: {key}',
                'vod_pic': '',
                'vod_url': 'https://item.btime.com/search',
                'vod_remarks': '搜索结果'
            }],
            'page': 1,
            'pagecount': 1
        }
    
    def playerContent(self, flag, id, vipFlags):
        """播放"""
        return {
            'parse': 1,
            'url': 'https://item.btime.com/test'
        }
    
    def localProxy(self, param):
        return [200, "video/MP2T", action, ""]
