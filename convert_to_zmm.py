import yaml
import base64
import json
import requests

# 下载 Clash 配置文件
url = "http://zmm.300000.best"
output_file = "zmm_sub.txt"

def encode_base64(data: str) -> str:
    """Base64 编码"""
    return base64.b64encode(data.encode()).decode().strip()

def convert_to_passwall(proxies):
    """转换 Clash 代理为 Passwall 订阅格式"""
    passwall_nodes = []
    
    for node in proxies:
        name = node.get("name", "Unnamed")
        server = node.get("server", "")
        port = node.get("port", "")
        
        if node["type"] == "vmess":
            vmess_data = {
                "v": "2",
                "ps": name,
                "add": server,
                "port": str(port),
                "id": node["uuid"],
                "aid": str(node.get("alterId", 0)),
                "net": node.get("network", "tcp"),
                "type": "none",
                "host": node.get("servername", ""),
                "path": node.get("path", ""),
                "tls": "tls" if node.get("tls", False) else "",
            }
            vmess_link = "vmess://" + encode_base64(json.dumps(vmess_data, separators=(",", ":")))
            passwall_nodes.append(vmess_link)
        
        elif node["type"] == "vless":
            params = f"?encryption=none&security=tls#{name}" if node.get("tls") else f"?encryption=none#{name}"
            vless_link = f"vless://{node['uuid']}@{server}:{port}{params}"
            passwall_nodes.append(vless_link)
        
        elif node["type"] == "ss":
            ss_data = f"{node['cipher']}:{node['password']}@{server}:{port}"
            ss_link = "ss://" + encode_base64(ss_data) + f"#{name}"
            passwall_nodes.append(ss_link)
        
        elif node["type"] == "trojan":
            trojan_link = f"trojan://{node['password']}@{server}:{port}#{name}"
            passwall_nodes.append(trojan_link)
        
        elif node["type"] == "ssr":
            ssr_data = f"{server}:{port}:{node.get('protocol', 'origin')}:{node['cipher']}:{node.get('obfs', 'plain')}:{encode_base64(node['password'])}"
            ssr_link = "ssr://" + encode_base64(ssr_data)
            passwall_nodes.append(ssr_link)
    
    return passwall_nodes

# 下载 Clash 配置文件
response = requests.get(url)
if response.status_code == 200:
    config = yaml.safe_load(response.text)

    if "proxies" in config:
        passwall_links = convert_to_passwall(config["proxies"])
        base64_sub = encode_base64("\n".join(passwall_links))
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(base64_sub)
        
        print(f"转换完成，请在 Passwall 订阅链接中填入：")
        print(f"https://raw.githubusercontent.com/boleechat/collect/main/zmm_sub.txt")
    else:
        print("错误: YAML 文件中未找到 proxies 配置")
else:
    print("下载 Clash 配置失败")
