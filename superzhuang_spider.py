#!/usr/bin/env python3
# coding=utf-8
# 超级装 视频爬虫 for TVBox
# 网站: https://m.superzhuang.com/owner?typecode=video
# API: https://api.superzhuangplus.com/api/stayUser/plusDecorationContentList

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

    # 分类配置
    # type_id 格式: "typeCode|contentTemplate|contentTemplateSecond"
    # contentTemplate 来自 F12 抓包，其他分类如需调整在各 tab 下抓包确认
    categories = [
        {'type_id': 'video|9500002|950000200002',    'type_name': '往期节目'},
        {'type_id': 'case|9500001|950000100001',     'type_name': '精选案例'},
        {'type_id': 'strategy|9500003|950000300003', 'type_name': '装修攻略'},
        {'type_id': 'story|9500004|950000400004',    'type_name': '老房故事'},
    ]

    # 列表 API（POST，来自 F12 抓包）
    list_api = 'https://api.superzhuangplus.com/api/stayUser/plusDecorationContentList'

    # 详情页 URL 模板
    detail_page_tpl = 'https://m.superzhuang.com/programme?tfcode=baidu_free&contentId={cid}'

    # 请求头（来自 F12 抓包）
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) '
            'Version/18.5 Mobile/15E148 Safari/604.1'
        ),
        'Referer': 'https://m.superzhuang.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Origin': 'https://m.superzhuang.com',
        'access-control-allow-origin': '*',
        'authorization-token': 'null',
        'Content-Type': 'text/plain',
    }

    page_size = 10

    # ─── 首页 ────────────────────────────────────────────────────
    def homeContent(self, filter):
        return {'class': self.categories, 'filters': {}}

    def homeVideoContent(self):
        videos = self._fetch_list('video', '9500002', '950000200002', 1)
        return {'list': videos}

    # ─── 分类内容 ─────────────────────────────────────────────────
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1
        parts = tid.split('|')
        type_code            = parts[0] if len(parts) > 0 else 'video'
        content_template     = parts[1] if len(parts) > 1 else '9500002'
        content_template_sec = parts[2] if len(parts) > 2 else '950000200002'

        videos = self._fetch_list(type_code, content_template, content_template_sec, pg)

        return {
            'list':      videos,
            'page':      pg,
            'pagecount': 99,
            'limit':     self.page_size,
            'total':     999,
        }

    # ─── 详情 ─────────────────────────────────────────────────────
    def detailContent(self, ids):
        if not ids:
            return {'list': []}

        # vod_id 格式: "contentId|title|cover"
        parts      = ids[0].split('|', 2)
        content_id = parts[0]
        title      = parts[1] if len(parts) > 1 else f'视频{content_id}'
        cover      = parts[2] if len(parts) > 2 else ''

        detail_url = self.detail_page_tpl.format(cid=content_id)

        # 访问详情页，从 iframe src 提取腾讯视频 vid
        play_url = detail_url  # 兜底
        try:
            page_headers = {
                'User-Agent':      self.headers['User-Agent'],
                'Referer':         'https://m.superzhuang.com/',
                'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            resp = self.session.get(detail_url, headers=page_headers, timeout=15)
            resp.raise_for_status()
            html = resp.text

            tx_vid = self._extract_tx_vid(html)
            if tx_vid:
                # 直接构造 iframe URL，parse:1 由 TVBox 嗅探处理
                play_url = f'https://v.qq.com/txp/iframe/player.html?vid={tx_vid}'
                print(f'[detailContent] contentId={content_id} vid={tx_vid}')
            else:
                print(f'[detailContent] No vid found for contentId={content_id}')

        except Exception as e:
            print(f'[detailContent] Error: {e}')

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
        """
        TVBox 错误码 3003 = 播放地址加载失败，说明直接播放 v.qq.com iframe URL 不行。
        解决方案：
          - mp4 直链 → parse:0 直接播放
          - 腾讯视频任何形式 → parse:1 交给 TVBox 内置解析器嗅探
          - 超级装详情页 → 先提取 vid，再按上面规则处理
        """
        # 已是 mp4 直链 → 直接播放
        if '.mp4' in id and any(cdn in id for cdn in ('qqvideo', 'smtcdns', 'ugchsy', 'ugcbsy')):
            return {
                'parse': 0,
                'url':   id,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer':    'https://v.qq.com/',
                },
            }

        # 腾讯视频 iframe 播放器页面 → parse:1 嗅探
        # 格式: https://v.qq.com/txp/iframe/player.html?vid=z3544nb763i
        if 'v.qq.com/txp/iframe' in id:
            return {
                'parse': 1,
                'url':   id,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer':    'https://m.superzhuang.com/',
                },
            }

        # 腾讯视频其他页面 → parse:1 嗅探
        if 'v.qq.com' in id:
            return {
                'parse': 1,
                'url':   id,
                'header': {'User-Agent': self.headers['User-Agent']},
            }

        # 超级装详情页 → 重新提取 vid
        if 'm.superzhuang.com' in id:
            play_url = self._resolve_play_url(id)
            return {
                'parse': 1,
                'url':   play_url,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer':    'https://m.superzhuang.com/',
                },
            }

        return {'parse': 1, 'url': id, 'header': self.headers}

    def localProxy(self, param):
        return param

    # ─── 内部方法 ─────────────────────────────────────────────────
    def _fetch_list(self, type_code, content_template, content_template_sec, page):
        """
        POST 调用真实 API，返回 TVBox vod 列表。
        请求体结构来自 F12 抓包：
        {
            "currentPage": 1,
            "pageSize": 10,
            "contentTemplate": "9500002",
            "contentTemplateSecond": "950000200002",
            "ownedIp": "100004",
            "secondTagNumbers": [],
            "tfcode": "baidu_free",
            "typeCode": "video"
        }
        注意：Content-Type 是 text/plain，所以用 data= 发送序列化后的 JSON 字符串
        """
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
                print(f"[_fetch_list] API error code={result.get('code')} msg={result.get('message')}")
                return []

            items = result.get('data', {}).get('data', [])
            videos = []

            for item in items:
                cid     = str(item.get('id', ''))
                title   = item.get('contentTitle', f'视频{cid}').strip()
                cover   = item.get('firstImg', '')
                created = item.get('createTime', '')
                remarks = created[:10] if created else ''

                # 把 title、cover 编码进 vod_id，详情页无需再查列表
                vod_id = f'{cid}|{title}|{cover}'

                videos.append({
                    'vod_id':      vod_id,
                    'vod_name':    title,
                    'vod_pic':     cover,
                    'vod_content': '',
                    'vod_remarks': remarks,
                })

            print(f"[_fetch_list] typeCode={type_code} page={page} → {len(videos)} items")
            return videos

        except Exception as e:
            print(f"[_fetch_list] Error: {e}")
            return []

    def _resolve_play_url(self, detail_page_url):
        """
        访问超级装详情页，提取腾讯视频 vid，
        尝试用 proxyhttp 获取 mp4 直链；
        失败则返回 iframe URL（parse:1 交给TVBox嗅探）。
        """
        try:
            page_headers = {
                'User-Agent':      self.headers['User-Agent'],
                'Referer':         'https://m.superzhuang.com/',
                'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            resp = self.session.get(detail_page_url, headers=page_headers, timeout=15)
            resp.raise_for_status()
            html = resp.text

            tx_vid = self._extract_tx_vid(html)
            if not tx_vid:
                print(f"[_resolve_play_url] No vid found in {detail_page_url}")
                return detail_page_url

            print(f"[_resolve_play_url] tx_vid={tx_vid}")

            # 先尝试获取直链 mp4
            direct = self._get_tencent_direct_url(tx_vid)
            if direct:
                return direct

            # 兜底：返回 iframe URL，parse:1 嗅探
            iframe_url = f'https://v.qq.com/txp/iframe/player.html?vid={tx_vid}'
            print(f"[_resolve_play_url] fallback to iframe: {iframe_url}")
            return iframe_url

        except Exception as e:
            print(f"[_resolve_play_url] Error: {e}")
            return detail_page_url

    def _extract_tx_vid(self, html):
        """
        从 HTML 中提取腾讯视频 vid。
        经 F12 确认，vid 在超级装详情页的 iframe src 里：
          <iframe src="https://v.qq.com/txp/iframe/player.html?vid=z3544nb763i" ...>
        优先匹配此模式，其余作为备用。
        """
        patterns = [
            # ★ 最精确：iframe src 里的 vid 参数（F12 实测确认）
            r'v\.qq\.com/txp/iframe/player\.html\?vid=([A-Za-z0-9]+)',
            # 备用：其他腾讯视频 URL 格式
            r'v\.qq\.com/x/page/([A-Za-z0-9]{8,16})\.html',
            r'v\.qq\.com/x/cover/[^/]+/([A-Za-z0-9]{8,16})\.html',
            r'v\.qq\.com[^"\']{0,80}[?&]vid=([A-Za-z0-9]{8,16})',
            # JSON 格式
            r'"vid"\s*:\s*"([A-Za-z0-9]{8,16})"',
            r"'vid'\s*:\s*'([A-Za-z0-9]{8,16})'",
            # 播放器初始化
            r'txplayer[^}]{0,200}vid["\'\s:]+([A-Za-z0-9]{8,16})',
        ]
        skip = {'undefined', 'null', 'true', 'false', 'function'}
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
            if m:
                candidate = m.group(1)
                if candidate not in skip:
                    return candidate
        return None

    def _get_tencent_direct_url(self, vid):
        """
        POST vd6.l.qq.com/proxyhttp，精确还原 superplayer.js 的请求。
        响应结构（F12 实测）:
          vinfo(JSON字符串) → vl → vi[0] → ul.ui[0].url + fn + ?guid=...&vkey=fvkey
        """
        import urllib.parse, time as _time

        guid    = '76dd34894279343eb209c5309b8d8059'
        flowid  = 'd30dd6b3aedfcd19ff25d28c568cde85'
        tm      = str(int(_time.time()))
        ehost_q = urllib.parse.quote(
            f'https://v.qq.com/txp/iframe/player.html?vid={vid}', safe='')
        refer_q = urllib.parse.quote('https://m.superzhuang.com/', safe='')

        vinfoparam = (
            f'charge=0&otype=ojson&defnpayver=0'
            f'&spau=1&spaudio=0&spwm=1&sphls=1'
            f'&host=v.qq.com'
            f'&refer={refer_q}'
            f'&ehost={ehost_q}'
            f'&sphttps=1&encryptVer=8.5&cKey='
            f'&clip=4&guid={guid}&flowid={flowid}'
            f'&platform=11001&sdtfrom=v3010&appVer=1.60.0'
            f'&unid=&auth_from=&auth_ext='
            f'&vid={vid}&defn=shd&fhdswitch=0&dtype=3'
            f'&spsrt=2&tm={tm}&lang_code=0&logintoken='
            f'&qimei=&spvvpay=1&spadseg=3&spav1=15'
            f'&spvideo=0&screeninfo=%5B%7B%22rw%22%3A1920%2C%22rh%22%3A1080%7D%5D'
            f'&spm3u8tag=67&spmasterm3u8=3&track=undefined'
            f'&atime=0&playctrl=0&drm=0&multidrm=0'
        )

        adparam = (
            f'adType=preAd&vid={vid}'
            f'&flowid={flowid}&sspKey=fany'
        )

        # sspAdParam 精确还原（来自 F12 载荷）
        ssp_ad_param = json.dumps({
            "ad_scene": 1,
            "pre_ad_params": {
                "ad_scene": 1,
                "user_type": -1,
                "video": {
                    "base": {"vid": vid},
                    "is_live": False,
                    "type_id": 0,
                    "referer": "https://m.superzhuang.com/",
                    "url": f"https://v.qq.com/txp/iframe/player.html?vid={vid}",
                    "flow_id": flowid,
                    "fmt": "shd"
                },
                "platform": {
                    "guid": guid,
                    "channel_id": 191,
                    "site": "web",
                    "platform": "H5",
                    "from": 3,
                    "device": "iphone",
                    "play_platform": 11001,
                    "pv_tag": "m_superzhuang_com"
                },
                "player": {
                    "version": "1.60.0",
                    "plugin": "4.2.37",
                    "switch": 1,
                    "play_type": "0",
                    "img_type": "webp"
                },
                "token": {
                    "type": 0, "vuid": 0,
                    "vuser_session": "", "app_id": "",
                    "open_id": "", "access_token": ""
                }
            }
        }, ensure_ascii=False, separators=(',', ':'))

        payload = json.dumps({
            'buid':        'vinfoad',
            'adparam':     adparam,
            'sspAdParam':  ssp_ad_param,
            'vinfoparam':  vinfoparam,
        }, ensure_ascii=False)

        tx_headers = {
            'User-Agent':    self.headers['User-Agent'],
            'Referer':       f'https://v.qq.com/txp/iframe/player.html?vid={vid}',
            'Origin':        'https://v.qq.com',
            'Accept':        '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Content-Type':  'application/json',
        }

        for api in ['https://vd6.l.qq.com/proxyhttp',
                    'https://vd.l.qq.com/proxyhttp']:
            try:
                resp = self.session.post(
                    api,
                    data=payload.encode('utf-8'),
                    headers=tx_headers,
                    timeout=15,
                )
                resp.raise_for_status()
                outer = resp.json()

                vinfo_raw = outer.get('vinfo', '')
                if not vinfo_raw:
                    print(f"[proxyhttp] {api} → no vinfo field")
                    continue

                vinfo = json.loads(vinfo_raw)
                url = self._extract_url_from_vinfo(vinfo, guid)
                if url:
                    print(f"[proxyhttp] {api} success → {url[:80]}...")
                    return url
                else:
                    print(f"[proxyhttp] {api} → vinfo parsed but no url")

            except Exception as e:
                print(f"[proxyhttp] {api} error: {e}")

        return None

    def _extract_url_from_vinfo(self, vinfo, guid='76dd34894279343eb209c5309b8d8059'):
        """
        从 proxyhttp 响应的 vinfo 结构提取完整 mp4 URL。

        实测响应结构（F12 抓包）:
          vinfo.vl.vi[0]:
            ul.ui[]: CDN base URL 列表（取第一个）
            fn:      文件名，如 gzc_1000035_xxx.f632.mp4
            fvkey:   vkey 字符串

        完整 URL = ui[0].url + fn + ?guid=...&vkey=fvkey
        """
        try:
            vi_list = vinfo.get('vl', {}).get('vi', [])
            if not vi_list:
                return None

            vi = vi_list[0]
            fn    = vi.get('fn', '')
            fvkey = vi.get('fvkey', '')
            ui_list = vi.get('ul', {}).get('ui', [])

            if not fn or not fvkey or not ui_list:
                print(f"[_extract_url_from_vinfo] missing fields: fn={fn!r} fvkey={bool(fvkey)} ui_cnt={len(ui_list)}")
                return None

            base_url = ui_list[0].get('url', '')
            if not base_url:
                return None

            full_url = f"{base_url}{fn}?sdtfrom=v3010&guid={guid}&vkey={fvkey}"
            return full_url

        except Exception as e:
            print(f"[_extract_url_from_vinfo] error: {e}")
            # 兜底递归
            return self._find_mp4_url(vinfo)

    def _find_mp4_url(self, data, depth=0):
        """递归在 JSON 里找 mp4 直链"""
        if depth > 10:
            return None
        cdn_keywords = ('qqvideo', 'smtcdns', 'ugchsy', 'ugcbsy', 'tc.qq.com')
        if isinstance(data, str):
            if '.mp4' in data and any(k in data for k in cdn_keywords):
                return data
        elif isinstance(data, dict):
            for v in data.values():
                r = self._find_mp4_url(v, depth + 1)
                if r:
                    return r
        elif isinstance(data, list):
            for item in data:
                r = self._find_mp4_url(item, depth + 1)
                if r:
                    return r
        return None
