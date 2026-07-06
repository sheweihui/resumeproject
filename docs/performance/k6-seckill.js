import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    seckill_smoke: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '20s', target: 50 },
        { duration: '40s', target: 200 },
        { duration: '30s', target: 500 },
        { duration: '20s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.20'],
    http_req_duration: ['p(95)<3000'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const ACTIVITY_ID = __ENV.ACTIVITY_ID || '1';
const TOKEN = __ENV.TOKEN || '';

export default function () {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (TOKEN) {
    headers.Authorization = `Bearer ${TOKEN}`;
  }

  const response = http.post(
    `${BASE_URL}/api/store/flash-sale/purchase/${ACTIVITY_ID}`,
    JSON.stringify({}),
    { headers }
  );

  check(response, {
    'status is not 5xx': (r) => r.status < 500,
    'response returned': (r) => r.body && r.body.length > 0,
  });

  sleep(0.2);
}

// Usage:
// k6 run docs/performance/k6-seckill.js
// BASE_URL=http://localhost:8080 ACTIVITY_ID=1 TOKEN=xxx k6 run docs/performance/k6-seckill.js
