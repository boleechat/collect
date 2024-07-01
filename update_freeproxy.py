import requests
import yaml

URL = 'https://yue.btjson.us.kg/5eb5a617-ea5e-4305-9e3e-c40f54f7207d?clash'
PROXY_GROUP_NAME = "Auto"
CHANNEL_INFO = "- 加入我的频道t.me/CMLiussss解锁更多优选节点"
END_MARKER = "      - 200848A7-A9BE-4546-BCC4-79B9BB10304A_VIP"

def fetch_remote_content():
    response = requests.get(URL)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")

def process_content(content):
    start_index = content.find(CHANNEL_INFO)
    end_index = content.find(END_MARKER, start_index)
    
    print("Content fetched: ", content[:500])  # Print the first 500 characters of content for debugging
    print("Start index: ", start_index)
    print("End index: ", end_index)
    
    if start_index == -1 or end_index == -1:
        raise Exception("Markers not found in the content")
    
    proxies_content = content[start_index:end_index].strip()
    return proxies_content

def generate_freeproxy_yml(proxies_content):
    with open('begin.yml', 'r') as file:
        begin_data = yaml.safe_load(file)

    auto_proxy_group = {
        "name": PROXY_GROUP_NAME,
        "type": "url-test",
        "proxies": proxies_content.split('\n'),
        "url": "http://www.google.com/generate_204",
        "interval": 300,
        "tolerance": 100,
        "lazy": True
    }

    begin_data['proxy-groups'].append(auto_proxy_group)

    with open('freeproxy.yml', 'w') as file:
        yaml.safe_dump(begin_data, file)

def main():
    content = fetch_remote_content()
    proxies_content = process_content(content)
    generate_freeproxy_yml(proxies_content)
    print("Freeproxy.yml updated successfully.")

if __name__ == "__main__":
    main()
