const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../sig_warehouse/page/dispatch_queue/dispatch_queue.js'), 'utf8');
const end = source.indexOf('frappe.pages[');
assert.ok(end > 0, 'page entry point not found');
const context = {};
context.window = context;
vm.createContext(context);
vm.runInContext(source.slice(0, end), context);
const {sortRows, matches} = context.sig_dq_pure;

test('newest mode puts the latest MIR first and is the default', () => {
    const rows = [{name: 'MR-26-1208', created: '2026-11-05 09:00:00'}, {name: 'MR-26-1256', created: '2026-11-10 09:40:15'},
        {name: 'MR-26-1100', created: '2026-10-01 09:00:00'}];
    assert.equal(sortRows(rows, 'newest')[0].name, 'MR-26-1256');
    assert.equal(sortRows(rows, undefined)[0].name, 'MR-26-1256');
    assert.equal(sortRows(rows, 'nonsense')[0].name, 'MR-26-1256');
    assert.equal(rows[0].name, 'MR-26-1208', 'input must not be mutated');
});

test('waiting mode orders open requests by required date then age, closed after', () => {
    const rows = [{name: 'a', stage: 'PENDING', required_by: '2026-12-01', created: '2026-11-01'},
        {name: 'b', stage: 'PARTIAL', required_by: '2026-11-20', created: '2026-11-05'},
        {name: 'c', stage: 'DISPATCHED', created: '2026-11-09'}];
    assert.deepEqual(sortRows(rows, 'waiting').map((r) => r.name), ['b', 'a', 'c']);
});

test('attention mode lists short stock, then return waits, then oldest', () => {
    const rows = [{name: 'old', stage: 'PENDING', age_days: 30, flags: []},
        {name: 'ret', stage: 'DISPATCHED', age_days: 5, flags: ['return_blocks_close']},
        {name: 'red', stage: 'PENDING', age_days: 1, availability: 'red', flags: []}];
    assert.deepEqual(sortRows(rows, 'attention').map((r) => r.name), ['red', 'ret', 'old']);
});

test('search matches MIR number, MR id, site, project and PO, ignoring case', () => {
    const row = {name: 'MR-26-1256', mir: '1256', site: 'ZRI439', project: 'Capex', po: 'PO-9', work_type: ''};
    for (const q of ['1256', 'mr-26-1256', 'zri439', 'capex', 'po-9', '  1256  ', '']) assert.ok(matches(row, q), q);
    assert.ok(!matches(row, '9999'));
});

test('Warehouse Workbench opens the Dispatch Queue page by default and keeps the Kanban as a secondary tile', () => {
    const ws = fs.readFileSync(path.join(__dirname, '../sig_warehouse/page/warehouse_workspace/warehouse_workspace.js'), 'utf8');
    const card = (title) => {
        const i = ws.indexOf(`title: __('${title}')`);
        assert.ok(i > 0, title);
        return ws.slice(i, ws.indexOf('}', ws.indexOf('route:', i)));
    };
    const main = card('Dispatch materials');
    assert.match(main, /route: \['dispatch-queue'\]/);
    assert.match(main, /page_roles: \[[^\]]*'Stock User'[^\]]*\]/);
    assert.doesNotMatch(main, /Kanban/);
    const board = card('Dispatch Kanban board');
    assert.match(board, /route: \['List', 'Material Request', 'Kanban', 'SIG Dispatch Queue'\]/);
    assert.doesNotMatch(ws, /title: __\('Dispatch queue'\)/, 'no duplicate Dispatch queue tile');
});

test('custody button is hidden until the server says the user can dispatch', () => {
    assert.match(source, /sig-dq-custody" style="display:none"/);
    assert.match(source, /\.sig-dq-custody'\)\.toggle\(!!access\.can_dispatch\)/);
});
