import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = { vus: Number(__ENV.K6_VUS || 8), duration: __ENV.K6_DURATION || '60s', tags: { testid: __ENV.K6_TEST_ID || 'checkout-load' }, thresholds: { http_req_duration: ['p(95)<10000'] } };
const baseUrl = __ENV.BASE_URL || 'http://localhost:5055';
export function setup() {
  if (__ENV.K6_INCIDENT !== 'true') return;
  const response = http.post(`${baseUrl}/demo/state`, JSON.stringify({ mode: 'incident' }), { headers: { 'Content-Type': 'application/json' } });
  if (response.status >= 300) throw new Error(`could not activate incident: HTTP ${response.status}`);
}
export default function () {
  const res = http.get(`${baseUrl}/checkout`);
  check(res, { 'checkout succeeded': r => r.status === 200 });
  sleep(0.2);
}
