import http.server
import urllib.request
import urllib.parse
import json
import os

API_BASE = 'https://vibecode.bitrix24.tech/v1'
STATIC_DIR = '/opt/app/b24ActivityDetails-main'

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def add_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Vibe-Key, Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.add_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Proxy API calls
        if path.startswith('/api/'):
            api_path = path[4:]  # strip /api
            url = API_BASE + api_path
            if parsed.query:
                url += '?' + parsed.query
            key = self.headers.get('X-Vibe-Key', '')
            try:
                req = urllib.request.Request(url, headers={'X-Vibe-Key': key})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = r.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.add_cors()
                self.end_headers()
                self.wfile.write(data)
            except urllib.error.HTTPError as e:
                body = e.read()
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.add_cors()
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.add_cors()
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        # Serve static files
        file_path = path if path != '/' else '/index.html'
        full_path = STATIC_DIR + file_path
        if os.path.exists(full_path) and os.path.isfile(full_path):
            ext = full_path.rsplit('.', 1)[-1].lower()
            ct = {'html': 'text/html; charset=utf-8', 'js': 'application/javascript',
                  'css': 'text/css', 'json': 'application/json'}.get(ext, 'text/plain')
            with open(full_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.add_cors()
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server = http.server.ThreadingHTTPServer(('', 3000), Handler)
    print('Serving on :3000')
    server.serve_forever()
