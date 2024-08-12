import requests

def process_m3u():
    url = "https://raw.githubusercontent.com/xiongjian83/TvBox/main/live.m3u"
    response = requests.get(url)
    content = response.text.splitlines()

    header = content[:3]
    phoenix_content = []
    capture = False

    for line in content:
        if "凤凰" in line:
            capture = True
        if capture:
            phoenix_content.append(line)
        if "翡翠" in line:
            phoenix_content.append(line)
            break

    with open("fh.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(header) + "\n")
        f.write("\n".join(phoenix_content))

if __name__ == "__main__":
    process_m3u()
