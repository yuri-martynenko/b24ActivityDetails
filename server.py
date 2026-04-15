import http.server, urllib.request, urllib.parse, os

API_KEY  = 'vibe_api_LPzpJuecyBB8QcrWN2W7mIk32F2c0y24_dc8d4f'
API_BASE = 'https://vibecode.bitrix24.tech/v1'
STATIC   = '/opt/app/b24ActivityDetails-main'

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, f, *a): pass

    def cors(self):
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','*')

    def do_OPTIONS(self):
        self.send_response(200); self.cors(); self.end_headers()

    def proxy(self, api_path, query):
        url = API_BASE + api_path + ('?'+query if query else '')
        try:
            req = urllib.request.Request(url, headers={'X-Api-Key': API_KEY})
            with urllib.request.urlopen(req, timeout=60) as r:
                chunks = []
                while True:
                    c = r.read(65536)
                    if not c: break
                    chunks.append(c)
                data = b''.join(chunks)
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.cors(); self.end_headers()
            self.wfile.write(data); self.wfile.flush()
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type','application/json')
            self.cors(); self.end_headers(); self.wfile.write(body)
        except Exception as e:
            err = ('{"error":"%s"}' % str(e).replace('"','')).encode()
            self.send_response(502)
            self.send_header('Content-Type','application/json')
            self.cors(); self.end_headers(); self.wfile.write(err)

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        path, query = p.path, p.query
        # /api/... -> proxy to activities endpoint
        if path.startswith('/api/'):
            self.proxy(path[4:], query)
            return
        # /api_entity/... -> proxy to any entity endpoint
        if path.startswith('/api_entity/'):
            self.proxy(path[11:], query)
            return
        # Static files
        fp = path if path != '/' else '/index.html'
        full = STATIC + fp
        if os.path.isfile(full):
            ext = full.rsplit('.',1)[-1].lower()
            ct = {'html':'text/html;charset=utf-8','js':'application/javascript','css':'text/css'}.get(ext,'text/plain')
            data = open(full,'rb').read()
            self.send_response(200)
            self.send_header('Content-Type',ct)
            self.send_header('Content-Length',str(len(data)))
            self.cors(); self.end_headers(); self.wfile.write(data)
        else:
            self.send_response(404); self.end_headers()

http.server.ThreadingHTTPServer(('',3000),H).serve_forever()
