import requests

# 定义文件路径和URL
url = 'https://raw.githubusercontent.com/xiongjian83/iptv/main/speedtest/zubo_fofa.txt'
output_file = 'zubo.m3u'

# 下载文件
response = requests.get(url)
response.encoding = 'utf-8'
lines = response.text.splitlines()

# 打开输出文件并写入M3U格式
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("#EXTM3U\n")
    for i in range(0, len(lines), 2):
        if i+1 < len(lines):
            name = lines[i].split(',')[0].strip()
            url = lines[i+1].strip()
            f.write(f"#EXTINF:-1,{name}\n{url}\n")
