
#RISHU PLEASE FOLLOW MY CHANNEL FOR HARD WORK ♥️♥️♥️
import re
from urllib.parse import unquote
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

def decode_nickname(encoded: str) -> str:
    try:
        return unquote(encoded, encoding='utf-8')
    except:
        return encoded

def extract_from_url_string(url_string):
    
    eat_token = None
    account_id = None
    nickname = None

    # Extract eat=...
    eat_match = re.search(r'[?&]eat=([^&]+)', url_string)
    if eat_match:
        eat_token = eat_match.group(1)
    else:
        
        hex_match = re.search(r'[a-fA-F0-9]{64,}', url_string)
        if hex_match:
            eat_token = hex_match.group(0)

    # Extract account_id=...
    acc_match = re.search(r'[?&]account_id=([^&]+)', url_string, re.IGNORECASE)
    if acc_match:
        account_id = acc_match.group(1)

    # Extract nickname=...
    nick_match = re.search(r'[?&]nickname=([^&]+)', url_string, re.IGNORECASE)
    if nick_match:
        encoded = nick_match.group(1)
        nickname = decode_nickname(encoded)

    return eat_token, account_id, nickname

def get_access_token_from_eat(eat_token):
    api_url = f"https://api-otrss.garena.com/support/callback/?access_token={eat_token}"
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 Chrome/114.0.0.0 Mobile"}
    try:
        response = requests.get(api_url, headers=headers, allow_redirects=True, timeout=10)
        qs = response.url.split('?', 1)[-1] if '?' in response.url else ''
        params = dict(pair.split('=') for pair in qs.split('&') if '=' in pair)
        return params.get('access_token')
    except Exception:
        return None

@app.route('/')
def home():
    return jsonify({
        "message": "EAT → Access Token API MADE BY RISHU CODEX",
        "usage": "GET /rishu?url=your url"
    })

@app.route('/rishu', methods=['GET', 'POST'])
def convert():
    input_data = None
    top_account_id = None
    top_nickname = None

    if request.method == 'GET':
        input_data = request.args.get('url') or request.args.get('eat')
        top_account_id = request.args.get('account_id')
        top_nickname = request.args.get('nickname')
    elif request.method == 'POST':
        data = request.get_json() or {}
        input_data = data.get('url') or data.get('eat')
        top_account_id = data.get('account_id')
        top_nickname = data.get('nickname')
        if not input_data:
            input_data = request.form.get('url') or request.form.get('eat')

    if not input_data:
        return jsonify({"error": "Missing 'url' or 'eat' parameter"}), 400

    
    eat_token, acc_id_from_url, nick_from_url = extract_from_url_string(input_data)

    
    if not eat_token:
        if re.match(r'^[a-fA-F0-9]{64,}$', input_data):
            eat_token = input_data

    if not eat_token:
        return jsonify({"error": "Could not extract EAT token from input"}), 400


    account_id = top_account_id or acc_id_from_url
    nickname = top_nickname or nick_from_url

    
    if nickname and '%' in nickname:
        nickname = decode_nickname(nickname)

    access_token = get_access_token_from_eat(eat_token)
    if not access_token:
        return jsonify({"error": "Failed to convert EAT to Access Token"}), 500

    return jsonify({
        "Nickname": nickname,
        "Account_id": account_id,
        "Access_token": access_token,
        "Original_url": input_data if ("http" in input_data or "?" in input_data) else None
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
