#!/usr/bin/env python3
"""Persistent EasyOCR HTTP worker for sq_plate_ocr_bridge_4p2.py.

The service accepts a JPEG from the ROS robot and returns OCR JSON. Bind only
to a trusted local or VMware adapter, for example:
  python3 tools/plate_ocr_server_4p2.py --host 192.168.232.1 --port 8765
"""
import argparse
import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer

import easyocr

from plate_ocr_4p2 import recognize


def make_handler(reader):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode('utf8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/health':
                self.respond(200, {'ready': True})
            else:
                self.respond(404, {'error': 'unknown path'})

        def do_POST(self):
            if self.path != '/ocr':
                self.respond(404, {'error': 'unknown path'})
                return
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 5000000:
                self.respond(413, {'error': 'invalid JPEG size'})
                return
            image = self.rfile.read(size)
            fd, path = tempfile.mkstemp(prefix='sq4_plate_', suffix='.jpg')
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(image)
                result = recognize(reader, path)
                result['image'] = self.headers.get('X-Task-Id', '')
                self.respond(200, result)
            except Exception as exc:
                self.respond(500, {'plate': None, 'error': str(exc)})
            finally:
                os.remove(path)

    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
    print('EasyOCR ready at %s:%d' % (args.host, args.port), flush=True)
    HTTPServer((args.host, args.port), make_handler(reader)).serve_forever()
