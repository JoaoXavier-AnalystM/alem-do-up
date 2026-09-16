import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = { vus: 8, duration: '60s', thresholds: { http_req_duration: ['p(95)<10000'] } };
export default function () {
  const res = http.get('http://localhost:8080/checkout');
  check(res, { 'checkout responded': r => [200, 503].includes(r.status) });
  sleep(0.2);
}
