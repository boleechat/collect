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
    for line in lines:
        if ',' in line and line.startswith("http"):
            # 分割成频道名称和URL
            name, url = line.split(',', 1)
            f.write(f"#EXTINF:-1,{name.strip()}\n{url.strip()}\n")
