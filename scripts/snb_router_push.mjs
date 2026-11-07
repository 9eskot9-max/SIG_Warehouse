// Push an already-built recognition queue to the ERP router after it is deployed.
// Preview is the default; --push is required for ERP writes.
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const file = args.find((arg) => !arg.startsWith('--'));
if (!file) throw new Error('Usage: node scripts/snb_router_push.mjs <queue.json> [--push]');
const queue = JSON.parse(fs.readFileSync(path.resolve(file), 'utf8'));
if (queue.schema_version !== 1 || !Array.isArray(queue.items)) throw new Error('Invalid recognition queue.');
if (!args.includes('--push')) {
  console.log(JSON.stringify({ mode: 'preview', rows: queue.items.length, source: queue.source, summary: queue.summary }, null, 2));
  process.exit(0);
}
if (!queue.source?.am_snapshot_loaded) throw new Error('Sheet Am evidence is not loaded. Build the queue with a reviewed AM snapshot before pushing.');
if (!queue.source?.employee_account_count || !queue.source?.beneficiary_registry_count || !queue.source?.transfer_request_count) throw new Error('The AM snapshot is incomplete: beneficiary, employee-account, and transfer-request data are required before pushing.');
const site = String(process.env.SIG_ERPNEXT_SITE || '').replace(/\/+$/, '');
const key = process.env.SIG_ERPNEXT_API_KEY, secret = process.env.SIG_ERPNEXT_API_SECRET;
if (site !== 'https://neosys.frappe.cloud' || !key || !secret) throw new Error('Configure the exact production ERP URL and API credentials in the process environment.');
const auth = `token ${key}:${secret}`;
const who = await fetch(`${site}/api/method/frappe.auth.get_logged_user`, { headers: { Authorization: auth }, signal: AbortSignal.timeout(15000) });
const identity = await who.json();
if (!who.ok || identity.message !== '9eskot9@gmail.com') throw new Error('ERP integration identity did not match the configured SNB owner.');
const counts = { CREATED: 0, EXISTS: 0, SOURCE_CONFLICT: 0 };
for (let i = 0; i < queue.items.length; i += 50) {
  const response = await fetch(`${site}/api/method/sig_warehouse.sig_accounting.snb_movement_router.ingest`, {
    method: 'POST', headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: queue.items.slice(i, i + 50) }), signal: AbortSignal.timeout(75000),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !Array.isArray(data.message)) throw new Error(`ERP intake failed at batch ${Math.floor(i / 50) + 1}; HTTP ${response.status}. Reconcile before retrying.`);
  for (const item of data.message) counts[item.status] = (counts[item.status] || 0) + 1;
  if (data.message.some((item) => item.status === 'SOURCE_CONFLICT')) {
    console.error(JSON.stringify({ counts, conflicts: data.message.filter((item) => item.status === 'SOURCE_CONFLICT').map((item) => item.name) }));
    process.exitCode = 2;
    break;
  }
}
console.log(JSON.stringify({ mode: 'push', counts }));
