#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Интеграционный проектировщик v7.6 — сервер.

Запуск:  python app.py
Открыть: http://127.0.0.1:8110/
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import re
import sqlite3
import uuid

from engine import analyze
from report import markdown_report
import ui

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '8110'))
MAX_POST = int(os.environ.get('MAX_POST_BYTES', str(2 * 1024 * 1024)))
APP_DIR = Path(os.environ.get('APP_DIR', '.architect6'))
APP_DIR.mkdir(exist_ok=True)
DB = APP_DIR / 'runs.sqlite3'

RUN_RE = re.compile(r'^/run/([0-9a-f]{32})(\.md)?$')


def db():
    con = sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS runs '
                '(id TEXT PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP, '
                'payload TEXT, result TEXT)')
    return con


def save_run(payload, result):
    rid = uuid.uuid4().hex
    with db() as con:
        con.execute('INSERT INTO runs (id, payload, result) VALUES (?,?,?)',
                    (rid, json.dumps(payload, ensure_ascii=False),
                     json.dumps(result, ensure_ascii=False, default=str)))
    return rid


def load_run(rid):
    with db() as con:
        row = con.execute('SELECT result FROM runs WHERE id=?', (rid,)).fetchone()
    return json.loads(row[0]) if row else None


class Handler(BaseHTTPRequestHandler):
    server_version = 'Architect6'

    def _send(self, code, body, ctype='text/html; charset=utf-8'):
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            return self._send(200, ui.form_page())
        if self.path in ('/invariants', '/invariants.html'):
            return self._send(200, ui.invariant_reference_page())
        if self.path == '/health':
            return self._send(200, '{"ok":true}', 'application/json')
        m = RUN_RE.match(self.path)
        if m:
            res = load_run(m.group(1))
            if not res:
                return self._send(404, '<h1>Разбор не найден</h1>')
            if m.group(2):
                return self._send(200, markdown_report(res),
                                  'text/markdown; charset=utf-8')
            return self._send(200, ui.result_page(m.group(1), res))
        return self._send(404, '<h1>404</h1>')

    def do_POST(self):
        if self.path != '/api/analyze':
            return self._send(404, '{"ok":false}', 'application/json')
        length = int(self.headers.get('Content-Length') or 0)
        if length > MAX_POST:
            return self._send(413, json.dumps(
                {'ok': False, 'errors': ['Слишком большой запрос.']}), 'application/json')
        try:
            payload = json.loads(self.rfile.read(length).decode('utf-8') or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._send(400, json.dumps(
                {'ok': False, 'errors': ['Некорректный JSON.']}), 'application/json')
        res = analyze(payload)
        if not res['ok']:
            return self._send(200, json.dumps(res, ensure_ascii=False), 'application/json')
        rid = save_run(payload, res)
        return self._send(200, json.dumps({'ok': True, 'id': rid}), 'application/json')

    def log_message(self, fmt, *args):  # тихий лог
        pass


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f'Интеграционный проектировщик v7.6: http://127.0.0.1:{PORT}/')
    srv.serve_forever()


if __name__ == '__main__':
    main()
