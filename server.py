import http.server, urllib.request, urllib.parse, os

API_KEY = 'vibe_api_LPzpJuecyBB8QcrWN2W7mIk32F2c0y24_dc8d4f'
API_BASE = 'https://vibecode.bitrix24.tech/v1'
STATIC_DIR = '/opt/app/b24ActivityDetails-main'

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, f, *a): pass

    def cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')

    def do_OPTIONS(self):
        self.send_response(200)
        self.cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path.startswith('/api/'):
            api_path = parsed.path[4:]  # /api/activities -> /activities
            url = API_BASE + api_path
            if parsed.query:
                url += '?' + parsed.query
            try:
                req = urllib.request.Request(url, headers={'X-Api-Key': API_KEY})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    # Read ALL data in chunks to avoid truncation
                    chunks = []
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        chunks.append(chunk)
                    data = b''.join(chunks)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.cors_headers()
                self.end_headers()
                self.wfile.write(data)
                self.wfile.flush()
            except urllib.error.HTTPError as e:
                body = e.read()
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.cors_headers()
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                err = '{"error": "' + str(e).replace('"', '') + '"}'
                self.send_response(502)
                self.send_header('Content-Type', 'application/json')
                self.cors_headers()
                self.end_headers()
                self.wfile.write(err.encode())
            return

        # Static files
        file_path = parsed.path if parsed.path != '/' else '/index.html'
        full_path = STATIC_DIR + file_path
        if os.path.isfile(full_path):
            ext = full_path.rsplit('.', 1)[-1].lower()
            ct = {'html': 'text/html; charset=utf-8', 'js': 'application/javascript',
                  'css': 'text/css', 'json': 'application/json'}.get(ext, 'text/plain')
            with open(full_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', str(len(data)))
            self.cors_headers()
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server = http.server.ThreadingHTTPServer(('', 3000), Handler)
    server.serve_forever()
