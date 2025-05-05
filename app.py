#!/usr/bin/env python

import os
import re
import shutil
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import requests
import json
import time
import base64
import random
import string
import asyncio

FILE_PATH = os.environ.get('FILE_PATH', './.tmp')
XCONF_PATH = os.path.join(FILE_PATH, 'xconf')
PROJECT_URL = os.environ.get('URL', '')
INTERVAL_SECONDS = int(os.environ.get("TIME", 120))
VMPATH = os.environ.get('VMPATH', 'startvm')
VLPATH = os.environ.get('VLPATH', 'startvl')
CFIP = os.environ.get('CFIP', 'ip.sb')
PORT = int(os.environ.get('SERVER_PORT') or os.environ.get('PORT') or 3000)
ARGO_PORT = int(os.environ.get('ARGO_PORT', 8080))
CFPORT = int(os.environ.get('CFPORT', 443))

UUID = os.environ.get('UUID', '')
NEZHA_VERSION = os.environ.get('NEZHA_VERSION', 'V0')
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', '')
NEZHA_KEY = os.environ.get('NEZHA_KEY', '')
NEZHA_PORT = os.environ.get('NEZHA_PORT', '443')
SUB_NAME = os.environ.get('SUB_NAME', '')
SUB_URL = os.environ.get('SUB_URL', '')

ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', '')
ARGO_AUTH = os.environ.get('ARGO_AUTH', '')

def cleanupOldFiles():
    if os.path.exists(FILE_PATH):
        shutil.rmtree(FILE_PATH)
        print(f"{FILE_PATH} deleted")
    else:
        print(f"{FILE_PATH} not created")

def createFolder(folderPath):
    if not os.path.exists(folderPath):
        os.makedirs(folderPath)
        print(f"{folderPath} is created")
    else:
        print(f"{folderPath} already exists")

class MyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Hello, world')
        elif self.path == '/sub':
            try:
                with open(os.path.join(FILE_PATH, 'log.txt'), 'rb') as file:
                    content = file.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'Error reading file')
        elif self.path == '/healthcheck':
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'ok')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

def start_http_server():
    server = HTTPServer(('0.0.0.0', PORT), MyHandler)
    print('server is running on port :', PORT)
    server.serve_forever()

vmpath = '/' + str(VMPATH)
vlpath = '/' + str(VLPATH)
def generate_config():
    inbound = {
        "log": {
            "access": "/dev/null",
            "error": "/dev/null",
            "loglevel": "none"
        },
        "dns": {
            "servers": [
                "https+local://8.8.8.8/dns-query"
            ]
        },
        "inbounds": [
            {
                "port": ARGO_PORT,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": UUID,
                            "flow": "xtls-rprx-vision"
                        }
                    ],
                    "decryption": "none",
                    "fallbacks": [
                        {
                            "path": vlpath,
                            "dest": 8001
                        },
                        {
                            "path": vmpath,
                            "dest": 8002
                        }
                    ]
                },
                "streamSettings": {
                    "network": "tcp"
                }
            },
            {
                "port": 8001,
                "listen": "127.0.0.1",
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": UUID,
                            "level": 0
                        }
                    ],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "ws",
                    "security": "none",
                    "wsSettings": {
                        "path": vlpath
                    }
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": [
                        "http",
                        "tls",
                        "quic"
                    ],
                    "metadataOnly": False
                }
            },
            {
                "port": 8002,
                "listen": "127.0.0.1",
                "protocol": "vmess",
                "settings": {
                    "clients": [
                        {
                            "id": UUID,
                            "alterId": 0
                        }
                    ]
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {
                        "path": vmpath
                    }
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": [
                        "http",
                        "tls",
                        "quic"
                    ],
                    "metadataOnly": False
                }
            }
        ]
    };
    with open(os.path.join(XCONF_PATH, 'inbound.json'), 'w', encoding='utf-8') as inbound_file:
        json.dump(inbound, inbound_file, ensure_ascii=False, indent=2)

    outbound = {
        "outbounds": [
            {
                "tag": "direct",
                "protocol": "freedom"
            },
            {
                "tag": "block",
                "protocol": "blackhole"
            }
        ]
    };
    with open(os.path.join(XCONF_PATH, 'outbound.json'), 'w', encoding='utf-8') as outbound_file:
        json.dump(outbound, outbound_file, ensure_ascii=False, indent=2)

