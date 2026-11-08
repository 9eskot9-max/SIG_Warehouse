frappe.pages['snb-movement-router'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Bank Movement Router'), single_column: true});
    const root = $('<main class="snb-router"></main>').appendTo(page.main), el = root[0];
    const esc = value => frappe.utils.escape_html(String(value == null ? '' : value));
    const method = 'sig_warehouse.sig_accounting.snb_movement_router.';
    const lanes = {RECEIPTS: 'Receipts', PAYMENTS: 'Payments', OWN_ACCOUNTS: 'Own accounts', OTHER: 'Other', DEFERRED: 'Deferred'};
    const routes = ['CUSTOMER_RECEIPT','OWN_ACCOUNT_TRANSFER','PETTY_CASH_FUNDING','SUPPLIER_PAYMENT','MATERIAL_SUPPLIER_PAYMENT','SUBCONTRACTOR_PAYMENT','MAINTENANCE_PAYMENT','LOGISTICS_PAYMENT','HR_EMPLOYEE_PAYMENT','SALARY_PAYMENT','SADAD_PAYMENT','EMPLOYEE_PAYMENT','OTHER','DEFERRED_TAWAL','DEFERRED_XXCL'];
    const state = {rows: [], lane: 'RECEIPTS', bank: 'ALL', selected: '', search: '', referenceQueryKey: ''};
    root.html(`<header><h2>${__('Review bank movements')}</h2><p>${__('Review bank evidence from connected sources and save an accountant decision. ERP draft creation is not yet enabled.')}</p><button class="btn btn-default" data-refresh>${__('Refresh')}</button></header><label class="snb-bank-filter">${__('Bank')} <select data-bank><option value="ALL">${__('All banks')}</option><option value="SNB">SNB</option><option value="ALINMA">Alinma</option></select></label><nav data-lanes></nav><input class="form-control" data-search placeholder="${__('Search party, account ending, reference…')}"><section class="snb-grid"><aside><h4 data-title></h4><div data-queue></div></aside><article data-evidence></article><article data-review></article></section>`);
    const q = s => el.querySelector(s);
    const bankOf = x => String(x.source.bank || 'SNB').toUpperCase() === 'ALINMA' ? 'ALINMA' : 'SNB';
    const bankRows = () => state.rows.filter(x => state.bank === 'ALL' || bankOf(x) === state.bank);
    const opt = (items, value, labels={}) => '<option value="">' + __('Choose…') + '</option>' + items.map(x => `<option value="${esc(x)}" ${x===value?'selected':''}>${esc(labels[x] || x.replaceAll('_',' '))}</option>`).join('');
    const selected = () => state.rows.find(x => x.name === state.selected);
    const referenceKey = (doctype,name) => doctype && name ? `${doctype}::${name}` : '';
    const requestReference = x => {
        const raw=x?.source?.transfer_request?.allocation_json;
        try { const rows=Array.isArray(raw)?raw:JSON.parse(String(raw||'[]')); return Array.isArray(rows)?rows[0]||null:null; } catch(e) { return null; }
    };
    const formatCurrency=(amount,currency)=>`${Number(amount||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})} ${currency||''}`;
    function loadPaymentReferences(x) {
        if(x?.source?.direction!=='DEBIT') return;
        const supplier=q('[data-field="party"]')?.value.trim()||'';
        const partyType=q('[data-field="party_type"]')?.value||'';
        const company=q('[data-field="company"]')?.value.trim()||'';
        const select=q('[data-reference-choice]');
        if(!select || partyType!=='Supplier' || !supplier || !company) return;
        const key=`${x.name}|${supplier}|${company}|${x.source.currency||''}`;
        if(state.referenceQueryKey===key && select.dataset.loaded==='1') return;
        state.referenceQueryKey=key;
        frappe.call({method:method+'get_supplier_payment_references',args:{name:x.name,supplier,company}}).then(response=>{
            if(state.referenceQueryKey!==key || selected()?.name!==x.name) return;
            const data=response.message||{}, review=x.review||{}, req=requestReference(x);
            const current=referenceKey(review.payment_reference_doctype,review.payment_reference) || referenceKey(req?.reference_doctype,req?.reference_name);
            select.innerHTML=`<option value="">${__('No document · leave unallocated')}</option>`;
            const addGroup=(label,rows,kind)=>{
                if(!rows?.length) return;
                const group=document.createElement('optgroup'); group.label=label;
                for(const row of rows){
                    const option=document.createElement('option'); option.value=referenceKey(kind,row.name);
                    option.textContent=kind==='Purchase Order'
                        ? `${__('Advance · Purchase Order')} ${row.name} · ${row.transaction_date||''} · ${formatCurrency(row.grand_total,row.currency)}`
                        : `Purchase Invoice ${row.name} · ${__('Outstanding')} ${formatCurrency(row.outstanding_amount,row.currency)}`;
                    group.append(option);
                }
                select.append(group);
            };
            addGroup(__('Purchase Orders · advances'),data.purchase_orders||[],'Purchase Order');
            addGroup(__('Purchase Invoices · allocations'),data.purchase_invoices||[],'Purchase Invoice');
            if(current && ![...select.options].some(option=>option.value===current)) select.append(new Option(`${__('Saved or TX Manager reference')} · ${current.replace('::',' · ')}`,current));
            if(current) select.value=current;
            select.dataset.loaded='1';
            const amount=q('[data-reference-amount]');
            if(amount && !review.payment_reference_amount && current===referenceKey(req?.reference_doctype,req?.reference_name)) amount.value=req?.allocated_amount||'';
        }).catch(()=>{
            if(state.referenceQueryKey===key){ const status=q('[data-reference-status]'); if(status) status.textContent=__('ERP document list unavailable; leaving the payment unallocated is still available.'); }
        });
    }
    function render() {
        const sourceRows = bankRows();
        q('[data-lanes]').innerHTML = Object.entries(lanes).map(([key, label]) => `<button class="btn ${state.lane===key?'btn-primary':'btn-default'}" data-lane="${key}">${__(label)} · ${sourceRows.filter(x => (x.review.lane || x.recognition.lane) === key).length}</button>`).join('');
        q('[data-title]').textContent = __(lanes[state.lane]);
        const list = sourceRows.filter(x => (x.review.lane || x.recognition.lane) === state.lane && JSON.stringify([x.source,x.recognition,x.review.party]).toLowerCase().includes(state.search));
        if (!list.some(x => x.name === state.selected)) state.selected = list[0]?.name || '';
        q('[data-queue]').innerHTML = list.map(x => `<button class="snb-row ${state.selected===x.name?'selected':''}" data-row="${esc(x.name)}"><strong>${Number(x.source.signed_amount || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})} ${esc(x.source.currency)}</strong><span>${esc(bankOf(x))} · ${esc(x.source.event_date)} · ••${esc(x.source.account_tail)}</span><span>${esc(x.review.party || x.erp.proposed_party || x.source.extracted_name || x.source.detail_description || 'Unidentified')}</span><small>${esc(x.review.review_status || x.recognition.status || 'PENDING')}</small></button>`).join('') || `<p>${__('No movements in this view.')}</p>`;
        const x = selected();
        if (!x) { q('[data-evidence]').innerHTML = `<p>${__('Select a movement.')}</p>`; q('[data-review]').innerHTML = ''; return; }
        const s=x.source,r=x.recognition,d=x.review,m=s.beneficiary_mapping || {};
        const text=[s.transaction_description,s.detail_description,s.extra_description,s.remarks].filter(Boolean).join('\n');
        const requestRef=requestReference(x), savedRef=referenceKey(d.payment_reference_doctype,d.payment_reference);
        const effectiveRef=savedRef||referenceKey(requestRef?.reference_doctype,requestRef?.reference_name);
        const supplierHint=String(m.erp_party||x.erp.proposed_party||'').match(/^Supplier:\s*(.+)$/i)?.[1]?.trim()||'';
        const partyValue=d.party||supplierHint||x.erp.proposed_party||'';
        const partyTypeValue=d.party_type||(supplierHint?'Supplier':'');
        const managerHint=requestRef?`<h5>${__('TX Manager reference · pending accountant confirmation')}</h5><p>${requestRef.reference_doctype==='Purchase Order'?__('Advance reference'):__('Invoice allocation')} · ${esc(requestRef.reference_doctype)} ${esc(requestRef.reference_name)} · ${formatCurrency(requestRef.allocated_amount,s.currency)}</p>`:'';
        q('[data-evidence]').innerHTML = `<h3>${esc(bankOf(x))} · ${__('Bank evidence')}</h3><div class="snb-amount">${Number(s.signed_amount || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})} ${esc(s.currency)}</div><p>${esc(s.event_date)} · ••${esc(s.account_tail)} · ${__('Reference')} ${esc(s.reference || '—')}</p><h5>${__('Statement narrative')}</h5><pre>${esc(text || '—')}</pre><h5>${__('Recognition evidence')}</h5><p>${esc(r.reason || 'No route suggestion')}</p><p>${(r.evidence || []).map(esc).join(' · ')}</p>${bankOf(x)==='SNB'?`<h5>${__('AM beneficiary mapping')}</h5><p>${esc(m.beneficiary_name || m.nickname || 'Not matched')} · ${esc(m.status || '—')} · ${esc(m.erp_party || 'No ERP party')}</p>`:''}${managerHint}<h5>${__('ERP link hint')}</h5><p>${esc(x.erp.linked_doc || 'None')} ${x.erp.linked_doc ? '· ' + __('Read-back required') : ''}</p><small>${__('Source evidence is immutable.')} ${esc(x.id)}</small>`;
        q('[data-review]').innerHTML = `<h3>${__('Accountant decision')}</h3><p>${__('Suggestions require review. Select exact ERP names for linked records.')}</p><label>${__('Lane')}<select data-field="lane">${opt(Object.keys(lanes),d.lane || r.lane,lanes)}</select></label><label>${__('Route')}<select data-field="route">${opt(routes,d.route || r.route)}</select></label><label>${__('Category')}<select data-field="category">${opt(['XXPC','XXSL','XXCL','XXMT','XXMR','XXOM','XXSC','XXLG','XXHR','ALINMA_SALARY_CANDIDATE'],d.category || r.category)}</select></label><label>${__('Party type')}<select data-field="party_type">${opt(['Customer','Supplier','Employee','Other'],partyTypeValue)}</select></label><label>${__('ERP party')}<input data-field="party" value="${esc(partyValue)}"></label><label>${__('Company')}<input data-field="company" value="${esc(d.company || '')}"></label><label>${__('Bank GL account')}<input data-field="bank_account" value="${esc(d.bank_account || '')}"></label><label>${__('Counter GL account')}<input data-field="counter_account" value="${esc(d.counter_account || '')}"></label><label>${__('Material treatment')}<select data-field="material_treatment">${opt(['STOCK','OPERATIONAL_NON_STOCK'],d.material_treatment)}</select></label>${s.direction==='DEBIT'?`<section class="snb-payment-reference"><h4>${__('Supplier payment reference · optional')}</h4><p>${__('Purchase Orders are advance references. Purchase Invoices allocate against outstanding. No selection leaves the payment unallocated. Purchase Receipts are not payment references.')}</p><label>${__('Document')}<select data-reference-choice><option value="" ${effectiveRef?'':'selected'}>${__('No document · leave unallocated')}</option>${effectiveRef?`<option value="${esc(effectiveRef)}" selected>${esc(effectiveRef.replace('::',' · '))}</option>`:''}</select></label><label>${__('Allocated amount')}<input data-reference-amount type="number" min="0" max="${Math.abs(Number(s.signed_amount||0))}" step="0.01" value="${esc(d.payment_reference_amount || requestRef?.allocated_amount || '')}"></label><small data-reference-status>${__('Choose Supplier and Company to load submitted documents. The list respects your ERP permissions.')}</small></section>`:''}<label>${__('Review state')}<select data-field="review_status">${opt(['PENDING','REVIEWED','NEEDS_CLARIFICATION','DEFERRED'],d.review_status || 'PENDING')}</select></label><label>${__('Note')}<textarea data-field="notes">${esc(d.notes || '')}</textarea></label><button class="btn btn-primary" data-save>${__('Save decision')}</button><div data-message></div>`;
        loadPaymentReferences(x);
    }
    async function load() {
        try { let rows=[],start=0,part; do { part=(await frappe.call({method:method+'list_movements',args:{start,limit:200}})).message || []; rows=rows.concat(part); start+=part.length; } while(part.length===200 && start<10000); state.rows=rows; render(); }
        catch(e) { frappe.msgprint(__('Could not load bank movements. Check your access.')); }
    }
    root.on('click','[data-lane]',function(){state.lane=this.dataset.lane;state.selected='';render();});
    root.on('change','[data-bank]',function(){state.bank=this.value;state.selected='';render();});
    root.on('click','[data-row]',function(){state.selected=this.dataset.row;render();});
    root.on('input','[data-search]',function(){state.search=this.value.toLowerCase();render();});
    root.on('click','[data-refresh]',load);
    root.on('change','[data-field="party_type"], [data-field="party"], [data-field="company"]',function(){state.referenceQueryKey='';const x=selected();if(x)loadPaymentReferences(x);});
    root.on('change','[data-reference-choice]',function(){const amount=q('[data-reference-amount]');if(this.value&&amount&&!amount.value)amount.value=Math.abs(Number(selected()?.source?.signed_amount||0)).toFixed(2);if(!this.value&&amount)amount.value='';});
    root.on('click','[data-save]',async function(){const x=selected();if(!x)return;const decision={};el.querySelectorAll('[data-field]').forEach(n=>decision[n.dataset.field]=n.value);const choice=q('[data-reference-choice]')?.value||'';const sep=choice.indexOf('::');decision.payment_reference_doctype=sep>0?choice.slice(0,sep):'';decision.payment_reference=sep>0?choice.slice(sep+2):'';decision.payment_reference_amount=decision.payment_reference?Number(q('[data-reference-amount]')?.value||0):0;this.disabled=true;try{const result=await frappe.call({method:method+'save_review',type:'POST',args:{name:x.name,modified:x.modified,decision}});const index=state.rows.findIndex(z=>z.name===x.name);state.rows[index]=result.message;state.referenceQueryKey='';render();frappe.show_alert({message:__('Decision saved'),indicator:'green'});}catch(e){q('[data-message]').textContent=__('Could not save. Check the error and refresh if the row changed.');}finally{this.disabled=false;}});
    load();
};
