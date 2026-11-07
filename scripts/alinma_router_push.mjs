// Adapt the local Alinma review queue to the shared Bank Movement Router.
// Preview is read-only; --push is required for ERP intake.
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const files = args.filter((arg) => !arg.startsWith('--'));
const file = files[0];
if (files.length !== 1 || !file || args.some((arg) => arg.startsWith('--') && arg !== '--push')) {
  throw new Error('Usage: node scripts/alinma_router_push.mjs <alinma-review-queue.json> [--push]');
}
const queue = JSON.parse(fs.readFileSync(path.resolve(file), 'utf8'));
if (queue.schema_version !== 1 || queue.bank !== 'ALINMA' || !Array.isArray(queue.items)) {
  throw new Error('Expected an Alinma review queue (schema v1).');
}

function dateIso(value) {
  const text = String(value || '').trim();
  let match = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+12\.00\s+AM)?$/i);
  if (match) {
    const day = Number(match[1]), month = Number(match[2]), year = Number(match[3]);
    const date = new Date(Date.UTC(year, month - 1, day));
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) throw new Error('Invalid Alinma statement date.');
    return date.toISOString().slice(0, 10);
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    const [year, month, day] = text.split('-').map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) throw new Error('Invalid Alinma statement date.');
    return text;
  }
  throw new Error('Unsupported Alinma date format; no rows sent.');
}

const items = [];
const skipped = { other_debits: 0 };
for (const row of queue.items) {
  if (row.movement_type === 'OTHER_DEBIT') { skipped.other_debits += 1; continue; }
  if (!['RECEIVED_AMOUNT', 'SALARY_TRANSFER_CANDIDATE'].includes(row.movement_type)) throw new Error('Unknown Alinma movement type; no rows sent.');
  if (!/^[a-f0-9]{64}$/.test(String(row.key || '')) || !/^\d{8,34}$/.test(String(row.account || '')) || !row.reference) throw new Error('Alinma source identity is incomplete; no rows sent.');
  const amount = Number(row.signed_amount);
  const direction = row.movement_type === 'RECEIVED_AMOUNT' ? 'CREDIT' : 'DEBIT';
  if (!Number.isFinite(amount) || (direction === 'CREDIT' && amount <= 0) || (direction === 'DEBIT' && amount >= 0)) throw new Error('Alinma amount and direction disagree; no rows sent.');
  const salary = direction === 'DEBIT';
  const source = {
    bank: 'ALINMA',
    event_date: dateIso(row.date),
    account_tail: String(row.account).slice(-4),
    reference: String(row.reference),
    signed_amount: amount,
    currency: 'SAR',
    direction,
    transaction_description: 'Alinma account statement',
    detail_description: String(row.description || ''),
    balance: String(row.balance || ''),
  };
  const recognition = {
    lane: salary ? 'PAYMENTS' : 'RECEIPTS',
    route: salary ? 'SALARY_PAYMENT' : 'CUSTOMER_RECEIPT',
    category: salary ? 'ALINMA_SALARY_CANDIDATE' : '',
    status: salary ? 'SALARY_CANDIDATE_REVIEW' : 'UNMATCHED_RECEIVED_CREDIT',
    confidence: salary ? 'NARRATIVE_CANDIDATE' : 'NONE',
    reason: salary
      ? 'Outbound statement narrative matches a salary/payroll marker; accountant confirms that this is payroll.'
      : 'Bank credit captured for receivables review; no customer, invoice, or accounting account was inferred.',
    evidence: salary ? ['ALINMA source', 'Outbound salary/payroll narrative candidate'] : ['ALINMA source', 'Bank statement credit'],
    party_candidates: [],
    invoice_candidates: [],
  };
  items.push({
    id: `ALINMA-${row.key}`,
    schema_version: 1,
    source,
    recognition,
    erp: { linked_doc: '', readback_status: 'NOT_LINKED', proposed_doctype: 'Review', proposed_party: '' },
    review: { status: 'PENDING', decision: null },
  });
}

if (!args.includes('--push')) {
  const summary = {
    mode: 'preview',
    bank: 'ALINMA',
    rows_to_route: items.length,
    received_amounts: items.filter((row) => row.source.direction === 'CREDIT').length,
    salary_candidates: items.filter((row) => row.recognition.category === 'ALINMA_SALARY_CANDIDATE').length,
    ...skipped,
  };
  console.log(JSON.stringify(summary, null, 2));
  process.exit(0);
}

const site = String(process.env.SIG_ERPNEXT_SITE || '').replace(/\/+$/, '');
const key = process.env.SIG_ERPNEXT_API_KEY, secret = process.env.SIG_ERPNEXT_API_SECRET;
if (site !== 'https://neosys.frappe.cloud' || !key || !secret) throw new Error('Configure the exact production ERP URL and approved integration credentials in the process environment.');
const auth = `token ${key}:${secret}`;
const who = await fetch(`${site}/api/method/frappe.auth.get_logged_user`, { headers: { Authorization: auth }, signal: AbortSignal.timeout(15000) });
const identity = await who.json();
if (!who.ok || identity.message !== '9eskot9@gmail.com') throw new Error('ERP integration identity did not match the configured movement integration owner.');
const counts = { CREATED: 0, EXISTS: 0, SOURCE_CONFLICT: 0 };
for (let i = 0; i < items.length; i += 50) {
  const response = await fetch(`${site}/api/method/sig_warehouse.sig_accounting.snb_movement_router.ingest`, {
    method: 'POST',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: items.slice(i, i + 50) }),
    signal: AbortSignal.timeout(75000),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !Array.isArray(data.message)) throw new Error(`ERP intake failed at batch ${Math.floor(i / 50) + 1}; HTTP ${response.status}. Reconcile before retrying.`);
  for (const item of data.message) counts[item.status] = (counts[item.status] || 0) + 1;
  if (data.message.some((item) => item.status === 'SOURCE_CONFLICT')) throw new Error('ERP reported a source conflict. Stop and reconcile before retrying.');
}
console.log(JSON.stringify({ mode: 'push', bank: 'ALINMA', counts, ...skipped }, null, 2));