def argo_config():
    if not ARGO_AUTH or not ARGO_DOMAIN:
        print("ARGO_DOMAIN or ARGO_AUTH is empty, use quick Tunnels")
        return

    if 'TunnelSecret' in ARGO_AUTH:
        with open(os.path.join(FILE_PATH, 'tunnel.json'), 'w') as file:
            file.write(ARGO_AUTH)
        tunnel_yaml = f"""tunnel: {ARGO_AUTH.split('"')[11]}
credentials-file: {os.path.join(FILE_PATH, 'tunnel.json')}
protocol: http2

ingress:
  - hostname: {ARGO_DOMAIN}
    service: http://localhost:{ARGO_PORT}
    originRequest:
      noTLSVerify: true
  - service: http_status:404
"""
        with open(os.path.join(FILE_PATH, 'tunnel.yml'), 'w') as file:
            file.write(tunnel_yaml)
    else:
        print("Use token connect to tunnel")

def get_cloud_flare_args():
    args = ""
    if re.match(r'^[A-Z0-9a-z=]{120,250}$', ARGO_AUTH):
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 run --token {ARGO_AUTH}"
    elif "TunnelSecret" in ARGO_AUTH:
        args = f"tunnel --edge-ip-version auto --config {os.path.join(FILE_PATH, 'tunnel.yml')} run"
    else:
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {os.path.join(FILE_PATH, 'boot.log')} --loglevel info --url http://localhost:{ARGO_PORT}"
    return args

