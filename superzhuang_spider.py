#!/usr/bin/env python3
# coding=utf-8
# 超级装 视频爬虫 for TVBox
# 网站: https://m.superzhuang.com/owner?typecode=video
# 列表API: https://api.superzhuangplus.com/api/stayUser/plusDecorationContentList
# 详情API: https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails
# 播放API: https://vv.video.qq.com/getinfo (无需cKey，直接返回mp4+vkey)

import json
import sys
import re
import requests

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

    # type_id 格式: "typeCode|contentTemplate|contentTemplateSecond"
    categories = [
        {'type_id': 'video|9500002|950000200002',    'type_name': '往期节目'},
        {'type_id': 'case|9500001|950000100001',     'type_name': '精选案例'},
        {'type_id': 'strategy|9500003|950000300003', 'type_name': '装修攻略'},
        {'type_id': 'story|9500004|950000400004',    'type_name': '老房故事'},
    ]

    # 列表 API
    list_api   = 'https://api.superzhuangplus.com/api/stayUser/plusDecorationContentList'
    # 详情 API（GET，返回含腾讯视频vid的HTML片段）
    detail_api = 'https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails'
    # 腾讯视频信息 API（无需cKey，实测可用）
    txvideo_api = 'https://vv.video.qq.com/getinfo'

    guid     = '76dd34894279343eb209c5309b8d8059'
    platform = '11001'

    # 列表请求头
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) '
            'Version/18.5 Mobile/15E148 Safari/604.1'
        ),
        'Referer':                  'https://m.superzhuang.com/',
        'Accept':                   'application/json, text/plain, */*',
        'Accept-Language':          'zh-CN,zh;q=0.9',
        'Origin':                   'https://m.superzhuang.com',
        'access-control-allow-origin': '*',
        'authorization-token':      'null',
        'Content-Type':             'text/plain',
    }

    page_size = 10

    # ─── 首页 ────────────────────────────────────────────────────
    def homeContent(self, filter):
        return {'class': self.categories, 'filters': {}}

    def homeVideoContent(self):
        return {'list': self._fetch_list('video', '9500002', '950000200002', 1)}

    # ─── 分类 ─────────────────────────────────────────────────────
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1
        parts = tid.split('|')
        tc  = parts[0] if len(parts) > 0 else 'video'
        ct  = parts[1] if len(parts) > 1 else '9500002'
        ct2 = parts[2] if len(parts) > 2 else '950000200002'
        videos = self._fetch_list(tc, ct, ct2, pg)
        return {'list': videos, 'page': pg, 'pagecount': 99,
                'limit': self.page_size, 'total': 999}

    # ─── 详情 ─────────────────────────────────────────────────────
    def detailContent(self, ids):
        if not ids:
            return {'list': []}

        # vod_id 格式: "contentId|title|cover"
        parts      = ids[0].split('|', 2)
        content_id = parts[0]
        title      = parts[1] if len(parts) > 1 else f'视频{content_id}'
        cover      = parts[2] if len(parts) > 2 else ''

        # 第一步：从详情API拿腾讯视频vid
        tx_vid = self._get_vid_from_detail_api(content_id)

        # 第二步：用vid调vv.video.qq.com拿mp4直链
        if tx_vid:
            play_url = self._get_mp4_by_vid(tx_vid)
        else:
            play_url = ''

        if not play_url:
            print(f'[detailContent] 无法获取播放地址 contentId={content_id}')
            play_url = f'https://m.superzhuang.com/programme?tfcode=baidu_free&contentId={content_id}'

        vod = {
            'vod_id':        ids[0],
            'vod_name':      title,
            'vod_pic':       cover,
            'vod_content':   '',
            'vod_remarks':   '',
            'vod_play_from': 'SuperZhuang',
            'vod_play_url':  f'{title}${play_url}',
        }
        return {'list': [vod]}

    # ─── 搜索 ─────────────────────────────────────────────────────
    def searchContent(self, key, quick, pg="1"):
        results = []
        for page in range(1, 5):
            videos = self._fetch_list('video', '9500002', '950000200002', page)
            if not videos:
                break
            for v in videos:
                if key.lower() in v.get('vod_name', '').lower():
                    results.append(v)
        return {'list': results, 'page': 1, 'pagecount': 1,
                'limit': 50, 'total': len(results)}

    # ─── 播放 ─────────────────────────────────────────────────────
    def playerContent(self, flag, id, vipFlags):
        # mp4 直链 → parse:0 直接播放
        if '.mp4' in id:
            return {
                'parse': 0,
                'url':   id,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer':    'https://v.qq.com/',
                },
            }
        # 兜底
        return {'parse': 1, 'url': id, 'header': self.headers}

    def localProxy(self, param):
        return param

    # ─── 内部方法 ─────────────────────────────────────────────────
    def _fetch_list(self, type_code, content_template, content_template_sec, page):
        """调用列表API，返回TVBox vod列表"""
        payload = json.dumps({
            'currentPage':           page,
            'pageSize':              self.page_size,
            'contentTemplate':       content_template,
            'contentTemplateSecond': content_template_sec,
            'ownedIp':               '100004',
            'secondTagNumbers':      [],
            'tfcode':                'baidu_free',
            'typeCode':              type_code,
        }, ensure_ascii=False)

        try:
            resp = self.session.post(
                self.list_api,
                data=payload.encode('utf-8'),
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get('code') != 200:
                print(f"[_fetch_list] API error code={result.get('code')}")
                return []

            videos = []
            for item in result.get('data', {}).get('data', []):
                cid     = str(item.get('id', ''))
                title   = item.get('contentTitle', f'视频{cid}').strip()
                cover   = item.get('firstImg', '')
                created = item.get('createTime', '')
                remarks = created[:10] if created else ''
                videos.append({
                    'vod_id':      f'{cid}|{title}|{cover}',
                    'vod_name':    title,
                    'vod_pic':     cover,
                    'vod_content': '',
                    'vod_remarks': remarks,
                })
            print(f"[_fetch_list] {type_code} page={page} → {len(videos)} items")
            return videos
        except Exception as e:
            print(f"[_fetch_list] Error: {e}")
            return []

    def _get_vid_from_detail_api(self, content_id):
        """
        调用超级装详情API获取腾讯视频vid。
        实测：GET getApiDecorationContentDetails?contentId=xxx
        响应HTML片段里含 <iframe src="https://v.qq.com/txp/iframe/player.html?vid=xxx">
        """
        url = f'{self.detail_api}?contentId={content_id}'
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            txt = resp.text
            # 精确匹配 iframe src 里的 vid（F12实测确认的位置）
            m = re.search(
                r'v\.qq\.com/txp/iframe/player\.html\?vid=([A-Za-z0-9]+)',
                txt, re.IGNORECASE)
            if m:
                vid = m.group(1)
                print(f"[_get_vid] contentId={content_id} → vid={vid}")
                return vid
            print(f"[_get_vid] 未找到vid，响应长度={len(txt)}")
        except Exception as e:
            print(f"[_get_vid] Error: {e}")
        return None

    def _get_mp4_by_vid(self, vid):
        """
        用 vv.video.qq.com/getinfo 获取mp4直链。
        实测：platform=11001 可返回 fn + fvkey + ul.ui[0].url，无需cKey。
        完整URL = base + fn + ?sdtfrom=v3010&guid=...&vkey=fvkey
        """
        url = (f'{self.txvideo_api}?vids={vid}'
               f'&platform={self.platform}&charge=0&otype=json&guid={self.guid}')
        try:
            resp = self.session.get(url, headers={
                'User-Agent': self.headers['User-Agent'],
                'Referer':    'https://v.qq.com/',
            }, timeout=15)

            txt = resp.text
            # 去掉JSONP包装（如有）
            m = re.search(r'\{.*\}', txt, re.DOTALL)
            if not m:
                print(f"[_get_mp4] 无JSON响应")
                return None

            data    = json.loads(m.group())
            vi_list = data.get('vl', {}).get('vi', [])
            if not vi_list:
                print(f"[_get_mp4] vi为空")
                return None

            vi    = vi_list[0]
            fn    = vi.get('fn', '')
            fvkey = vi.get('fvkey', '')
            ui    = vi.get('ul', {}).get('ui', [])
            base  = ui[0].get('url', '') if ui else ''

            if not (fn and fvkey and base):
                print(f"[_get_mp4] 字段缺失 fn={bool(fn)} fvkey={bool(fvkey)} base={bool(base)}")
                return None

            mp4 = f"{base}{fn}?sdtfrom=v3010&guid={self.guid}&vkey={fvkey}"
            print(f"[_get_mp4] vid={vid} → {mp4[:80]}...")
            return mp4

        except Exception as e:
            print(f"[_get_mp4] Error: {e}")
        return None
