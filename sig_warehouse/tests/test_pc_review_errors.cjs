// Reproduce v15's 403 error callback with no argument, followed by jqXHR.fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../sig_accounting/page/pc_invoice_review/pc_invoice_review.js'), 'utf8');
const helpers = source.slice(source.indexOf('    function serverMessages('), source.indexOf('    // ---- data'));
const message = 'Only Finance can designate a Journal Entry as petty-cash funding.';
const xhr = {status: 403, responseText: JSON.stringify({
    _server_messages: JSON.stringify([JSON.stringify({message})]),
})};
const context = {plainText: String, __: String, frappe: {call(options) {
    options.error();
    return {fail(callback) { queueMicrotask(() => callback(xhr)); }};
}}};
vm.createContext(context);
vm.runInContext(helpers, context);
assert.equal(context.readError(xhr), message);
assert.equal(context.readError({responseJSON: {exception: 'frappe.exceptions.PermissionError: denied'}}), 'denied');
context.call('confirm', {}).then(
    () => { throw new Error('Expected confirmation rejection'); },
    error => { assert.equal(error.message, message); console.log('PC Review v15 error callback regression PASS'); },
).catch(error => { console.error(error); process.exitCode = 1; });
