import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const script = path.join(path.dirname(fileURLToPath(import.meta.url)), 'snb_router_push.mjs');
test('preview is read-only and push refuses a queue without AM evidence', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'snb-router-'));
  try {
    const file = path.join(dir, 'queue.json');
    writeFileSync(file, JSON.stringify({ schema_version: 1, items: [{ id: 'movement' }], source: { am_snapshot_loaded: false }, summary: {} }));
    const preview = spawnSync(process.execPath, [script, file], { encoding: 'utf8' });
    assert.equal(preview.status, 0);
    assert.equal(JSON.parse(preview.stdout).mode, 'preview');
    const push = spawnSync(process.execPath, [script, file, '--push'], { encoding: 'utf8' });
    assert.notEqual(push.status, 0);
    assert.match(push.stderr, /Sheet Am evidence is not loaded/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
