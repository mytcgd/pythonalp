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
AUTO_ACCESS = os.environ.get('AUTO_ACCESS', 'false').lower() == 'true'
BAOHUO_URL = os.environ.get('BAOHUO_URL', 'tcgd.serv00.net')
INTERVAL_SECONDS = int(os.environ.get("TIME", 100))
CFIP = os.environ.get('CFIP', 'ip.sb')
PORT = int(os.environ.get('SERVER_PORT') or os.environ.get('PORT') or 3000)
OPENSERVER = os.environ.get('OPENSERVER', 'true').lower() == 'true'
V_PORT = int(os.environ.get('V_PORT', 8080))
CFPORT = int(os.environ.get('CFPORT', 443))
SUB_URL = os.environ.get('SUB_URL', '')

VLPATH = os.environ.get('VLPATH', '')
XHPPATH = os.environ.get('XHPPATH', '')

UUID = os.environ.get('UUID', '')
NEZHA_VERSION = os.environ.get('NEZHA_VERSION', 'V0')
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', '')
NEZHA_KEY = os.environ.get('NEZHA_KEY', '')
NEZHA_PORT = os.environ.get('NEZHA_PORT', '443')
SUB_NAME = os.environ.get('SUB_NAME', '')
MY_DOMAIN = os.environ.get('MY_DOMAIN', '')

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
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

def start_http_server():
    server = HTTPServer(('0.0.0.0', PORT), MyHandler)
    print('server is running on port :', PORT)
    server.serve_forever()

def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def add_visit_task():
    if not AUTO_ACCESS or not MY_DOMAIN:
        print("Skipping adding automatic access task")
        return

    try:
        response = requests.post(
            'https://{BAOHUO_URL}/add-url',
            json={"url": MY_DOMAIN},
            headers={"Content-Type": "application/json"}
        )
        print('automatic access task added successfully')
    except Exception as e:
        print(f'Failed to add URL: {e}')

def kill_bot_process(process_name):
    try:
        pidof_cmd = f"pidof {process_name}"
        pid_result = subprocess.run(pidof_cmd, shell=True, check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True)
        pid = pid_result.stdout.strip()

        if not pid:
            print(f"Process '{process_name}' not found.")
            return

        kill_cmd = f"kill -9 {pid}"
        kill_result = subprocess.run(kill_cmd, shell=True, check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)

        print(f"Process '{process_name}' killed successfully.")

    except subprocess.CalledProcessError as e:
        if "No such process" in e.stderr or "No such process" in e.stdout:
            print(f"Process '{process_name}' not found.")
        else:
            print(f"Error killing process {process_name}: {e.stderr.strip()}")

    except Exception as e:
        print(f"Unexpected error killing process {process_name}: {str(e)}")

