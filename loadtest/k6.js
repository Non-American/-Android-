// docker compose run --rm -v "$PWD/loadtest:/app/loadtest" api python -m scripts.seed loadtest --n 100000
// docker compose --profile loadtest run --rm k6
// docker compose run --rm api python -m scripts.seed cleanup-loadtest
import http from 'k6/http';
import ws from 'k6/ws';
import { check } from 'k6';
import { SharedArray } from 'k6/data';
import { Counter } from 'k6/metrics';

const tokens = new SharedArray('tokens', () => JSON.parse(open('./tokens.json')));
const BASE = __ENV.BASE_URL || 'http://localhost:8000';
const WS_BASE = BASE.replace(/^http/, 'ws');
const PEAK = +(__ENV.PEAK || 600);
const HOLD = __ENV.HOLD || '2m';
const SOCKETS = +(__ENV.SOCKETS || 1000);
const SESSION = 20;
const wsEvents = new Counter('ws_events');

export const options = {
  scenarios: {
    swipes: {
      executor: 'ramping-arrival-rate',
      exec: 'swipes',
      startRate: 20, timeUnit: '1s', preAllocatedVUs: 300, maxVUs: 1500,
      stages: [
        { target: Math.round(PEAK / 3), duration: '30s' },
        { target: PEAK, duration: '30s' },
        { target: PEAK, duration: HOLD },
        { target: 0, duration: '10s' },
      ],
    },
    sockets: {
      executor: 'constant-vus',
      exec: 'sockets',
      vus: SOCKETS,
      duration: '3m',
    },
  },
  thresholds: {
    'http_req_failed{scenario:swipes}': ['rate<0.01'],
    'http_req_duration{ep:swipe}': ['p(95)<150'],
    'http_req_duration{ep:feed}': ['p(95)<500'],
    'http_req_duration{ep:matches}': ['p(95)<300'],
    'checks{scenario:sockets}': ['rate>0.99'],
    dropped_iterations: ['count<500'],
  },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
};

// per-VU session: a random user swipes through ~SESSION cards, then the VU switches to another user
let token = null;
let left = 0;
let queue = [];

function auth(ep) {
  return { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, tags: { ep } };
}

export function swipes() {
  if (left <= 0 || !token) {
    token = tokens[Math.floor(Math.random() * tokens.length)];
    left = SESSION;
    queue = [];
  }
  if (queue.length < 5) {
    const r = http.get(`${BASE}/api/feed?limit=20`, auth('feed'));
    check(r, { 'feed 200': (x) => x.status === 200 });
    if (r.status === 200) {
      const have = new Set(queue);
      queue.push(...r.json().map((c) => c.id).filter((id) => !have.has(id)));
    }
  }
  const target = queue.shift();
  left--;
  if (target) {
    const r = http.post(`${BASE}/api/swipe`, JSON.stringify({ target, liked: Math.random() < 0.3 }), auth('swipe'));
    check(r, { 'swipe 200': (x) => x.status === 200 });
  } else {
    left = 0;
  }
  if (Math.random() < 0.05) {
    check(http.get(`${BASE}/api/matches`, auth('matches')), { 'matches 200': (x) => x.status === 200 });
  }
}

export function sockets() {
  const t = tokens[(__VU * 7919) % tokens.length];
  let ready = false;
  const res = ws.connect(`${WS_BASE}/api/ws`, { tags: { ep: 'ws' } }, (socket) => {
    socket.on('open', () => socket.send(t));
    socket.on('message', (m) => {
      if (JSON.parse(m).type === 'ready') ready = true;
      wsEvents.add(1);
    });
    socket.setInterval(() => socket.send('ping'), 25000);
    socket.setTimeout(() => socket.close(), 60000 + Math.random() * 30000);
  });
  check(res, { 'ws 101': (r) => r && r.status === 101 });
  check(ready, { 'ws ready': (x) => x });
}
