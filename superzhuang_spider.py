#!/usr/bin/env python3
# coding=utf-8
# 超级装 视频爬虫 for TVBox
# 列表API: plusDecorationContentList
# 详情API: getApiDecorationContentDetails (含完整季集列表+vid)
# 播放API: vv.video.qq.com/getinfo (无需cKey)

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

    # 分类：往期节目 + 第1~17季
    # type_id 规则:
    #   "list"         → 往期节目列表（最新）
    #   "season_N"     → 第N季全集
    categories = (
        [{'type_id': 'list', 'type_name': '往期节目'}] +
        [{'type_id': f'season_{s}', 'type_name': f'第{s}季'} for s in range(1, 18)]
    )

    list_api   = 'https://api.superzhuangplus.com/api/stayUser/plusDecorationContentList'
    detail_api = 'https://api.superzhuangplus.com/api/stayUser/getApiDecorationContentDetails'
    txvideo_api = 'https://vv.video.qq.com/getinfo'

    # 任意一个固定contentId，用于拉取完整季集列表
    ANCHOR_CONTENT_ID = '1222913635461312512'

    guid     = '76dd34894279343eb209c5309b8d8059'
    platform = '11001'
    page_size = 10

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) '
            'Version/18.5 Mobile/15E148 Safari/604.1'
        ),
        'Referer':                     'https://m.superzhuang.com/',
        'Accept':                      'application/json, text/plain, */*',
        'Accept-Language':             'zh-CN,zh;q=0.9',
        'Origin':                      'https://m.superzhuang.com',
        'access-control-allow-origin': '*',
        'authorization-token':         'null',
        'Content-Type':                'text/plain',
    }

    # 季集数据缓存
    _season_cache = {}

    # ─── 首页 ────────────────────────────────────────────────────
    def homeContent(self, filter):
        return {'class': self.categories, 'filters': {}}

    def homeVideoContent(self):
        return {'list': self._fetch_latest_list(1)}

    # ─── 分类 ─────────────────────────────────────────────────────
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1

        if tid == 'list':
            videos = self._fetch_latest_list(pg)
            return {'list': videos, 'page': pg, 'pagecount': 99,
                    'limit': self.page_size, 'total': 999}

        if tid.startswith('season_'):
            season_num = int(tid.split('_')[1])
            videos = self._fetch_season(season_num)
            return {'list': videos, 'page': 1, 'pagecount': 1,
                    'limit': len(videos), 'total': len(videos)}

        return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 0, 'total': 0}

    # ─── 详情 ─────────────────────────────────────────────────────
    def detailContent(self, ids):
        if not ids:
            return {'list': []}

        # vod_id 格式: "contentId|title|cover|vid"
        # vid 已在列表阶段从 contentText 提取，直接使用，无需再请求
        parts      = ids[0].split('|', 3)
        content_id = parts[0]
        title      = parts[1] if len(parts) > 1 else f'视频{content_id}'
        cover      = parts[2] if len(parts) > 2 else ''
        vid        = parts[3] if len(parts) > 3 else ''

        # 如果 vid 已知，直接获取 mp4
        if vid:
            play_url = self._get_mp4_by_vid(vid)
        else:
            # 兜底：从详情API重新提取
            vid = self._get_vid_from_detail_api(content_id)
            play_url = self._get_mp4_by_vid(vid) if vid else ''

        if not play_url:
            print(f'[detailContent] 无法获取播放地址 contentId={content_id} vid={vid}')
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
        # 搜索往期节目
        for page in range(1, 5):
            videos = self._fetch_latest_list(page)
            if not videos:
                break
            for v in videos:
                if key.lower() in v.get('vod_name', '').lower():
                    results.append(v)
        # 搜索所有季集
        all_seasons = self._load_all_seasons()
        for ep in all_seasons:
            if key.lower() in ep.get('vod_name', '').lower():
                if not any(r['vod_id'] == ep['vod_id'] for r in results):
                    results.append(ep)
        return {'list': results, 'page': 1, 'pagecount': 1,
                'limit': 50, 'total': len(results)}

    # ─── 播放 ─────────────────────────────────────────────────────
    def playerContent(self, flag, id, vipFlags):
        if '.mp4' in id:
            return {
                'parse': 0,
                'url':   id,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer':    'https://v.qq.com/',
                },
            }
        return {'parse': 1, 'url': id, 'header': self.headers}

    def localProxy(self, param):
        return param

    # ─── 内部方法 ─────────────────────────────────────────────────
    def _fetch_latest_list(self, page):
        """往期节目最新列表（按时间倒序）"""
        payload = json.dumps({
            'currentPage':           page,
            'pageSize':              self.page_size,
            'contentTemplate':       '9500002',
            'contentTemplateSecond': '950000200002',
            'ownedIp':               '100004',
            'secondTagNumbers':      [],
            'tfcode':                'baidu_free',
            'typeCode':              'video',
        }, ensure_ascii=False)
        try:
            resp = self.session.post(
                self.list_api,
                data=payload.encode('utf-8'),
                headers=self.headers,
                timeout=15,
            )
            result = resp.json()
            if result.get('code') != 200:
                return []
            videos = []
            for item in result.get('data', {}).get('data', []):
                cid   = str(item.get('id', ''))
                title = item.get('contentTitle', '').strip()
                cover = item.get('firstImg', '')
                date  = item.get('createTime', '')[:10]
                # vid 需要从详情API获取，先留空，detailContent 时再取
                videos.append({
                    'vod_id':      f'{cid}|{title}|{cover}|',
                    'vod_name':    title,
                    'vod_pic':     cover,
                    'vod_content': '',
                    'vod_remarks': date,
                })
            return videos
        except Exception as e:
            print(f"[_fetch_latest_list] Error: {e}")
            return []

    def _load_all_seasons(self):
        """加载全部季集数据（含vid），带缓存"""
        if self._season_cache:
            all_eps = []
            for eps in self._season_cache.values():
                all_eps.extend(eps)
            return all_eps

        url = f'{self.detail_api}?contentId={self.ANCHOR_CONTENT_ID}'
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            data = resp.json().get('data', {})
            video_list = data.get('videoList', [])

            for season_obj in video_list:
                season_num = season_obj.get('videoSeasons', 0)
                eps = []
                for ep in season_obj.get('videoEpisodesList', []):
                    cid      = str(ep.get('contentId', ''))
                    title    = ep.get('contentTitle', '').strip()
                    cover    = ep.get('firstImg', '')
                    ep_num   = ep.get('videoEpisodes', 0)
                    # 直接从 contentText 里提取 vid，无需额外请求
                    vid = self._extract_vid_from_text(ep.get('contentText', ''))
                    remarks  = f'第{season_num}季 第{ep_num}集'
                    eps.append({
                        'vod_id':      f'{cid}|{title}|{cover}|{vid}',
                        'vod_name':    title,
                        'vod_pic':     cover,
                        'vod_content': '',
                        'vod_remarks': remarks,
                    })
                if eps:
                    self._season_cache[season_num] = eps

            print(f"[_load_all_seasons] 共 {len(video_list)} 季，"
                  f"{sum(len(v) for v in self._season_cache.values())} 集")
        except Exception as e:
            print(f"[_load_all_seasons] Error: {e}")

        all_eps = []
        for eps in self._season_cache.values():
            all_eps.extend(eps)
        return all_eps

    def _fetch_season(self, season_num):
        """获取指定季的全部集数"""
        if not self._season_cache:
            self._load_all_seasons()
        return self._season_cache.get(season_num, [])

    def _extract_vid_from_text(self, content_text):
        """从 contentText 的 iframe src 中提取腾讯视频 vid"""
        if not content_text:
            return ''
        m = re.search(
            r'v\.qq\.com/txp/iframe/player\.html\?vid=([A-Za-z0-9]+)',
            content_text, re.IGNORECASE)
        return m.group(1) if m else ''

    def _get_vid_from_detail_api(self, content_id):
        """兜底：从详情API页面提取vid（当列表阶段未提取到时使用）"""
        url = f'{self.detail_api}?contentId={content_id}'
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            data = resp.json().get('data', {})
            # 优先从 contentText 取
            vid = self._extract_vid_from_text(data.get('contentText', ''))
            if vid:
                return vid
            # 再从 videoList 里找 checked=true 的那集
            for season_obj in data.get('videoList', []):
                for ep in season_obj.get('videoEpisodesList', []):
                    if ep.get('checked') and str(ep.get('contentId')) == content_id:
                        return self._extract_vid_from_text(ep.get('contentText', ''))
        except Exception as e:
            print(f"[_get_vid_from_detail_api] Error: {e}")
        return ''

    def _get_mp4_by_vid(self, vid):
        """
        vv.video.qq.com/getinfo 获取 mp4 直链（无需 cKey，实测可用）
        结构: vl.vi[0] → ul.ui[0].url + fn + ?sdtfrom=v3010&guid=...&vkey=fvkey
        """
        if not vid:
            return ''
        url = (f'{self.txvideo_api}?vids={vid}'
               f'&platform={self.platform}&charge=0&otype=json&guid={self.guid}')
        try:
            resp = self.session.get(url, headers={
                'User-Agent': self.headers['User-Agent'],
                'Referer':    'https://v.qq.com/',
            }, timeout=15)
            txt = resp.text
            m = re.search(r'\{.*\}', txt, re.DOTALL)
            if not m:
                return ''
            data    = json.loads(m.group())
            vi_list = data.get('vl', {}).get('vi', [])
            if not vi_list:
                return ''
            vi    = vi_list[0]
            fn    = vi.get('fn', '')
            fvkey = vi.get('fvkey', '')
            ui    = vi.get('ul', {}).get('ui', [])
            base  = ui[0].get('url', '') if ui else ''
            if not (fn and fvkey and base):
                return ''
            mp4 = f"{base}{fn}?sdtfrom=v3010&guid={self.guid}&vkey={fvkey}"
            print(f"[_get_mp4] vid={vid} → OK")
            return mp4
        except Exception as e:
            print(f"[_get_mp4] Error: {e}")
            return ''
