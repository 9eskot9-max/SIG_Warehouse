import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const script = path.join(here, 'alinma_router_push.mjs');

test('Alinma preview includes credits, salary candidates and unclassified debits', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'alinma-router-'));
  const file = path.join(dir, 'queue.json');
  const key = (n) => String(n).repeat(64);
  const queue = {
    schema_version: 1,
    bank: 'ALINMA',
    items: [
      { key: key(1), account: '1234567890', date: '09/11/2026 12.00 AM', reference: 'R1', signed_amount: '125.00', movement_type: 'RECEIVED_AMOUNT' },
      { key: key(2), account: '1234567890', date: '10/11/2026 12.00 AM', reference: 'R2', signed_amount: '-300.00', movement_type: 'SALARY_TRANSFER_CANDIDATE' },
      { key: key(3), account: '1234567890', date: '11/11/2026 12.00 AM', reference: 'R3', signed_amount: '-20.00', movement_type: 'OTHER_DEBIT' },
    ],
  };
  fs.writeFileSync(file, JSON.stringify(queue));
  try {
    const run = spawnSync(process.execPath, [script, file], { encoding: 'utf8' });
    assert.equal(run.status, 0, run.stderr);
    const summary = JSON.parse(run.stdout);
    assert.deepEqual(summary, {
      mode: 'preview', bank: 'ALINMA', rows_to_route: 3,
      received_amounts: 1, salary_candidates: 1, other_debits: 1,
    });
    assert.doesNotMatch(run.stdout, /1234567890/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('Alinma preview refuses an unsupported date without sending rows', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'alinma-router-date-'));
  const file = path.join(dir, 'queue.json');
  fs.writeFileSync(file, JSON.stringify({
    schema_version: 1,
    bank: 'ALINMA',
    items: [{ key: 'a'.repeat(64), account: '1234567890', date: 'not-a-date', reference: 'R1', signed_amount: '1.00', movement_type: 'RECEIVED_AMOUNT' }],
  }));
  try {
    const run = spawnSync(process.execPath, [script, file], { encoding: 'utf8' });
    assert.notEqual(run.status, 0);
    assert.match(run.stderr, /Unsupported Alinma date format/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('Alinma preview rejects impossible ISO dates', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'alinma-router-iso-date-'));
  const file = path.join(dir, 'queue.json');
  fs.writeFileSync(file, JSON.stringify({
    schema_version: 1,
    bank: 'ALINMA',
    items: [{ key: 'b'.repeat(64), account: '1234567890', date: '2026-02-30', reference: 'R1', signed_amount: '1.00', movement_type: 'RECEIVED_AMOUNT' }],
  }));
  try {
    const run = spawnSync(process.execPath, [script, file], { encoding: 'utf8' });
    assert.notEqual(run.status, 0);
    assert.match(run.stderr, /Invalid Alinma statement date/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
