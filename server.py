import http.server, urllib.request, urllib.parse, os, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

API_KEY  = 'vibe_api_LPzpJuecyBB8QcrWN2W7mIk32F2c0y24_dc8d4f'
API_BASE = 'https://vibecode.bitrix24.tech/v1'
STATIC   = '/opt/app/b24ActivityDetails-main'

def api_get(path, params_str=''):
    url = API_BASE + path + ('?' + params_str if params_str else '')
    req = urllib.request.Request(url, headers={'X-Api-Key': API_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        chunks = []
        while True:
            c = r.read(65536)
            if not c: break
            chunks.append(c)
        return json.loads(b''.join(chunks))

def fetch_all_pages(path, base_qs):
    """Fetch all pages for given query string, return list of items."""
    all_items = []
    offset = 0
    while True:
        qs = base_qs + '&limit=50&offset=' + str(offset)
        data = api_get(path, qs)
        items = data.get('data', [])
        all_items.extend(items)
        if not data.get('meta', {}).get('hasMore', False):
            break
        offset += 50
    return all_items

def fetch_combo(owner_type_id, type_id, df, dt):
    """Fetch activities for one ownerTypeId+typeId combination."""
    qs = ('filter%5BownerTypeId%5D=' + str(owner_type_id) +
          '&filter%5BtypeId%5D=' + str(type_id) +
          '&filter%5BcreatedAt%5D%5Bfrom%5D=' + urllib.parse.quote(df + 'T00:00:00') +
          '&filter%5BcreatedAt%5D%5Bto%5D=' + urllib.parse.quote(dt + 'T23:59:59'))
    return fetch_all_pages('/activities', qs)

def fetch_names(ids, path):
    """Fetch entity names for list of IDs."""
    result = {}
    for i in range(0, len(ids), 50):
        batch = ids[i:i+50]
        qs = '&'.join('filter%5Bid%5D%5B' + str(j) + '%5D=' + str(bid)
                      for j, bid in enumerate(batch)) + '&limit=50'
        try:
            data = api_get(path, qs)
            for item in data.get('data', []):
                name = (item.get('title') or
                        ((item.get('name','') + ' ' + item.get('lastName','')).strip()) or
                        ('ID ' + str(item.get('id',''))))
                result[item['id']] = name
        except Exception:
            pass
    return result

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, f, *a): pass

    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')

    def do_OPTIONS(self):
        self.send_response(200); self.cors(); self.end_headers()

    def send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.cors()
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        path, query = p.path, p.query
        qs = urllib.parse.parse_qs(query)

        # /load — main endpoint: fetch all activities with filters
        if path == '/load':
            try:
                df = qs.get('df', [''])[0]
                dt = qs.get('dt', [''])[0]
                ents = qs.get('ents[]', qs.get('ents', []))
                types = qs.get('types[]', qs.get('types', []))
                stats = qs.get('stats[]', qs.get('stats', []))
                if not df or not dt:
                    self.send_json(400, {'error': 'df and dt required'}); return
                if not ents:
                    self.send_json(400, {'error': 'ents required'}); return
                if not types:
                    self.send_json(400, {'error': 'types required'}); return

                # Build combos and fetch in parallel
                combos = [(e, t) for e in ents for t in types]
                all_items = []
                seen = set()
                lock = Lock()

                def do_combo(e, t):
                    try:
                        return fetch_combo(e, t, df, dt)
                    except Exception as ex:
                        return []

                with ThreadPoolExecutor(max_workers=8) as pool:
                    futures = {pool.submit(do_combo, e, t): (e, t) for e, t in combos}
                    for future in as_completed(futures):
                        items = future.result()
                        with lock:
                            for item in items:
                                if item['id'] not in seen:
                                    seen.add(item['id'])
                                    all_items.append(item)

                # Client-side status filter
                if len(stats) < 2 and stats:
                    want = stats[0].lower() == 'true'
                    all_items = [a for a in all_items if bool(a.get('completed')) == want]

                # Sort by createdAt desc
                all_items.sort(key=lambda a: a.get('createdAt',''), reverse=True)

                # Fetch entity names in parallel
                ids_by_type = {1:[], 2:[], 3:[], 4:[]}
                for a in all_items:
                    ot = a.get('ownerTypeId')
                    if ot in ids_by_type:
                        ids_by_type[ot].append(a.get('ownerId'))

                entity_paths = {1:'/leads', 2:'/deals', 3:'/contacts', 4:'/companies'}
                name_maps = {}

                def load_names(ot):
                    ids = list(set(x for x in ids_by_type[ot] if x))
                    if not ids: return ot, {}
                    return ot, fetch_names(ids, entity_paths[ot])

                with ThreadPoolExecutor(max_workers=4) as pool:
                    for ot, nmap in pool.map(load_names, [1,2,3,4]):
                        name_maps[ot] = nmap

                # Fetch users
                umap = {}
                try:
                    udata = api_get('/users', 'limit=200')
                    for u in udata.get('data', []):
                        umap[u['id']] = ((u.get('name','') + ' ' + u.get('lastName','')).strip())
                except Exception:
                    pass

                # Build result rows
                TMAP = {1:'Встреча', 2:'Звонок', 4:'Email', 6:'Задача', 12:'Чат'}
                OMAP = {1:'Лид', 2:'Сделка', 3:'Контакт', 4:'Компания'}

                rows = []
                for a in all_items:
                    ot = a.get('ownerTypeId')
                    oid = a.get('ownerId')
                    nm = name_maps.get(ot, {})
                    rows.append({
                        'id': a.get('id'),
                        'otype': OMAP.get(ot, 'Type ' + str(ot)),
                        'oid': oid,
                        'oname': nm.get(oid, '—'),
                        'tname': TMAP.get(a.get('typeId'), 'Type ' + str(a.get('typeId'))),
                        'subj': a.get('subject') or '—',
                        'resp': umap.get(a.get('responsibleId'), 'ID ' + str(a.get('responsibleId',''))).strip(),
                        'cre': a.get('createdAt', ''),
                        'dl': a.get('deadline', ''),
                        'done': a.get('completed', False),
                        'desc': a.get('description', '')
                    })

                self.send_json(200, {'rows': rows, 'total': len(rows)})
            except Exception as e:
                self.send_json(500, {'error': str(e)})
            return

        # Static files
        fp = path if path != '/' else '/index.html'
        full = STATIC + fp
        if os.path.isfile(full):
            ext = full.rsplit('.',1)[-1].lower()
            ct = {'html':'text/html;charset=utf-8','js':'application/javascript','css':'text/css'}.get(ext,'text/plain')
            data = open(full,'rb').read()
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', str(len(data)))
            self.cors()
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404); self.end_headers()

if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('', 3000), H).serve_forever()
