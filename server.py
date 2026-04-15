import http.server, urllib.request, urllib.parse, os, sys

API_KEY = 'vibe_api_LPzpJuecyBB8QcrWN2W7mIk32F2c0y24_dc8d4f'
API_BASE = 'https://vibecode.bitrix24.tech/v1'
STATIC_DIR = '/opt/app/b24ActivityDetails-main'

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, f, *a): pass

    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')

    def do_OPTIONS(self):
        self.send_response(200); self.cors(); self.end_headers()

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        if p.path.startswith('/api/'):
            url = API_BASE + p.path[4:]
            if p.query: url += '?' + p.query
            try:
                req = urllib.request.Request(url, headers={'X-Api-Key': API_KEY})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = r.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.cors(); self.end_headers(); self.wfile.write(data)
            except urllib.error.HTTPError as e:
                body = e.read()
                self.send_response(e.code)
                self.send_header('Content-Type','application/json')
                self.cors(); self.end_headers(); self.wfile.write(body)
            except Exception as e:
                self.send_response(502); self.cors(); self.end_headers()
                self.wfile.write(('{}').encode())
            return
        fp = p.path if p.path != '/' else '/index.html'
        full = STATIC_DIR + fp
        if os.path.isfile(full):
            ext = full.rsplit('.',1)[-1]
            ct = {'html':'text/html;charset=utf-8','js':'application/javascript','css':'text/css'}.get(ext,'text/plain')
            data = open(full,'rb').read()
            self.send_response(200); self.send_header('Content-Type',ct)
            self.cors(); self.end_headers(); self.wfile.write(data)
        else:
            self.send_response(404); self.end_headers()

http.server.ThreadingHTTPServer(('',3000),Handler).serve_forever()
