import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = (__ENV.BASE_URL || 'http://localhost:5055').replace(/\/+$/, '');
const incidentMode = __ENV.K6_INCIDENT === 'true';
const cleanup = __ENV.K6_CLEANUP === 'true';

export const options = {
  vus: Number(__ENV.K6_VUS || 8),
  duration: __ENV.K6_DURATION || '60s',
  tags: { testid: __ENV.K6_TEST_ID || 'checkout-load' },
  thresholds: {
    checks: ['rate>0.95'],
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<10000'],
  },
};

export function setup() {
  if (!incidentMode) return;

  const response = http.post(
    `${baseUrl}/demo/state`,
    JSON.stringify({ mode: 'incident' }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  const state = response.status < 300 ? response.json() : {};
  if (response.status >= 300 || state.mode !== 'incident' || state.health?.mode !== 'incident') {
    throw new Error(`could not activate incident: HTTP ${response.status}`);
  }
}

export default function () {
  const response = http.get(`${baseUrl}/checkout`);
  let payload = null;
  if (response.status === 200) {
    try {
      payload = response.json();
    } catch (_) {
      payload = null;
    }
  }
  check(response, {
    'checkout succeeded': (res) => res.status === 200 && payload && payload.status === 'confirmed',
  });
  sleep(Number(__ENV.K6_SLEEP_SECONDS || 0.2));
}

export function teardown() {
  if (!cleanup) return;

  const response = http.post(
    `${baseUrl}/demo/state`,
    JSON.stringify({ mode: 'normal' }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  if (response.status >= 300) throw new Error(`could not clean up demo state: HTTP ${response.status}`);
}
