import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = (__ENV.BASE_URL || 'http://localhost:5055').replace(/\/+$/, '');
const startVus = Number(__ENV.GRADUAL_START_VUS || 4);
const maxVus = Number(__ENV.GRADUAL_MAX_VUS || 22);
const startDuration = __ENV.GRADUAL_START_DURATION || '2m';
const stepDuration = __ENV.GRADUAL_STEP_DURATION || '1m';
const cleanup = __ENV.K6_CLEANUP === 'true';

if (startVus < 1 || maxVus < startVus) {
  throw new Error('GRADUAL_MAX_VUS must be greater than or equal to GRADUAL_START_VUS');
}

const stages = [{ duration: startDuration, target: startVus }];
for (let vus = startVus + 1; vus <= maxVus; vus += 1) {
  stages.push({ duration: stepDuration, target: vus });
}

export const options = {
  stages,
  tags: { testid: __ENV.K6_TEST_ID || 'gradual-checkout' },
  thresholds: {
    checks: ['rate>0.95'],
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<10000'],
  },
};

export function setup() {
  const response = http.post(
    `${baseUrl}/demo/state`,
    JSON.stringify({ mode: 'degraded' }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  const state = response.status < 300 ? response.json() : {};
  if (response.status >= 300 || state.mode !== 'degraded' || state.health?.mode !== 'degraded') {
    throw new Error(`could not activate degraded mode: HTTP ${response.status}`);
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
    'checkout is still up': (res) => res.status === 200 && payload && payload.status === 'confirmed',
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
