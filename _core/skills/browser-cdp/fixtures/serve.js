// Tiny fixture server for testing browser-cdp. Usage: node fixtures/serve.js [port]  (default 8765)
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.argv[2] || 8765);

http
  .createServer((req, res) => {
    const u = new URL(req.url, `http://127.0.0.1:${port}`);
    if (u.pathname === '/' || u.pathname === '/index.html') {
      res.writeHead(200, { 'content-type': 'text/html', 'set-cookie': ['fixture_session=abc123secret; Path=/; HttpOnly'] });
      return res.end(fs.readFileSync(path.join(dir, 'index.html')));
    }
    if (u.pathname === '/variant') {
      res.writeHead(200, { 'content-type': 'text/html' });
      return res.end(fs.readFileSync(path.join(dir, 'index.html'), 'utf8').replace('Fixture Page', 'Fixture Page v2').replace('#2563eb', '#dc2626'));
    }
    res.writeHead(404, { 'content-type': 'text/plain' });
    res.end('not found');
  })
  .listen(port, '127.0.0.1', () => console.log(`fixture server on http://127.0.0.1:${port}`));
