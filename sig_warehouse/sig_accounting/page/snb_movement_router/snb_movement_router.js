frappe.pages['snb-movement-router'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Bank Movement Router'), single_column: true});
    const root = $('<main class="snb-router"></main>').appendTo(page.main), el = root[0];
    const esc = value => frappe.utils.escape_html(String(value == null ? '' : value));
    const method = 'sig_warehouse.sig_accounting.snb_movement_router.';
    const lanes = {RECEIPTS: 'Receipts', PAYMENTS: 'Payments', OWN_ACCOUNTS: 'Own accounts', OTHER: 'Other', DEFERRED: 'Deferred'};
    const routes = ['CUSTOMER_RECEIPT','OWN_ACCOUNT_TRANSFER','PETTY_CASH_FUNDING','SUPPLIER_PAYMENT','MATERIAL_SUPPLIER_PAYMENT','SUBCONTRACTOR_PAYMENT','MAINTENANCE_PAYMENT','LOGISTICS_PAYMENT','HR_EMPLOYEE_PAYMENT','SALARY_PAYMENT','SADAD_PAYMENT','EMPLOYEE_PAYMENT','OTHER','DEFERRED_TAWAL','DEFERRED_XXCL'];
    const state = {rows: [], lane: 'RECEIPTS', bank: 'ALL', selected: '', search: '', referenceQueryKey: '', partyQueryKey: '', unpostedOnly: true, markedDocs: [], markedComplete: false};
    root.html(`<header><h2>${__('Review bank movements')}</h2><p>${__('Review bank evidence from connected sources and save an accountant decision. ERP draft creation is not yet enabled.')}</p><button class="btn btn-default" data-refresh>${__('Refresh')}</button></header><label class="snb-bank-filter">${__('Bank')} <select data-bank><option value="ALL">${__('All banks')}</option><option value="SNB">SNB</option><option value="ALINMA">Alinma</option></select></label><label class="snb-unposted"><input type="checkbox" data-unposted checked> ${__('Show unposted and unconfirmed only')}</label><nav data-lanes></nav><input class="form-control" data-search placeholder="${__('Search party, account ending, reference…')}"><section class="snb-grid"><aside><h4 data-title></h4><div data-queue></div></aside><article data-evidence></article><article data-review></article></section>`);
    root.append(`<section class="snb-marked-documents"><details><summary>${__('Bank-linked ERP documents')}</summary><p>${__('These existing accounting documents have a bank statement marker. Journal Entry markers do not identify the bank by themselves.')}</p><div data-marked-documents>${__('Loading…')}</div></details></section>`);
    root.append(`<section class="snb-hint-rules"><details><summary>${__('Confirmed party hint rules')}</summary><p>${__('Rules link an exact SNB narrative hint and company account ending to one ERP Customer or Supplier. They suggest future matches; they do not post or allocate.')}</p><button class="btn btn-default" data-load-rules>${__('Refresh rules')}</button><div data-hint-rules>${__('Open Refresh rules to load saved mappings.')}</div></details></section>`);
    if ((frappe.user_roles||[]).some(role=>['Accounts Manager','System Manager'].includes(role))) root.append(`<section class="snb-hint-rules"><details><summary>${__('Manage approved router parties')}</summary><p>${__('Approvals start empty. Approve an enabled Customer or Supplier before selecting it in this router. Revoking approval also revokes its active hint rules.')}</p><select data-approval-type><option>Customer</option><option>Supplier</option></select><input class="form-control" data-approval-search type="search" placeholder="${__('Search enabled ERP parties')}"><select class="form-control" data-approval-choice><option value="">${__('Choose…')}</option></select><button class="btn btn-default" data-party-approval="APPROVED">${__('Approve')}</button> <button class="btn btn-default" data-party-approval="REVOKED">${__('Revoke approval')}</button><div data-approval-message></div></details></section>`);
    const q = s => el.querySelector(s);
    const bankOf = x => String(x.source.bank || 'SNB').toUpperCase() === 'ALINMA' ? 'ALINMA' : 'SNB';
    const statusFor = x => x.readback?.status || 'UNKNOWN';
    const statusLabel = x => ({POSTED:'✓ '+__('Posted'), DRAFT:'○ '+__('Draft'), CANCELLED:__('Cancelled'), AMBIGUOUS:__('Ambiguous'), UNAVAILABLE:__('Access unavailable'), UNKNOWN:__('Unconfirmed')})[statusFor(x)] || __('Unconfirmed');
    const isComplete = x => {
        if (statusFor(x)!=='POSTED') return false;
        const links=x.recognition?.related_fee_rows||[], related=feeRowsFor(x);
        return links.length===related.length && related.every(row=>statusFor(row)==='POSTED');
    };
    const bankRows = () => {
        const byId=new Map(state.rows.map(row=>[row.id,row])), grouped=new Set();
        for(const parent of state.rows) for(const line of parent.recognition?.related_fee_rows||[]) {
            const fee=byId.get(line.review_id);
            if(fee && fee.account_scope_hash && fee.account_scope_hash===parent.account_scope_hash && fee.recognition?.related_main_key===parent.source?.statement_key) grouped.add(fee.id);
        }
        return state.rows.filter(x => (state.bank === 'ALL' || bankOf(x) === state.bank) && !grouped.has(x.id) && (!state.unpostedOnly || !isComplete(x)));
    };
    const opt = (items, value, labels={}) => '<option value="">' + __('Choose…') + '</option>' + items.map(x => `<option value="${esc(x)}" ${x===value?'selected':''}>${esc(labels[x] || x.replaceAll('_',' '))}</option>`).join('');
    const selected = () => state.rows.find(x => x.name === state.selected);
    const referenceKey = (doctype,name) => doctype && name ? `${doctype}::${name}` : '';
    const requestReference = x => {
        const raw=x?.recognition?.transfer_request?.allocation_json || x?.source?.transfer_request?.allocation_json;
        try { const rows=Array.isArray(raw)?raw:JSON.parse(String(raw||'[]')); return Array.isArray(rows)?rows[0]||null:null; } catch(e) { return null; }
    };
    const formatCurrency=(amount,currency)=>`${Number(amount||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})} ${currency||''}`;
    // Statement format and hint candidates come from the server so the page and the API cannot disagree.
    const hintOptionsOf = x => (x?.hint_options || []).map(option => [option.kind, option.value]);
    function feeRowsFor(x) {
        const keys=new Set((x.recognition.related_fee_rows||[]).map(row=>String(row.review_id||'')).filter(Boolean));
        if(!keys.size) return [];
        return state.rows.filter(row=>row.name!==x.name && keys.has(String(row.id||'')));
    }
    async function loadPartyOptions(doctype, selectedName='') {
        const query=q('[data-party-search]')?.value.trim()||selectedName||'';
        const key=`${selected()?.name||''}|${doctype}|${query}|${selectedName}`;
        state.partyQueryKey=key;
        const select=q('[data-field="party"]'); if(!select) return;
        try {
            const response=await frappe.call({method:method+'search_parties',args:{doctype,query}});
            if(state.partyQueryKey!==key || selected()?.name!==key.split('|')[0]) return;
            const options=response.message||[];
            if(selectedName && selected()?.review?.party===selectedName && selected()?.review?.party_type===doctype && !options.some(row=>row.name===selectedName)) options.unshift({name:selectedName,label:`${selectedName} · ${__('previously saved')}`});
            select.innerHTML='<option value="">'+esc(__('Choose…'))+'</option>'+options.map(row=>`<option value="${esc(row.name)}" ${row.name===selectedName?'selected':''}>${esc(row.label)}</option>`).join('');
        } catch(e) { if(state.partyQueryKey===key) select.innerHTML='<option value="">'+esc(__('Party list unavailable; check your access'))+'</option>'; }
    }
    function setPartyControl(type, value='') {
        const previous=q('[data-field="party"]'), search=q('[data-party-search]');
        if(!previous || !search) return;
        const searchable=['Customer','Supplier'].includes(type);
        const control=document.createElement(searchable?'select':'input');
        control.dataset.field='party';
        if(!searchable) { control.value=value; control.placeholder=__('Enter the exact ERP record name'); }
        previous.replaceWith(control);
        search.style.display=searchable?'':'none';
        const note=search.parentElement.querySelector('small'); if(note) { note.style.display=searchable?'':'none'; if(searchable) note.textContent=__('Only approved, enabled ERP records visible to your account are listed.'); }
        if(search.parentElement.firstChild?.nodeType===Node.TEXT_NODE) search.parentElement.firstChild.nodeValue=searchable?__('Search approved ERP {0}',[type]):__('ERP party');
        if(searchable) loadPartyOptions(type,value);
    }
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
    // keepForm: refresh the list and evidence (for example when a read-back arrives) without resetting a decision being typed.
    function render(options = {}) {
        const previousSelected = state.selected;
        const sourceRows = bankRows();
        q('[data-lanes]').innerHTML = Object.entries(lanes).map(([key, label]) => `<button class="btn ${state.lane===key?'btn-primary':'btn-default'}" data-lane="${key}">${__(label)} · ${sourceRows.filter(x => (x.review.lane || x.recognition.lane) === key).length}</button>`).join('');
        q('[data-title]').textContent = __(lanes[state.lane]);
        const list = sourceRows.filter(x => (x.review.lane || x.recognition.lane) === state.lane && JSON.stringify([x.source,x.recognition,x.review.party]).toLowerCase().includes(state.search));
        if (!list.some(x => x.name === state.selected)) state.selected = list[0]?.name || '';
        const keepForm = Boolean(options.keepForm && previousSelected === state.selected && q('[data-review] [data-field]'));
        q('[data-queue]').innerHTML = list.map(x => `<button class="snb-row ${state.selected===x.name?'selected':''}" data-row="${esc(x.name)}"><strong>${Number(x.source.signed_amount || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})} ${esc(x.source.currency)}</strong><span>${esc(bankOf(x))} · ${esc(x.source.event_date)} · ••${esc(x.source.account_tail)}</span><span>${esc(x.review.party || x.erp.proposed_party || x.source.extracted_name || x.source.detail_description || 'Unidentified')}</span><small>${esc(x.review.review_status || x.recognition.status || 'PENDING')}</small></button>`).join('') || `<p>${__('No movements in this view.')}</p>`;
        const x = selected();
        if (!x) { q('[data-evidence]').innerHTML = `<p>${__('Select a movement.')}</p>`; q('[data-review]').innerHTML = ''; return; }
        const s=x.source,r=x.recognition,d=x.review,m=s.beneficiary_mapping || r.am_beneficiary_mapping || {};
        const text=[s.transaction_description,s.detail_description,s.extra_description,s.remarks].filter(Boolean).join('\n');
        const requestRef=requestReference(x), savedRef=referenceKey(d.payment_reference_doctype,d.payment_reference);
        const effectiveRef=savedRef||referenceKey(requestRef?.reference_doctype,requestRef?.reference_name);
        const rawPartyHint=String(m.erp_party||r.transfer_request?.erp_party||x.erp.proposed_party||'').trim();
        const typedPartyHint=rawPartyHint.match(/^(Customer|Supplier):\s*(.+)$/i);
        const suggestion=r.party_suggestion || null;
        const expectedPartyType=s.direction==='CREDIT'?'Customer':'Supplier';
        const partyValue=d.party||suggestion?.party||(typedPartyHint?.[1]?.toLowerCase()===expectedPartyType.toLowerCase()?typedPartyHint[2].trim():'');
        const partyTypeValue=d.party_type||suggestion?.party_type||(typedPartyHint?.[1]||'');
        const family=x.family || suggestion?.narrative_family || '';
        const hintOptions=hintOptionsOf(x);
        const managerHint=(r.transfer_request?`<h5>${__('TX Manager evidence · review required')}</h5><p>${esc(r.transfer_request.beneficiary||'')} · ${esc(r.transfer_request.erp_party||'')} · ${esc(r.am_category_status||'')}</p>`:'')+(requestRef?`<h5>${__('TX Manager reference · pending accountant confirmation')}</h5><p>${requestRef.reference_doctype==='Purchase Order'?__('Advance reference'):__('Invoice allocation')} · ${esc(requestRef.reference_doctype)} ${esc(requestRef.reference_name)} · ${formatCurrency(requestRef.allocated_amount,s.currency)}</p>`:'');
        const related=feeRowsFor(x);
        const accounting=(x.readback?.documents||[]).map(doc=>`<p><a href="#" data-erp-doctype="${esc(doc.doctype)}" data-erp-name="${esc(doc.name)}">${esc(doc.doctype)} · ${esc(doc.name)}</a> · ${esc(doc.status)}</p>`).join('');
        const suggestedHtml=suggestion?.status==='RULE_SUGGESTION'?`<div class="snb-hint-suggestion"><strong>${__('Rule suggestion · confirm this movement separately')}</strong><p>${esc(suggestion.party_label||suggestion.party)} · ${esc(suggestion.party_type)} · ${esc(suggestion.narrative_family)} · ${esc(suggestion.hint_value)}</p><small>${__('Saved ERP rule; it is also copied to Sheet Am on the next router sync.')}</small></div>`:suggestion?.status==='AMBIGUOUS_RULE'?`<div class="snb-hint-suggestion"><strong>${__('More than one saved hint fits this statement. Choose the party manually.')}</strong><ul>${(suggestion.candidates||[]).map(candidate=>`<li>${esc(candidate.party_label||candidate.party)} · ${esc(candidate.party_type)} · ${esc(candidate.hint)}</li>`).join('')}</ul></div>`:'';
        q('[data-evidence]').innerHTML = `<h3>${esc(bankOf(x))} · ${__('Bank evidence')}</h3><div class="snb-amount">${Number(s.signed_amount || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})} ${esc(s.currency)}</div><p>${esc(s.event_date)} · ••${esc(s.account_tail)} · ${__('Reference')} ${esc(s.reference || '—')}</p><p>${esc(s.extracted_name || m.beneficiary_name || m.nickname || __('Party not identified'))}</p><p>${__('ERP status')}: ${esc(statusLabel(x))}</p>${accounting}${suggestedHtml}${related.length?`<details class="snb-related-fees" open><summary>${__('Related bank fees / VAT')} · ${related.length}</summary>${related.map(row=>`<p>${esc(row.source.parser_family==='FEE_VAT'?'VAT':'Fee')} · ${esc(formatCurrency(row.source.signed_amount,row.source.currency))} · ${esc(row.source.event_date)} · ${esc(statusLabel(row))} ${(row.readback?.documents||[]).map(doc=>`<a href="#" data-erp-doctype="${esc(doc.doctype)}" data-erp-name="${esc(doc.name)}">${esc(doc.name)}</a>`).join(' ')}</p>`).join('')}<small>${__('Each statement line keeps its own accounting document and status.')}</small></details>`:''}<details><summary>${__('Statement and matching evidence')}</summary><h5>${__('Statement narrative')}</h5><pre>${esc(text || '—')}</pre><h5>${__('Recognition evidence')}</h5><p>${esc(r.reason || 'No route suggestion')}</p><p>${(r.evidence || []).map(esc).join(' · ')}</p>${bankOf(x)==='SNB'?`<h5>${__('AM beneficiary mapping')}</h5><p>${esc(m.beneficiary_name || m.nickname || 'Not matched')} · ${esc(m.status || '—')} · ${esc(m.erp_party || 'No ERP party')}</p>`:''}${managerHint}<h5>${__('ERP link hint')}</h5><p>${esc(x.erp.linked_doc || 'None')} ${x.erp.linked_doc && !accounting ? '· ' + __('Read-back required') : ''}</p><small>${__('Source evidence is immutable.')} ${esc(x.id)}</small></details>`;
        const partyOpt='';
        const partyType= s.direction==='CREDIT'?'Customer':'Supplier';
        const hintKinds=[...new Set([...hintOptions.map(([kind])=>kind),'NAME'])];
        const company=d.company||frappe.defaults.get_global_default('company')||'';
        if (!keepForm) q('[data-review]').innerHTML = `<h3>${__('Accountant decision')}</h3><p>${__('Choose the ERP party for this movement. Every movement remains separately reviewable.')}</p><label>${__('Lane')}<select data-field="lane">${opt(Object.keys(lanes),d.lane || r.lane,lanes)}</select></label><label>${__('Route')}<select data-field="route">${opt(routes,d.route || r.route)}</select></label><label>${__('Category')}<select data-field="category">${opt(['XXPC','XXSL','XXCL','XXMT','XXMR','XXOM','XXSC','XXLG','XXHR','ALINMA_SALARY_CANDIDATE'],d.category || r.category,{XXPC:__('Petty Cash')})}</select></label><label>${__('Party type')}<select data-field="party_type">${opt([partyType,'Employee','Other'],partyTypeValue||partyType)}</select></label><label>${__('Search approved ERP {0}',[partyType])}<input data-party-search type="search" placeholder="${__('Type at least two characters')}"><select data-field="party">${partyOpt}</select><small>${__('Only approved, enabled ERP records visible to your account are listed.')}</small></label>${family?`<section class="snb-hint-rule"><h4>${__('Reusable statement hint')}</h4><p>${esc(family)} · ••${esc(s.account_tail)}</p><label>${__('Hint type')}<select data-hint-kind>${opt(hintKinds,hintOptions[0]?.[0]||'NAME')}</select></label><label>${__('Exact stable text in the statement')}<input data-hint-value value="${esc(hintOptions[0]?.[1]||'')}"></label><button class="btn btn-default" data-save-hint ${x.account_scope_hash?'':'disabled'}>${__('Save hint rule for future suggestions')}</button><small>${x.account_scope_hash?__('Matching unconfirmed movements get a suggestion at once; each still needs review. The next SNB router sync copies the rule to Sheet Am.'):__('Refresh the SNB review sync to establish this account scope before saving a reusable hint.')}</small><div data-hint-message></div></section>`:''}<details><summary>${__('More accounting details')}</summary><label>${__('Company')}<input data-field="company" value="${esc(company)}"></label><label>${__('Bank GL account')}<input data-field="bank_account" value="${esc(d.bank_account || '')}"></label><label>${__('Counter GL account')}<input data-field="counter_account" value="${esc(d.counter_account || '')}"></label><label>${__('Material treatment')}<select data-field="material_treatment">${opt(['STOCK','OPERATIONAL_NON_STOCK'],d.material_treatment)}</select></label>${s.direction==='DEBIT'?`<section class="snb-payment-reference"><h4>${__('Supplier payment reference · optional')}</h4><label>${__('Document')}<select data-reference-choice><option value="" ${effectiveRef?'':'selected'}>${__('No document · leave unallocated')}</option>${effectiveRef?`<option value="${esc(effectiveRef)}" selected>${esc(effectiveRef.replace('::',' · '))}</option>`:''}</select></label><label>${__('Allocated amount')}<input data-reference-amount type="number" min="0" max="${Math.abs(Number(s.signed_amount||0))}" step="0.01" value="${esc(d.payment_reference_amount || requestRef?.allocated_amount || '')}"></label><small data-reference-status>${__('Select Supplier and Company to load submitted documents.')}</small></section>`:''}</details><label>${__('Review state')}<select data-field="review_status">${opt(['PENDING','REVIEWED','NEEDS_CLARIFICATION','DEFERRED'],d.review_status || 'PENDING')}</select></label><label>${__('Note')}<textarea data-field="notes">${esc(d.notes || '')}</textarea></label><button class="btn btn-primary" data-save>${__('Save decision')}</button><div data-message></div>`;
        if (!keepForm) {
            setPartyControl(q('[data-field="party_type"]')?.value||partyType, partyValue);
            loadPaymentReferences(x);
        }
    }
    async function loadMarkedDocuments() {
        const target=q('[data-marked-documents]'); state.markedComplete=false;
        try {
            const all=[], unavailable=[];
            for (const doctype of ['Payment Entry','Journal Entry']) {
                let start=0, part;
                do {
                    const response=await frappe.call({method:method+'list_marked_documents',args:{doctype,start,limit:200}});
                    const data=response.message || {};
                    if (!data.available) { unavailable.push(doctype); break; }
                    part=data.rows || []; all.push(...part); start+=part.length;
                } while(part.length===200);
            }
            state.markedDocs=all; state.markedComplete=unavailable.length===0;
            const visible=state.unpostedOnly ? all.filter(x=>Number(x.docstatus)===0) : all;
            target.innerHTML=(unavailable.length ? `<p>${__('Some document types are unavailable to your account')}: ${unavailable.map(esc).join(', ')}</p>` : '') +
                (visible.length ? visible.map(x=>`<p><a href="#" data-erp-doctype="${esc(x.doctype)}" data-erp-name="${esc(x.name)}">${esc(x.doctype)} · ${esc(x.name)}</a> · ${esc(x.posting_date)} · ${esc(x.bank==='SNB'?'SNB':__('Bank unconfirmed'))} · ${esc(({0:__('Draft'),1:__('Submitted'),2:__('Cancelled')})[x.docstatus] || __('Unknown'))}<br><small>${__('Statement marker')}: ${esc(x.statement_key)}</small></p>`).join('') : `<p>${__('No marked ERP documents visible.')}</p>`);
        } catch(e) { target.textContent=__('Could not load marked ERP documents. Check your document access and refresh.'); }
    }
    async function load() {
        try { await loadMarkedDocuments(); let rows=[],start=0,part; do { part=(await frappe.call({method:method+'list_movements',args:{start,limit:200}})).message || []; rows=rows.concat(part); start+=part.length; } while(part.length===200 && start<10000); state.rows=rows; render(); await loadReadbacks(); }
        catch(e) { frappe.msgprint(__('Could not load bank movements. Check your access.')); }
    }
    async function loadReadbacks() {
        const candidates=state.rows.filter(row=>bankOf(row)==='SNB' && row.erp?.linked_doc);
        for(let i=0;i<candidates.length;i+=50) {
            const chunk=candidates.slice(i,i+50);
            try {
                const response=await frappe.call({method:method+'readback_movements',type:'POST',args:{names:chunk.map(row=>row.name)}});
                const map=new Map((response.message||[]).map(row=>[row.name,row]));
                chunk.forEach(row=>{row.readback=map.get(row.name)||{status:'UNKNOWN'};});
            } catch(e) { chunk.forEach(row=>{row.readback={status:'UNAVAILABLE'};}); }
            render({keepForm: true});
        }
    }
    async function loadHintRules() {
        const target=q('[data-hint-rules]'); target.textContent=__('Loading…');
        try {
            let rows=[],start=0,part;
            do { part=(await frappe.call({method:method+'list_hint_rules',args:{start,limit:200}})).message||[]; rows.push(...part); start+=part.length; }
            while(part.length===200 && start<10000);
            target.innerHTML=rows.length?rows.map(rule=>`<div class="snb-hint-rule-row"><span><strong>${esc(rule.party_label||rule.party)}</strong> · ${esc(rule.party_type)} · ${esc(rule.display_hint)} · ${esc(rule.narrative_family)} · ••${esc(rule.account_tail)}<small>${esc(rule.status)} · ${esc(rule.sync_status)}</small></span><span>${rule.sync_status==='FAILED'?`<button class="btn btn-default btn-xs" data-retry-rule="${esc(rule.name)}" data-modified="${esc(rule.modified)}">${__('Queue retry')}</button>`:''} ${rule.status==='ACTIVE'?`<button class="btn btn-default btn-xs" data-revoke-rule="${esc(rule.name)}" data-modified="${esc(rule.modified)}">${__('Revoke')}</button>`:''}</span></div>`).join(''):`<p>${__('No party hint rules have been saved.')}</p>`;
        } catch(e) { target.textContent=__('Could not load saved party hint rules. Check your access.'); }
    }
    root.on('click','[data-erp-doctype]',function(event){event.preventDefault();frappe.set_route('Form',this.dataset.erpDoctype,this.dataset.erpName);});
    root.on('click','[data-lane]',function(){state.lane=this.dataset.lane;state.selected='';render();});
    root.on('change','[data-unposted]',async function(){state.unpostedOnly=this.checked;state.selected='';await loadMarkedDocuments();render();});
    root.on('change','[data-bank]',function(){state.bank=this.value;state.selected='';render();});
    root.on('click','[data-row]',function(){state.selected=this.dataset.row;render();});
    root.on('input','[data-search]',function(){state.search=this.value.toLowerCase();render();});
    root.on('click','[data-refresh]',load);
    root.on('click','[data-load-rules]',loadHintRules);
    let approvalSearchTimer;
    root.on('input change','[data-approval-search], [data-approval-type]',function(){clearTimeout(approvalSearchTimer);approvalSearchTimer=setTimeout(async()=>{const query=q('[data-approval-search]')?.value.trim()||'',doctype=q('[data-approval-type]')?.value,select=q('[data-approval-choice]');if(!select)return;if(query.length<2){select.innerHTML='<option value="">'+esc(__('Type at least two characters'))+'</option>';return;}try{const result=await frappe.call({method:method+'search_active_parties_for_approval',args:{doctype,query}});if(q('[data-approval-search]')?.value.trim()!==query||q('[data-approval-type]')?.value!==doctype)return;select.innerHTML='<option value="">'+esc(__('Choose…'))+'</option>'+(result.message||[]).map(row=>`<option value="${esc(row.name)}">${esc(row.label)}</option>`).join('');}catch(e){q('[data-approval-message]').textContent=__('Could not search ERP parties.');}},250);});
    root.on('click','[data-party-approval]',async function(){const party=q('[data-approval-choice]')?.value||'',party_type=q('[data-approval-type]')?.value||'',message=q('[data-approval-message]');if(!party){message.textContent=__('Choose an ERP party first.');return;}this.disabled=true;try{await frappe.call({method:method+'set_party_approval',type:'POST',args:{party_type,party,status:this.dataset.partyApproval}});message.textContent=__('Party approval updated.');loadHintRules();}catch(e){message.textContent=__('Could not update approval. Check your permissions and refresh.');}finally{this.disabled=false;}});
    root.on('click','[data-revoke-rule]',async function(){const button=this;button.disabled=true;try{await frappe.call({method:method+'set_hint_rule_status',type:'POST',args:{name:button.dataset.revokeRule,modified:button.dataset.modified,status:'REVOKED',note:'Revoked from Bank Movement Router'}});await loadHintRules();frappe.show_alert({message:__('Hint rule revoked; prior movement decisions were retained.'),indicator:'green'});}catch(e){q('[data-hint-rules]').textContent=__('Could not revoke this rule. Refresh the list and try again.');}finally{button.disabled=false;}});
    root.on('click','[data-retry-rule]',async function(){const button=this;button.disabled=true;try{await frappe.call({method:method+'retry_hint_rule',type:'POST',args:{name:button.dataset.retryRule,modified:button.dataset.modified}});await loadHintRules();frappe.show_alert({message:__('Queued for the next SNB router sync.'),indicator:'green'});}catch(e){q('[data-hint-rules]').textContent=__('Could not queue retry. Refresh the list and try again.');}finally{button.disabled=false;}});
    root.on('change','[data-field="party_type"], [data-field="party"], [data-field="company"]',function(){state.referenceQueryKey='';const x=selected();if(x)loadPaymentReferences(x);});
    let partySearchTimer;
    root.on('input','[data-party-search]',function(){const type=q('[data-field="party_type"]')?.value;if(!['Customer','Supplier'].includes(type))return;clearTimeout(partySearchTimer);partySearchTimer=setTimeout(()=>loadPartyOptions(type,''),250);});
    root.on('change','[data-field="party_type"]',function(){setPartyControl(this.value,'');});
    root.on('change','[data-reference-choice]',function(){const amount=q('[data-reference-amount]');if(this.value&&amount&&!amount.value)amount.value=Math.abs(Number(selected()?.source?.signed_amount||0)).toFixed(2);if(!this.value&&amount)amount.value='';});
    root.on('change','[data-hint-kind]',function(){const x=selected(),input=q('[data-hint-value]'),option=hintOptionsOf(x).find(([kind])=>kind===this.value);if(input&&option)input.value=option[1];});
    root.on('click','[data-save]',async function(){const x=selected();if(!x)return;const decision={};el.querySelectorAll('[data-field]').forEach(n=>decision[n.dataset.field]=n.value);const choice=q('[data-reference-choice]')?.value||'';const sep=choice.indexOf('::');decision.payment_reference_doctype=sep>0?choice.slice(0,sep):'';decision.payment_reference=sep>0?choice.slice(sep+2):'';decision.payment_reference_amount=decision.payment_reference?Number(q('[data-reference-amount]')?.value||0):0;this.disabled=true;try{const result=await frappe.call({method:method+'save_review',type:'POST',args:{name:x.name,modified:x.modified,decision}});const index=state.rows.findIndex(z=>z.name===x.name);state.rows[index]=result.message;state.referenceQueryKey='';render();frappe.show_alert({message:__('Decision saved'),indicator:'green'});}catch(e){q('[data-message]').textContent=__('Could not save. Check the error and refresh if the row changed.');}finally{this.disabled=false;}});
    root.on('click','[data-save-hint]',async function(){const x=selected(),kind=q('[data-hint-kind]')?.value||'',value=q('[data-hint-value]')?.value||'';if(!x||!kind||!value.trim())return;const partyType=q('[data-field="party_type"]')?.value||'',party=q('[data-field="party"]')?.value||'';const message=q('[data-hint-message]');if(!party||!['Customer','Supplier'].includes(partyType)){message.textContent=__('Select an approved ERP Customer or Supplier first.');return;}this.disabled=true;try{const result=await frappe.call({method:method+'confirm_party_hint',type:'POST',args:{name:x.name,modified:x.modified,hint_kind:kind,hint_value:value,party_type:partyType,party}});const index=state.rows.findIndex(z=>z.name===x.name);state.rows[index]=result.message.movement;render();if(q('[data-field="party_type"]'))q('[data-field="party_type"]').value=partyType;setPartyControl(partyType,party);loadHintRules();frappe.show_alert({message:__('Hint rule saved and active. Save this movement decision separately; Sheet Am copy follows on the next sync.'),indicator:'green'});}catch(e){message.textContent=__('Could not save this hint rule. Check whether the hint conflicts with an existing rule and refresh.');}finally{this.disabled=false;}});
    load();
};
