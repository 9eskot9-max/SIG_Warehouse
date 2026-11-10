const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../sig_operations/page/field_planner/field_planner.js'), 'utf8');
const start = source.indexOf('        let mapBaseRequest = 0;');
const end = source.indexOf('        function chooseCycle(', start);
assert.ok(start >= 0 && end > start);

function setup(requireFn, leaflet = {}) {
    const calls = [];
    const context = {Promise, L: leaflet, BOX0: [0, 0, 100, 100],
        view: {base: 'drawing', box: [0, 0, 100, 100]},
        frappe: {require: requireFn, utils: {map_defaults: {tiles: {default_tile: {url: 'tiles'}}}}, msgprint: msg => calls.push(msg)},
        __: x => x, refreshMap: () => calls.push('render'), project: () => [0, 0], clampBox: x => x,
    };
    vm.createContext(context);
    vm.runInContext(source.slice(start, end) + '\nthis.setBase = setMapBase;', context);
    return {context, calls};
}

test('loads both Frappe bundles before switching to road map', async () => {
    const assets = [];
    const {context, calls} = setup(name => { assets.push(name); context.L.map = () => {}; return Promise.resolve(); });
    await context.setBase('street');
    assert.deepEqual(assets, ['leaflet.bundle.js', 'leaflet.bundle.css']);
    assert.equal(context.view.base, 'street');
    assert.deepEqual(calls, ['render']);
});

test('keeps drawing visible and reports a failed library load', async () => {
    const {context, calls} = setup(() => Promise.reject(new Error('offline')));
    await context.setBase('street');
    assert.equal(context.view.base, 'drawing');
    assert.match(calls[0], /could not be loaded/);
});

test('ignores a late load when the user selects drawing', async () => {
    let resolve;
    const pending = new Promise(r => { resolve = r; });
    const {context, calls} = setup(() => pending, {map() {}});
    const switching = context.setBase('street');
    await context.setBase('drawing');
    resolve();
    await switching;
    assert.equal(context.view.base, 'drawing');
    assert.deepEqual(calls, []);
});
