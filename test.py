import requests
from bs4 import BeautifulSoup
import re

def extract_video_url(page_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(page_url, headers=headers)
    if response.status_code == 200:
        match = re.search(r'"play_url":"(https[^"]+)"', response.text)
        if match:
            return match.group(1)
    return page_url  # 若未找到播放地址，返回原页面链接

def generate_html(videos):
    html = """<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>节目单</title>
<style>
    body { font-family: Arial, sans-serif; background-color: #f0f2f5; }
    .container { display: flex; flex-wrap: wrap; gap: 10px; }
    .item { width: 16%; text-align: center; background: #fff; border-radius: 8px; padding: 10px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); }
    img { width: 100%; border-radius: 5px; }
    a { text-decoration: none; color: #0078ff; }
</style>
</head>
<body>
<h1>节目单</h1>
<div class="container">
"""
    for video in videos:
        html += f"""
        <div class="item">
            <a href="{video['url']}" target="_blank">
                <img src="{video['img']}" alt="{video['title']}">
                <div>{video['title']}</div>
                <div>{video['date']}</div>
            </a>
        </div>
"""
    html += "</div></body></html>"
    return html

# 示例数据
videos = [
    {"title": "春季，警惕这样的咳喘", "url": extract_video_url("https://item.btime.com/232308sr967o2877h09os0h971d"), "img": "https://p0.ssl.cdn.btime.com/t11a477708f5fa87b216a0a2f17.jpg?size=1920x1080", "date": "2025年03月11日"},
    {"title": "筋长一寸 柔软的陷阱", "url": extract_video_url("https://item.btime.com/26fpa7ed2hofd8sjsdl9ijoijul"), "img": "https://p1.ssl.cdn.btime.com/t11a477708ff1e3f256bd2da989.jpg?size=1920x1080", "date": "2025年03月10日"}
]

# 生成 HTML 文件
with open("2025-01-03.html", "w", encoding="utf-8") as file:
    file.write(generate_html(videos))

print("HTML 文件生成成功！")
