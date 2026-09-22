import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = __ENV.BASE_URL || 'http://localhost:5055';
const startVus = Number(__ENV.GRADUAL_START_VUS || 4);
const maxVus = Number(__ENV.GRADUAL_MAX_VUS || 22);
const startDuration = __ENV.GRADUAL_START_DURATION || '2m';
const stepDuration = __ENV.GRADUAL_STEP_DURATION || '1m';

const stages = [{ duration: startDuration, target: startVus }];
for (let vus = startVus + 1; vus <= maxVus; vus += 1) {
  stages.push({ duration: stepDuration, target: vus });
}

export const options = {
  stages,
  tags: { testid: __ENV.K6_TEST_ID || 'gradual-checkout' },
  thresholds: { http_req_duration: ['p(95)<10000'] },
};

export function setup() {
  const response = http.post(
    `${baseUrl}/demo/state`,
    JSON.stringify({ mode: 'degraded' }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  if (response.status >= 300) throw new Error(`could not activate degraded mode: HTTP ${response.status}`);
}

export default function () {
  const response = http.get(`${baseUrl}/checkout`);
  check(response, { 'checkout is still up': (res) => res.status === 200 });
  sleep(0.2);
}
