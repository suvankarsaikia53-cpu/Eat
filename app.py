from flask import Flask, jsonify, request, render_template_string
import requests
from urllib.parse import urlparse, parse_qs
import warnings
from urllib3.exceptions import InsecureRequestWarning
import jwt
import base64
import json
import my_pb2
import output_pb2
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

warnings.filterwarnings("ignore", category=InsecureRequestWarning)

app = Flask(__name__)
app.json.sort_keys = False

AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'

PLATFORM_MAP = {
    3: "Facebook",
    4: "Guest",
    5: "VK",
    6: "Huawei",
    8: "Google",
    11: "X (Twitter)",
    13: "AppleId",
}

def decode_ff_name(b64_str):
    try:
        if not b64_str:
            return ""
        key = b"1e5898ccb8dfdd921f9bdea848768b64a201"
        b64_str = b64_str.strip()
        b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
        encrypted_bytes = base64.b64decode(b64_str)
        decrypted_bytes = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            key_byte = key[i % len(key)]
            decrypted_bytes.append(byte ^ key_byte)
        return decrypted_bytes.decode('utf-8', errors='ignore')
    except:
        return ""

def encrypt_message(plaintext):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded_message = pad(plaintext, AES.block_size)
    return cipher.encrypt(padded_message)

def extract_eat_from_url(user_input):
    if "http" in user_input or "?" in user_input:
        parsed_url = urlparse(user_input)
        query_params = parse_qs(parsed_url.query)
        if 'eat' in query_params:
            return query_params['eat'][0]
        return None
    return user_input.strip()

def get_access_token_from_eat(eat_token):
    api_url = f"https://api-otrss.garena.com/support/callback/?access_token={eat_token}"
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 Chrome/114.0.0.0 Mobile"}
    try:
        response = requests.get(api_url, headers=headers, allow_redirects=True, timeout=10)
        final_params = parse_qs(urlparse(response.url).query)
        if 'access_token' in final_params:
            return final_params['access_token'][0]
        return None
    except:
        return None

def fetch_open_id(access_token):
    try:
        url = f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        open_id = data.get("open_id")
        if not open_id:
            return None, "Failed to extract open_id from token"
        return open_id, None
    except Exception as e:
        return None, str(e)

def internal_generate_jwt(access_token, open_id=None):
    if not open_id:
        open_id, error = fetch_open_id(access_token)
        if error:
            return {"status": "error", "message": error}, 400

    platforms = [8, 3, 4, 6]

    for platform_type in platforms:
        game_data = my_pb2.GameData()
        game_data.timestamp = "2024-12-05 18:15:32"
        game_data.game_name = "free fire"
        game_data.game_version = 1
        game_data.version_code = "1.108.3"
        game_data.os_info = "Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)"
        game_data.device_type = "Handheld"
        game_data.network_provider = "Verizon Wireless"
        game_data.connection_type = "WIFI"
        game_data.screen_width = 1280
        game_data.screen_height = 960
        game_data.dpi = "240"
        game_data.cpu_info = "ARMv7 VFPv3 NEON VMH | 2400 | 4"
        game_data.total_ram = 5951
        game_data.gpu_name = "Adreno (TM) 640"
        game_data.gpu_version = "OpenGL ES 3.0"
        game_data.user_id = "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610"
        game_data.ip_address = "172.190.111.97"
        game_data.language = "en"
        game_data.open_id = open_id
        game_data.access_token = access_token
        game_data.platform_type = platform_type
        game_data.field_99 = str(platform_type)
        game_data.field_100 = str(platform_type)

        serialized_data = game_data.SerializeToString()
        encrypted_data = encrypt_message(serialized_data)

        url = "https://loginbp.ggpolarbear.com/MajorLogin"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54"
        }

        try:
            response = requests.post(url, data=encrypted_data, headers=headers, verify=False, timeout=5)
            if response.status_code == 200:
                example_msg = output_pb2.Garena_420()
                example_msg.ParseFromString(response.content)
                token_value = getattr(example_msg, "token", None)
                if token_value:
                    try:
                        decoded_token = jwt.decode(token_value, options={"verify_signature": False})
                    except AttributeError:
                        payload_b64 = token_value.split('.')[1]
                        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                        decoded_token = json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))

                    p_id = decoded_token.get("external_type")
                    p_name = PLATFORM_MAP.get(p_id, f"Unknown ({p_id})")
                    raw_nickname = decoded_token.get("nickname", "")
                    account_name = decode_ff_name(raw_nickname)
                    if not account_name:
                        import urllib.parse
                        account_name = urllib.parse.unquote(raw_nickname)

                    return {
                        "account_name": account_name,
                        "account_id": decoded_token.get("account_id"),
                        "platform": p_name,
                        "region": decoded_token.get("lock_region"),
                        "access_token": access_token,
                        "open_id": open_id,
                        "token": token_value,
                        "status": "success"
                    }, 200
        except:
            continue

    return {"status": "error", "message": "No valid platform found or all authentication attempts failed."}, 400