def get_files_for_architecture():
    arch = os.uname().machine
    if arch in ['arm', 'arm64', 'aarch64']:
        base_files = [
            {'original_name': 'bot', 'file_url': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64'},
            {'original_name': 'web', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/xray_arm'},
        ]
        if NEZHA_VERSION == 'V0':
            base_files.append({'original_name': 'npm', 'file_url': 'https://github.com/kahunama/myfile/releases/download/main/nezha-agent_arm'})
        elif NEZHA_VERSION == 'V1':
            base_files.append({'original_name': 'npm', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/nezha-agentv1_arm'})
    else:
        base_files = [
            {'original_name': 'bot', 'file_url': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64'},
            {'original_name': 'web', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/xray'},
        ]
        if NEZHA_VERSION == 'V0':
            base_files.append({'original_name': 'npm', 'file_url': 'https://github.com/kahunama/myfile/releases/download/main/nezha-agent'})
        elif NEZHA_VERSION == 'V1':
            base_files.append({'original_name': 'npm', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/nezha-agentv1'})
    return base_files

def authorize_files(file_name_mapping):
    new_permissions = 0o775
    for original_name, new_file_name in file_name_mapping.items():
        absolute_file_path = os.path.join(FILE_PATH, new_file_name)
        try:
            os.chmod(absolute_file_path, new_permissions)
            print(f"Empowerment success for {absolute_file_path} ({original_name}): {oct(new_permissions)}")
        except Exception as e:
            print(f"Empowerment failed for {absolute_file_path} ({original_name}): {e}")

def download_function(original_name, file_url):
    random_file_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    file_path = os.path.join(FILE_PATH, random_file_name)
    try:
        with requests.get(file_url, stream=True) as response, open(file_path, 'wb') as file:
            shutil.copyfileobj(response.raw, file)
        print(f"Downloaded {original_name} (renamed to {random_file_name}) successfully")
        return random_file_name
    except Exception as e:
        print(f"Download {original_name} (renamed to {random_file_name}) failed: {e}")
        return None

def run_service_with_retry(cmd, service_name, max_retries=3):
    for attempt in range(max_retries):
        process = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

        if process.poll() is None:
            print(f"{service_name} is running")
            return True
        else:
            if attempt < max_retries - 1:
                print(f"{service_name} failed to start, retrying... ({attempt + 1}/{max_retries})")
                process.kill()
                time.sleep(1)
            else:
                print(f"{service_name} failed to start after {max_retries} attempts")
        return False

file_name_mapping = {}
def download_files_and_run():
    files_to_download = get_files_for_architecture()
    if not files_to_download:
        print("Can't find a file for the current architecture")
        return

    for file_info in files_to_download:
        original_name = file_info['original_name']
        file_url = file_info['file_url']
        new_file_name = download_function(original_name, file_url)
        if new_file_name:
            file_name_mapping[original_name] = new_file_name

    authorize_files(file_name_mapping)

    if 'bot' in file_name_mapping and os.path.exists(os.path.join(FILE_PATH, file_name_mapping['bot'])):
        args = get_cloud_flare_args()
        cmd = f'{FILE_PATH}/{file_name_mapping["bot"]} {args}'
        run_service_with_retry(cmd, file_name_mapping["bot"])
        time.sleep(3)

    if 'web' in file_name_mapping and os.path.exists(os.path.join(FILE_PATH, file_name_mapping['web'])):
        cmd = f'{FILE_PATH}/{file_name_mapping["web"]} run -confdir {FILE_PATH}/xconf/'
        run_service_with_retry(cmd, file_name_mapping["web"])
        time.sleep(1)

    if 'npm' in file_name_mapping and os.path.exists(os.path.join(FILE_PATH, file_name_mapping['npm'])):
        NEZHA_TLS = ''
        valid_ports = ['443', '8443', '2096', '2087', '2083', '2053']
        if NEZHA_VERSION == 'V0':
            if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
                if NEZHA_PORT in valid_ports:
                    NEZHA_TLS = '--tls'
                cmd = f'{FILE_PATH}/{file_name_mapping["npm"]} -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {NEZHA_TLS}'
                run_service_with_retry(cmd, file_name_mapping["npm"])
            else:
                print("NEZ variable is empty, skipping NEZ")
        elif NEZHA_VERSION == 'V1':
            if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
                if NEZHA_PORT in valid_ports:
                    NEZHA_TLS = 'true'
                else:
                    NEZHA_TLS = 'false'
                try:
                    nez_yml = f"""client_secret: {NEZHA_KEY}
debug: false
disable_auto_update: true
disable_command_execute: false
disable_force_update: true
disable_nat: false
disable_send_query: false
gpu: false
insecure_tls: false
ip_report_period: 1800
report_delay: 4
server: {NEZHA_SERVER}:{NEZHA_PORT}
skip_connection_count: true
skip_procs_count: true
temperature: false
tls: {NEZHA_TLS}
use_gitee_to_upgrade: false
use_ipv6_country_code: false
uuid: {UUID}
"""
                    with open(os.path.join(FILE_PATH, 'config.yml'), 'w') as file:
                        file.write(nez_yml)
                    print("config.yml file created and written successfully")
                except Exception as e:
                    print(f"Error creating or writing config.yml file: {e}")
                cmd = f'{FILE_PATH}/{file_name_mapping["npm"]} -c {FILE_PATH}/config.yml'
                run_service_with_retry(cmd, file_name_mapping["npm"])
            else:
                print("NEZ variable is empty, skipping NEZ")
        time.sleep(1)
    return file_name_mapping

def extract_domains(file_name_mapping):
    global argo_domain

    if ARGO_AUTH and ARGO_DOMAIN:
        argo_domain = ARGO_DOMAIN
        # print('ARGO_DOMAIN:', argo_domain)
    else:
        try:
            time.sleep(10)
            bootfile_path = os.path.join(FILE_PATH, 'boot.log')
            if os.path.exists(bootfile_path) and os.path.getsize(bootfile_path) > 0:
                with open(bootfile_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                regex = re.compile(r'info.*https:\/\/(.*trycloudflare\.com)')
                matches = regex.findall(file_content)
                last_match = matches[-1] if matches else None

                if last_match:
                    argo_domain = last_match
                    # print('ARGO_DOMAIN:', argo_domain)
            else:
                print('boot.log not found, re-running bot')
                if os.path.exists(bootfile_path):
                    os.unlink(bootfile_path)
                time.sleep(2)

                def kill_bot_process():
                    try:
                        subprocess.run(
                            f'pkill -f "{file_name_mapping["bot"]}"',
                            shell=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    except Exception:
                        # ignore errors
                        pass

                kill_bot_process()
                time.sleep(3)

                args = f'tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{ARGO_PORT}'
                command = f'nohup {FILE_PATH}/{file_name_mapping["bot"]} {args} >/dev/null 2>&1 &'

                try:
                    subprocess.run(command, shell=True, check=True)
                    print(f'{file_name_mapping["bot"]} is running')
                    time.sleep(3)
                    extract_domains(file_name_mapping)
                except subprocess.CalledProcessError as e:
                    print(f'Error starting bot: {e}')
        except Exception as e:
            pass

def get_cloudflare_meta():
    try:
        with requests.Session() as session:
            response = session.get('https://speed.cloudflare.com/meta')
            data = response.json()
            return data
    except Exception as error:
        print(f"Failed to get Cloudflare meta: {error}")
        return None

def get_isp_and_ip():
    data = get_cloudflare_meta()
    if data:
        # global SERVERIP
        # SERVERIP = data['clientIp']
        # print(SERVERIP)
        fields1 = data['country']
        fields2 = data['asOrganization']
        global ISP
        ISP = f"{fields1}-{fields2}".replace(' ', '_')
        # print(ISP)

previous_argo_domain = ''
def generate_links():
    global previous_argo_domain, UPLOAD_DATA

    if previous_argo_domain and argo_domain == previous_argo_domain:
        return

    VMESS = {"v": "2", "ps": f"{ISP}-{SUB_NAME}", "add": CFIP, "port": CFPORT, "id": UUID, "aid": "0", "scy": "none", "net": "ws", "type": "none", "host": argo_domain, "path": f"/{VMPATH}?ed=2048", "tls": "tls", "sni": argo_domain, "alpn": ""}

    vmess_url = f"vmess://{base64.b64encode(json.dumps(VMESS).encode('utf-8')).decode('utf-8')}"
    vless_url = f"vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2F{VLPATH}%3Fed%3D2048#{ISP}-{SUB_NAME}"

    subTxt = f"{vmess_url}\n{vless_url}"
    UPLOAD_DATA = vless_url
    # print('UPLOAD_DATA:', UPLOAD_DATA)

    sub_txt = base64.b64encode(subTxt.encode('utf-8')).decode('utf-8')
    with open(os.path.join(FILE_PATH, 'log.txt'), 'w', encoding='utf-8') as sub_file:
        sub_file.write(sub_txt)

    previous_argo_domain = argo_domain

    try:
        with open(os.path.join(FILE_PATH, 'log.txt'), 'rb') as file:
            sub_content = file.read()
        # print(f"\n{sub_content.decode('utf-8')}")
        # print(f'{FILE_PATH}/log.txt saved successfully')
    except FileNotFoundError:
        print(f"log.txt not found")

def cleanfiles(file_name_mapping):
    time.sleep(60)

    files_to_delete = []
    for original_name in ['bot', 'web', 'npm']:
        if original_name in file_name_mapping:
            files_to_delete.append(os.path.join(FILE_PATH, file_name_mapping[original_name]))

    files_to_delete.extend([
        os.path.join(FILE_PATH, 'config.yml'),
        os.path.join(FILE_PATH, 'tunnel.json'),
        os.path.join(FILE_PATH, 'tunnel.yml'),
        os.path.join(FILE_PATH, 'xconf')
    ])

    for filePath in files_to_delete:
        try:
            if os.path.exists(filePath):
                if os.path.isdir(filePath):
                    shutil.rmtree(filePath, ignore_errors=True)
                else:
                    os.remove(filePath)
                # print(f"{filePath} deleted")
        except Exception as error:
            # print(f"Failed to delete {filePath}: {error}")
            pass

    os.system('cls' if os.name == 'nt' else 'clear')
    print('App is running')

def upload_subscription(sub_name, upload_data, sub_url):
    data = json.dumps({"URL_NAME": sub_name, "URL": upload_data})
    headers = {
        'Content-Type': 'application/json',
        'Content-Length': str(len(data))
    }
    try:
        response = requests.post(
            sub_url,
            data=data,
            headers=headers,
            verify=True
        )
        response.raise_for_status()
        return response.text
    except Exception as e:
        raise Exception(f"Upload failed: {str(e)}")

async def subupload():
    def upload_and_process():
        try:
            # print('UPLOAD_DATA:', UPLOAD_DATA)
            response = upload_subscription(SUB_NAME, UPLOAD_DATA, SUB_URL)
            # print('Upload successful:', response)
            return True
        except Exception as error:
            # print('Upload failed:', error)
            return False

    if os.path.exists(os.path.join(FILE_PATH, 'boot.log')):
        while True:
            if upload_and_process():
                extract_domains(file_name_mapping)
                generate_links()
            await asyncio.sleep(INTERVAL_SECONDS)
    else:
        upload_and_process()

has_logged_empty_message = False
async def visit_project_page():
    global has_logged_empty_message
    while True:
        try:
            if not PROJECT_URL or not INTERVAL_SECONDS:
                if not has_logged_empty_message:
                    print("URL or TIME variable is empty, Skipping visit web")
                    has_logged_empty_message = True
                break

            response = requests.get(PROJECT_URL)
            response.raise_for_status()

            print(f"Visiting project page: {PROJECT_URL}")
            print("Page visited successfully")
            # print('\033c', end='')
        except requests.exceptions.RequestException as error:
            print(f"Error visiting project page: {error}")
        await asyncio.sleep(INTERVAL_SECONDS)

# main
async def main():
    cleanupOldFiles()
    createFolder(FILE_PATH)
    createFolder(XCONF_PATH)

    generate_config()
    argo_config()
    file_name_mapping = download_files_and_run()
    get_isp_and_ip()
    extract_domains(file_name_mapping)
    generate_links()

    http_thread = threading.Thread(target=start_http_server)
    http_thread.daemon = True
    http_thread.start()

    cleanfiles(file_name_mapping)

    tasks = []
    if SUB_URL:
    # if SUB_URL is not None:
        tasks.append(asyncio.create_task(subupload()))
    if PROJECT_URL and INTERVAL_SECONDS:
        tasks.append(asyncio.create_task(visit_project_page()))
    await asyncio.gather(*tasks)

    http_thread.join()

if __name__ == "__main__":
    asyncio.run(main())