def generate_config():
    vlpath = '/' + str(VLPATH)
    xhppath = '/' + str(XHPPATH)
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
        }
    };
    with open(os.path.join(XCONF_PATH, 'inbound.json'), 'w', encoding='utf-8') as inbound_file:
        json.dump(inbound, inbound_file, ensure_ascii=False, indent=2)

    if VLPATH:
        inbound_v = {
            "inbounds": [
                {
                    "port": V_PORT,
                    "listen": "::",
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
                }
            ]
        };
        with open(os.path.join(XCONF_PATH, 'inbound_v.json'), 'w', encoding='utf-8') as inbound_v_file:
            json.dump(inbound_v, inbound_v_file, ensure_ascii=False, indent=2)
    elif XHPPATH:
        inbound_v = {
            "inbounds": [
                {
                    "port": V_PORT,
                    "listen": "::",
                    "protocol": "vless",
                    "settings": {
                        "clients": [
                            {
                                "id": UUID
                            }
                        ],
                        "decryption": "none"
                    },
                    "streamSettings": {
                        "network": "xhttp",
                        "security": "none",
                        "xhttpSettings": {
                            "mode": "packet-up",
                            "path": xhppath
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
        with open(os.path.join(XCONF_PATH, 'inbound_v.json'), 'w', encoding='utf-8') as inbound_v_file:
            json.dump(inbound_v, inbound_v_file, ensure_ascii=False, indent=2)

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
    service: http://localhost:{V_PORT}
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
    if re.match(r"^[A-Z0-9a-z=]{120,250}$", ARGO_AUTH):
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 run --token {ARGO_AUTH}"
    elif "TunnelSecret" in ARGO_AUTH:
        args = f"tunnel --edge-ip-version auto --config {FILE_PATH}/tunnel.yml run"
    else:
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{V_PORT}"
    return args

def get_files_for_architecture():
    arch = os.uname().machine
    if arch in ['arm', 'arm64', 'aarch64']:
        base_files = [
            {'file_name': 'web', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/xray_arm'},
        ]
        if OPENSERVER:
            base_files.append({'file_name': 'bot', 'file_url': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64'})
        if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
            if NEZHA_VERSION == 'V0':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/kahunama/myfile/releases/download/main/nezha-agent_arm'})
            elif NEZHA_VERSION == 'V1':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/nezha-agentv1_arm'})
    else:
        base_files = [
            {'file_name': 'web', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/xray'},
        ]
        if OPENSERVER:
            base_files.append({'file_name': 'bot', 'file_url': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64'})
        if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
            if NEZHA_VERSION == 'V0':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/kahunama/myfile/releases/download/main/nezha-agent'})
            elif NEZHA_VERSION == 'V1':
                base_files.append({'file_name': 'npm', 'file_url': 'https://github.com/mytcgd/myfiles/releases/download/main/nezha-agentv1'})
    return base_files

def authorize_files(file_name_mapping):
    new_permissions = 0o775
    for file_name, new_file_name in file_name_mapping.items():
        absolute_file_path = os.path.join(FILE_PATH, new_file_name)
        try:
            os.chmod(absolute_file_path, new_permissions)
            print(f"Empowerment success for {absolute_file_path} ({file_name}): {oct(new_permissions)}")
        except Exception as e:
            print(f"Empowerment failed for {absolute_file_path} ({file_name}): {e}")

def download_function(file_name, file_url):
    random_file_name = generate_random_string(5)
    file_path = os.path.join(FILE_PATH, random_file_name)
    try:
        with requests.get(file_url, stream=True) as response, open(file_path, 'wb') as file:
            shutil.copyfileobj(response.raw, file)
        print(f"Downloaded {file_name} (renamed to {random_file_name}) successfully")
        return random_file_name
    except Exception as e:
        print(f"Download {file_name} (renamed to {random_file_name}) failed: {e}")
        return None

def run_service_with_retry(cmd, service_name, max_retries=3):
    for attempt in range(max_retries):
        try:
            process = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # process = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)

            if process.poll() is None:
                print(f"{service_name} is running")
                return True
            else:
                if attempt < max_retries - 1:
                    print(f"{service_name} failed to start, retrying... ({attempt + 1}/{max_retries})")
                    if process.poll() is None:
                        process.kill()
                    time.sleep(1)
        except Exception as e:
            print(f"Startup exception: {e}")
            if attempt >= max_retries - 1:
                return False
            continue

    print(f"{service_name} failed to start after {max_retries} attempts")
    return False

def download_files_and_run():
    file_name_mapping = {}
    files_to_download = get_files_for_architecture()
    if not files_to_download:
        print("Can't find a file for the current architecture")
        return

    for file_info in files_to_download:
        file_name = file_info['file_name']
        file_url = file_info['file_url']
        new_file_name = download_function(file_name, file_url)
        if new_file_name:
            file_name_mapping[file_name] = new_file_name

    authorize_files(file_name_mapping)

    if OPENSERVER:
        if 'bot' in file_name_mapping and os.path.exists(os.path.join(FILE_PATH, file_name_mapping['bot'])):
            argo_config()
            args = get_cloud_flare_args()
            cmd = f'{FILE_PATH}/{file_name_mapping["bot"]} {args}'
            run_service_with_retry(cmd, file_name_mapping["bot"])
            time.sleep(5)
        else:
            print("bot file not found, skip running")
    else:
        print("bot is not allowed, skip running")

    if 'web' in file_name_mapping and os.path.exists(os.path.join(FILE_PATH, file_name_mapping['web'])):
        cmd = f'{FILE_PATH}/{file_name_mapping["web"]} run -confdir {FILE_PATH}/xconf'
        run_service_with_retry(cmd, file_name_mapping["web"])
        time.sleep(1)
    else:
        print("web file not found, skip running")

    if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
        if 'npm' in file_name_mapping and os.path.exists(os.path.join(FILE_PATH, file_name_mapping['npm'])):
            NEZHA_TLS = ''
            valid_ports = ['443', '8443', '2096', '2087', '2083', '2053']
            if NEZHA_VERSION == 'V0':
                if NEZHA_PORT in valid_ports:
                    NEZHA_TLS = '--tls'
                cmd = f'{FILE_PATH}/{file_name_mapping["npm"]} -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {NEZHA_TLS} --report-delay=4 --skip-conn --skip-procs --disable-auto-update'
                run_service_with_retry(cmd, file_name_mapping["npm"])
            elif NEZHA_VERSION == 'V1':
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
                    print("Error creating or writing config.yml file: {e}")
                cmd = f'{FILE_PATH}/{file_name_mapping["npm"]} -c {FILE_PATH}/config.yml'
                run_service_with_retry(cmd, file_name_mapping["npm"])
            time.sleep(1)
        else:
            print("npm file not found, skip running")
    else:
        print("npm variable is empty, skip running")
    return file_name_mapping

def extract_domains(file_name_mapping):
    argo_domain = ''
    if OPENSERVER:
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
                    return argo_domain
                else:
                    print('boot.log not found, re-running bot')
                    if os.path.exists(bootfile_path):
                        os.unlink(bootfile_path)
                    time.sleep(1)
                    kill_bot_process(file_name_mapping["bot"])
                    time.sleep(1)

                    args = f'tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{V_PORT}'
                    command = f'{FILE_PATH}/{file_name_mapping["bot"]} {args}'

                    run_service_with_retry(command, file_name_mapping["bot"])
                    time.sleep(5)
                    extract_domains()
            except Exception as e:
                pass
    else:
        if MY_DOMAIN:
            argo_domain = MY_DOMAIN
    return argo_domain

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
        ISP = f"{fields1}-{fields2}".replace(' ', '_')
        # print(ISP)
        return ISP

previous_argo_domain = ''
def generate_links(ISP, argo_domain):
    global previous_argo_domain, UPLOAD_DATA
    if previous_argo_domain and argo_domain == previous_argo_domain:
        # print('previous_argo_domain:', previous_argo_domain)
        return

    if VLPATH:
        vless_url = f"vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2F{VLPATH}%3Fed%3D2560#{ISP}-{SUB_NAME}"
    elif XHPPATH:
        vless_url = f"vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=xhttp&host={argo_domain}&path=%2F{XHPPATH}%3Fed%3D2560&mode=packet-up#{ISP}-{SUB_NAME}"

    subTxt = vless_url
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

async def cleanfiles(file_name_mapping):
    await asyncio.sleep(60)

    files_to_delete = []
    for file_name in ['bot', 'web', 'npm']:
        if file_name in file_name_mapping:
            files_to_delete.append(os.path.join(FILE_PATH, file_name_mapping[file_name]))

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

async def upload_subscription(sub_name, upload_data, sub_url):
    def _sync_upload():
        data = json.dumps({"URL_NAME": sub_name, "URL": upload_data})
        headers = {'Content-Type': 'application/json', 'Content-Length': str(len(data))}
        try:
            response = requests.post(sub_url, data=data, headers=headers, verify=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_upload)

async def subupload(ISP, file_name_mapping):
    async def upload_and_process():
        try:
            response = await upload_subscription(SUB_NAME, UPLOAD_DATA, SUB_URL)
            # print('Upload successful:', response)
            argo_domain = extract_domains(file_name_mapping)
            generate_links(ISP, argo_domain)
            return True
        except Exception as error:
            # print('Upload failed:', error)
            return False

    if os.path.exists(os.path.join(FILE_PATH, 'boot.log')):
        while True:
            await upload_and_process()
            await asyncio.sleep(INTERVAL_SECONDS)
    else:
        await upload_and_process()

# main
async def main():
    cleanupOldFiles()
    createFolder(FILE_PATH)
    createFolder(XCONF_PATH)

    generate_config()
    file_name_mapping = download_files_and_run()
    ISP = get_isp_and_ip()
    argo_domain = extract_domains(file_name_mapping)
    generate_links(ISP, argo_domain)

    http_thread = threading.Thread(target=start_http_server, daemon=False)
    http_thread.start()

    add_visit_task()

    tasks = []
    tasks.append(asyncio.create_task(cleanfiles(file_name_mapping)))
    if SUB_URL:
        tasks.append(asyncio.create_task(subupload(ISP, file_name_mapping)))
    await asyncio.gather(*tasks)

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