def process_eat_to_full_result(eat_input):
    eat_token = extract_eat_from_url(eat_input)
    if not eat_token:
        return {"status": "error", "message": "Could not extract eat token from input."}, 400

    access_token = get_access_token_from_eat(eat_token)
    if not access_token:
        return {"status": "error", "message": "Failed to resolve EAT to Access Token."}, 400

    result, status_code = internal_generate_jwt(access_token)
    return result, status_code

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>SPIDEY | Access Token Generator</title>
    
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.2/dist/confetti.browser.min.js"></script>

    <style>
        :root {
            --bg-dark: #01000E;
            --card-bg: rgba(12, 5, 50, 0.4);
            --border-color: rgba(167, 139, 250, 0.2);
            --glow-color: rgba(192, 132, 252, 0.6);
            --text-glow: #e0d5ff;
        }
        
        html { scroll-behavior: smooth; }
        body {
            font-family: 'Poppins', sans-serif;
            background-color: var(--bg-dark);
            color: #d9d2ff;
            overflow-x: hidden;
            margin: 0;
            padding: 0;
            -ms-overflow-style: none;
            scrollbar-width: none;
        }
        body::-webkit-scrollbar { display: none; }

        #vanta-bg {
            position: fixed;
            width: 100%; height: 100%;
            top: 0; left: 0;
            z-index: -1;
            pointer-events: none;
        }
        
        .gradient-text {
            background: linear-gradient(90deg, #c7d2fe, #fbcfe8, #c7d2fe);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: text-shimmer 4s linear infinite;
        }
        @keyframes text-shimmer { to { background-position: 200% center; } }

        .glass-card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 1.5rem;
        }
        .glass-card.glow-on-hover:hover {
            box-shadow: 0 0 40px var(--glow-color);
            border-color: var(--glow-color);
            transform: translateY(-4px);
        }

        .btn-glow {
            background: linear-gradient(90deg, #9333ea, #4f46e5);
            border: none;
            color: white;
            box-shadow: 0 0 15px rgba(139, 92, 246, 0.4);
            transition: all 0.3s;
        }
        .btn-glow:hover {
            box-shadow: 0 0 30px rgba(167, 139, 250, 0.8);
            transform: scale(1.02);
        }
        .btn-dark {
            background: rgba(30, 20, 70, 0.6);
            border: 1px solid rgba(167, 139, 250, 0.3);
            color: white;
            transition: 0.3s;
        }
        .btn-dark:hover {
            background: rgba(40, 30, 90, 0.8);
            box-shadow: 0 0 20px rgba(192, 132, 252, 0.4);
        }

        .form-input {
            background: rgba(12, 5, 50, 0.5);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            color: white;
            padding: 0.75rem 1rem;
            width: 100%;
            outline: none;
            transition: 0.3s;
            font-size: 0.875rem;
            font-family: 'Poppins', sans-serif;
        }
        .form-input:focus {
            border-color: var(--glow-color);
            box-shadow: 0 0 15px var(--glow-color);
        }

        .result-banner {
            padding: 0.75rem 1rem;
            border-radius: 0.75rem;
            font-size: 0.875rem;
            margin-top: 1rem;
            display: none;
        }
        .result-success { background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; color: #34d399; }
        .result-error { background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #f87171; }

        .provider-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 10px;
        }
        .provider-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(30, 20, 70, 0.6);
            border: 1px solid rgba(167, 139, 250, 0.3);
            border-radius: 12px;
            padding: 12px 4px;
            color: #fff;
            text-decoration: none;
            font-size: 11px;
            transition: all 0.3s;
            text-align: center;
        }
        .provider-btn:hover {
            background: rgba(40, 30, 90, 0.8);
            border-color: #f472b6;
            transform: translateY(-2px);
            box-shadow: 0 0 20px rgba(192, 132, 252, 0.4);
        }
        .provider-btn i { font-size: 22px; margin-bottom: 4px; }
        .provider-btn .name { font-size: 10px; font-weight: 500; }

        .token-section {
            background: rgba(16, 185, 129, 0.05);
            border: 2px solid #10b981;
            border-radius: 1rem;
            margin-top: 1.5rem;
            padding: 1rem;
            position: relative;
        }
        .token-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        .token-header .label {
            color: #34d399;
            font-weight: 600;
            font-size: 0.9rem;
        }
        .copy-btn {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid #10b981;
            color: #34d399;
            padding: 0.4rem 1.2rem;
            border-radius: 2rem;
            font-size: 0.8rem;
            cursor: pointer;
            transition: 0.3s;
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }
        .copy-btn:hover {
            background: #10b981;
            color: #000;
        }
        .token-value {
            background: rgba(0,0,0,0.3);
            border-radius: 0.5rem;
            padding: 0.75rem;
            word-break: break-all;
            font-family: 'Courier New', monospace;
            color: #6ee7b7;
            font-size: 0.9rem;
        }

        .player-card {
            background: rgba(147, 51, 234, 0.08);
            border: 1px solid rgba(147, 51, 234, 0.4);
            border-radius: 1rem;
            padding: 1rem;
            margin-top: 1rem;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            font-size: 0.85rem;
        }
        .player-card .info-item {
            display: flex;
            flex-direction: column;
        }
        .player-card .label {
            color: #c084fc;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .player-card .value {
            color: #f3e8ff;
            font-weight: 500;
            word-break: break-all;
        }

        .json-toggle {
            background: rgba(168, 85, 247, 0.1);
            border: 1px solid rgba(168, 85, 247, 0.3);
            color: #c084fc;
            border-radius: 2rem;
            padding: 0.4rem 1.2rem;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 1rem;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .json-toggle:hover {
            background: rgba(168, 85, 247, 0.2);
        }
        .json-block {
            margin-top: 0.75rem;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(168, 85, 247, 0.4);
            border-radius: 0.75rem;
            padding: 0.75rem;
            font-family: 'Poppins', sans-serif;
            font-size: 0.80rem;
            color: #c4b5fd;
            white-space: pre-wrap;
            word-break: break-all;
            display: none;
            width: 100%;
            min-height: 150px;
            resize: vertical;
            outline: none;
            box-sizing: border-box;
            overflow-y: auto;
            max-height: 300px;
            line-height: 1.5;
        }
        .json-block.open { display: block; }

        @media (max-width: 500px) {
            .player-card { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body class="antialiased">

    <div id="vanta-bg"></div>

    <header class="fixed top-0 left-0 w-full z-50 glass-card !rounded-none !border-x-0 !border-t-0">
        <div class="container mx-auto px-6 py-4 flex justify-between items-center">
            <div class="text-2xl font-bold gradient-text text-glow">
                <i class="fa-solid fa-bolt mr-2"></i> SPIDEY
            </div>
            <a href="https://youtu.be/TFEQMlS2vOY?si=K-1iesJtnDNxdFpr" target="_blank" class="btn-dark px-4 py-2 rounded-lg text-sm flex items-center gap-2">
                <i class="fab fa-youtube"></i> FULL TUTORIAL
            </a>
        </div>
    </header>

    <main class="relative z-10 pt-28 pb-12 px-4">
        <div class="max-w-3xl mx-auto">
            <div class="glass-card p-6 mb-8" data-aos="fade-up">
                <h2 class="text-xl font-bold text-purple-300 mb-4"><i class="fas fa-circle-info mr-2"></i> HOW TO USE</h2>
                <div class="text-sm space-y-2 text-gray-300">
                    <p><span class="text-pink-400 font-semibold">1️⃣</span> Choose a provider and login with your Free Fire account.</p>
                    <p><span class="text-pink-400 font-semibold">2️⃣</span> After login, copy the full URL from the redirect page (contains <code class="bg-purple-900/40 px-1 rounded">eat=</code>).</p>
                    <p><span class="text-pink-400 font-semibold">3️⃣</span> Paste it below and click <strong>GENERATE</strong>.</p>
                    <div class="mt-3 p-2 bg-black/30 rounded text-xs text-green-300 break-all">
                        Example: https://discstore.recargajogo.com.br/?eat=14f06077...&lang=en...
                    </div>
                    <p class="text-xs text-gray-400 mt-2"><i class="fas fa-shield-alt text-green-400"></i> 100% Safe – Official Garena servers, no password needed.</p>
                </div>
            </div>

            <div class="glass-card p-6 mb-8" data-aos="fade-up" data-aos-delay="100">
                <h3 class="text-lg font-semibold text-purple-300 mb-4"><i class="fas fa-right-to-bracket mr-2"></i> LOGIN WITH</h3>
                <div class="provider-grid">
                    <a href="https://auth.garena.com/universal/oauth?platform=8&response_type=code&locale=en-SG&client_id=100067&redirect_uri=https://api.ff.garena.co.id/auth/auth/callback_n?site=https://api-discountstore.gid.recargajogo.com.br/oauth/callback_redirect/" target="_blank" class="provider-btn">
                        <i class="fab fa-google text-red-500"></i>
                        <span class="name">Google</span>
                    </a>
                    <a href="https://auth.garena.com/universal/oauth?platform=3&response_type=code&locale=en-SG&client_id=100067&redirect_uri=https://api.ff.garena.co.id/auth/auth/callback_n?site=https://api-discountstore.gid.recargajogo.com.br/oauth/callback_redirect/" target="_blank" class="provider-btn">
                        <i class="fab fa-facebook-f text-blue-500"></i>
                        <span class="name">Facebook</span>
                    </a>
                    <a href="https://auth.garena.com/universal/oauth?platform=11&response_type=code&locale=en-SG&client_id=100067&redirect_uri=https://api.ff.garena.co.id/auth/auth/callback_n?site=https://api-discountstore.gid.recargajogo.com.br/oauth/callback_redirect/" target="_blank" class="provider-btn">
                        <i class="fab fa-x-twitter text-white"></i>
                        <span class="name">X</span>
                    </a>
                    <a href="https://auth.garena.com/universal/oauth?platform=10&response_type=code&locale=en-SG&client_id=100067&redirect_uri=https://api.ff.garena.co.id/auth/auth/callback_n?site=https://api-discountstore.gid.recargajogo.com.br/oauth/callback_redirect/" target="_blank" class="provider-btn">
                        <i class="fab fa-apple text-gray-300"></i>
                        <span class="name">Apple</span>
                    </a>
                    <a href="https://auth.garena.com/universal/oauth?platform=5&response_type=code&locale=en-SG&client_id=100067&redirect_uri=https://api.ff.garena.co.id/auth/auth/callback_n?site=https://api-discountstore.gid.recargajogo.com.br/oauth/callback_redirect/" target="_blank" class="provider-btn">
                        <i class="fab fa-vk text-blue-400"></i>
                        <span class="name">VK</span>
                    </a>
                    <a href="https://auth.garena.com/universal/oauth?platform=7&response_type=code&locale=en-SG&client_id=100067&redirect_uri=https://api.ff.garena.co.id/auth/auth/callback_n?site=https://api-discountstore.gid.recargajogo.com.br/oauth/callback_redirect/" target="_blank" class="provider-btn">
                        <i class="fa-solid fa-mobile-screen text-red-400"></i>
                        <span class="name">Huawei</span>
                    </a>
                </div>
            </div>

            <div class="glass-card p-6" data-aos="fade-up" data-aos-delay="200">
                <label class="text-sm text-purple-200 mb-2 block"><i class="fas fa-key mr-1"></i> Paste Eat Token or Full URL</label>
                <textarea id="eatInput" class="form-input" rows="3" placeholder="Paste your eat token or URL here..."></textarea>
                <button id="generateBtn" onclick="generateToken()" class="btn-glow w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 mt-4">
                    <span id="btnText"><i class="fas fa-wand-magic-sparkles"></i> GENERATE ACCESS</span>
                    <span id="btnSpinner" class="hidden"><i class="fas fa-spinner fa-spin"></i></span>
                </button>

                <div id="resultBanner" class="result-banner"></div>

                <div id="outputContainer" style="display: none;">
                    <div class="token-section">
                        <div class="token-header">
                            <span class="label"><i class="fas fa-key mr-1"></i> TOKEN ACCESS</span>
                            <button class="copy-btn" onclick="copyToken()"><i class="fas fa-copy"></i> COPY</button>
                        </div>
                        <div id="tokenDisplay" class="token-value"></div>
                    </div>
                    <div id="playerCard" class="player-card" style="display: none;"></div>
                    <button id="jsonToggle" class="json-toggle" onclick="toggleJson()">
                        <i class="fas fa-code"></i> <span>Show Full Response</span>
                    </button>
                    <textarea id="jsonBlock" class="json-block" readonly rows="12"></textarea>
                </div>
            </div>
        </div>
    </main>

    <footer class="relative z-10 pb-8">
        <div class="max-w-3xl mx-auto px-4">
            <div class="glass-card p-6 flex flex-wrap justify-center items-center gap-4 text-sm">
                <a href="https://t.me/spideyabd" target="_blank" class="btn-dark px-4 py-2 rounded-full flex items-center gap-2">
                    <i class="fab fa-telegram"></i> SPIDEY
                </a>
                <a href="https://t.me/SPIDEYFREEFILES" target="_blank" class="btn-dark px-4 py-2 rounded-full flex items-center gap-2">
                    <i class="fab fa-telegram"></i> SPIDEY FREE FILES
                </a>
                <span class="text-gray-500">CREATED BY SPIDEY</span>
            </div>
        </div>
    </footer>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/vanta@latest/dist/vanta.waves.min.js"></script>

    <script>
        let fullResponseData = null;

        async function generateToken() {
            const input = document.getElementById('eatInput').value.trim();
            const btn = document.getElementById('generateBtn');
            const btnText = document.getElementById('btnText');
            const spinner = document.getElementById('btnSpinner');
            const resultBanner = document.getElementById('resultBanner');
            const outputContainer = document.getElementById('outputContainer');
            const tokenDisplay = document.getElementById('tokenDisplay');
            const playerCard = document.getElementById('playerCard');
            const jsonBlock = document.getElementById('jsonBlock');
            const jsonToggle = document.getElementById('jsonToggle');

            resultBanner.style.display = 'none';
            outputContainer.style.display = 'none';
            playerCard.style.display = 'none';
            jsonBlock.classList.remove('open');
            jsonToggle.querySelector('span').textContent = 'Show Full Response';
            jsonBlock.value = '';

            if (!input) {
                showBanner('error', 'Please paste an eat token or URL.');
                return;
            }

            btn.disabled = true;
            btnText.classList.add('hidden');
            spinner.classList.remove('hidden');

            try {
                const response = await fetch(`/generate?eat=${encodeURIComponent(input)}`);

                const data = await response.json();

                if (data.status === 'success') {
                    fullResponseData = data;
                    tokenDisplay.textContent = data.access_token;
                    outputContainer.style.display = 'block';
                    if (data.account_name || data.account_id) {
                        fillPlayerCard(data);
                        playerCard.style.display = 'grid';
                    }
                    showBanner('success', '✅ Access token generated successfully!');
                    launchConfetti();
                } else {
                    fullResponseData = null;
                    showBanner('error', '❌ ' + (data.message || 'Unknown error'));
                }
            } catch (error) {
                showBanner('error', '❌ Network error. Please try again.');
                fullResponseData = null;
            } finally {
                btn.disabled = false;
                btnText.classList.remove('hidden');
                spinner.classList.add('hidden');
            }
        }

        function fillPlayerCard(info) {
            const card = document.getElementById('playerCard');
            card.innerHTML = `
                <div class="info-item"><span class="label">Nickname</span><span class="value">${esc(info.account_name || 'N/A')}</span></div>
                <div class="info-item"><span class="label">Account ID</span><span class="value">${esc(info.account_id || 'N/A')}</span></div>
                <div class="info-item"><span class="label">Region</span><span class="value">${esc(info.region || 'N/A')}</span></div>
                <div class="info-item"><span class="label">Open ID</span><span class="value">${esc(info.open_id || 'N/A')}</span></div>
            `;
        }

        function toggleJson() {
            const jsonBlock = document.getElementById('jsonBlock');
            const toggleBtn = document.getElementById('jsonToggle');
            const span = toggleBtn.querySelector('span');
            if (!fullResponseData) return;
            if (jsonBlock.classList.contains('open')) {
                jsonBlock.classList.remove('open');
                span.textContent = 'Show Full Response';
            } else {
                jsonBlock.value = JSON.stringify(fullResponseData, null, 2);
                jsonBlock.classList.add('open');
                span.textContent = 'Hide Full Response';
            }
        }

        function esc(text) {
            return String(text).replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
        }

        function showBanner(type, msg, append = false) {
            const banner = document.getElementById('resultBanner');
            if (!append) banner.innerHTML = '';
            banner.style.display = 'block';
            banner.className = `result-banner ${type === 'success' ? 'result-success' : 'result-error'}`;
            banner.innerHTML += msg;
            if (!append) setTimeout(() => { banner.style.display = 'none'; }, 5000);
        }

        function copyToken() {
            const token = document.getElementById('tokenDisplay').textContent;
            navigator.clipboard.writeText(token).then(() => {
                const btn = document.querySelector('.copy-btn');
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check"></i> COPIED!';
                setTimeout(() => { btn.innerHTML = originalHTML; }, 2000);
            });
        }

        function launchConfetti() {
            confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 } });
            setTimeout(() => {
                confetti({ particleCount: 100, angle: 60, spread: 55, origin: { x: 0 } });
                confetti({ particleCount: 100, angle: 120, spread: 55, origin: { x: 1 } });
            }, 200);
        }

        document.addEventListener('DOMContentLoaded', () => {
            AOS.init({ once: true, duration: 800, offset: 50 });

            VANTA.WAVES({
                el: "#vanta-bg",
                mouseControls: true,
                touchControls: true,
                gyroControls: false,
                minHeight: 200.00,
                minWidth: 200.00,
                scale: 1.00,
                scaleMobile: 1.00,
                color: 0x20023,
                shininess: 25.00,
                waveHeight: 15.00,
                waveSpeed: 0.75,
                zoom: 0.85
            });

            document.getElementById('eatInput').addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    generateToken();
                }
            });
        });
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/generate", methods=["GET"])
def generate_token():
    eat_input = request.args.get("eat", "").strip()
    if not eat_input:
        return jsonify({"status": "error", "message": "Missing 'eat' parameter"}), 400

    result, status_code = process_eat_to_full_result(eat_input)
    return jsonify(result), status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1080, debug=True)