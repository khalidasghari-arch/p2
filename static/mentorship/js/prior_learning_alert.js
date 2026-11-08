/* Attention and guidance only. Server-side validation remains authoritative. */
(function () {
    'use strict';
    function start() {
        if (document.getElementById('mentorship-prior-ls-dialog')) return;
        const groups = Array.from(document.querySelectorAll('.inline-group')).filter(group =>
            group.querySelector('input[type="checkbox"][name$="-pc"], input[type="checkbox"][name$="-mc"]'));
        if (!groups.length) return;
        const style = document.createElement('style');
        style.textContent = `
        .mls-reminder{background:#f1f7f3;border:1px solid #c9ded2;border-radius:7px;padding:13px 16px;margin:12px 0;color:#173b30;font:14px/1.6 Arial,sans-serif}
        .mls-error-row{outline:2px solid #b35a18;outline-offset:-2px}.mls-error-row .errorlist{white-space:pre-line}
        #mentorship-prior-ls-dialog{box-sizing:border-box;width:min(720px,calc(100vw - 28px));max-height:88vh;margin:auto;padding:0;border:0;border-radius:12px;background:#fff;color:#203a32;box-shadow:0 18px 65px #0006;font:16px/1.6 Arial,sans-serif}
        #mentorship-prior-ls-dialog::backdrop{background:rgba(10,28,23,.65)}
        #mentorship-prior-ls-dialog .mls-header{padding:22px 26px 16px;border-top:6px solid #c26a22;background:#f5f8f6}
        #mentorship-prior-ls-dialog h2{margin:0;font-size:23px;line-height:1.3;color:#083d33}
        #mentorship-prior-ls-dialog .mls-unsaved{margin:9px 0 0;font-size:14px;font-weight:bold;color:#8a3f12}
        #mentorship-prior-ls-dialog .mls-body{padding:20px 26px;max-height:48vh;overflow:auto}
        #mentorship-prior-ls-dialog .mls-body p{font-size:16px;margin:0 0 14px;line-height:1.6}
        #mentorship-prior-ls-dialog ol{padding-left:23px;margin:0 0 15px}#mentorship-prior-ls-dialog li{margin:0 0 12px;font-size:15px}
        #mentorship-prior-ls-dialog .mls-actions{padding:16px 26px 22px;display:flex;gap:12px;flex-wrap:wrap;border-top:1px solid #dbe5df}
        #mentorship-prior-ls-dialog button{padding:11px 17px;border:1px solid #083d33;border-radius:6px;background:#083d33;color:#fff;font:600 14px/1.4 Arial,sans-serif;cursor:pointer}
        #mentorship-prior-ls-dialog button.mls-close{background:white;color:#083d33}
        #mentorship-prior-ls-dialog button:focus-visible{outline:3px solid #d47a32;outline-offset:3px}
        .mls-fallback-shade{position:fixed;inset:0;background:rgba(10,28,23,.65);z-index:99998}
        #mentorship-prior-ls-dialog.mls-fallback{position:fixed;inset:50% auto auto 50%;transform:translate(-50%,-50%);display:block;z-index:99999}
        @media(max-width:480px){#mentorship-prior-ls-dialog .mls-header,#mentorship-prior-ls-dialog .mls-body,#mentorship-prior-ls-dialog .mls-actions{padding-left:18px;padding-right:18px}#mentorship-prior-ls-dialog h2{font-size:20px}}
        @media print{#mentorship-prior-ls-dialog,.mls-fallback-shade{display:none!important}}`;
        document.head.appendChild(style);
        function element(tag, text, className) {
            const node = document.createElement(tag);
            if (text) node.textContent = text;
            if (className) node.className = className;
            return node;
        }
        groups.forEach(group => {
            const note = element('p', 'Before recording PC or MC, confirm that the mentee has a Learning Session (LS) for the same topic on an earlier visit date. This requirement also applies when updating records.', 'mls-reminder');
            note.setAttribute('role', 'note');
            const table = group.querySelector('table');
            if (table) table.parentNode.insertBefore(note, table);
            else group.prepend(note);
        });
        const matched = Array.from(new Set(groups.flatMap(group =>
            Array.from(group.querySelectorAll('.errorlist li')).map(node => node.textContent.trim()).filter(text =>
                text.includes('A previous Learning Session (LS) must be recorded for') ||
                text.includes('Prior Learning Session Required.') ||
                text.includes('This change would leave an existing PC/MC record without an earlier learning session.')))));
        if (!matched.length) return;
        const errorRows = groups.flatMap(group => Array.from(group.querySelectorAll('.row-form-errors')).filter(row =>
            row.textContent.includes('A previous Learning Session (LS) must be recorded for')));
        errorRows.forEach(row => { row.classList.add('mls-error-row'); if (row.nextElementSibling) row.nextElementSibling.classList.add('mls-error-row'); });
        const dialog = element('dialog');
        dialog.id = 'mentorship-prior-ls-dialog';
        dialog.setAttribute('role', 'alertdialog');
        dialog.setAttribute('aria-modal', 'true');
        dialog.setAttribute('aria-labelledby', 'mls-dialog-title');
        dialog.setAttribute('aria-describedby', 'mls-dialog-description');
        const header = element('div', '', 'mls-header');
        const title = element('h2', 'Prior Learning Session Required'); title.id = 'mls-dialog-title';
        header.append(title, element('p', 'Your changes have not been saved.', 'mls-unsaved'));
        const body = element('div', '', 'mls-body'); body.id = 'mls-dialog-description';
        const rowMessages = matched.filter(text => text.startsWith('A previous Learning Session (LS) must be recorded for'));
        if (rowMessages.length === 1) {
            rowMessages[0].split(/\n\s*\n/).forEach(part => body.appendChild(element('p', part)));
        } else if (rowMessages.length > 1) {
            body.appendChild(element('p', 'Please review the following mentorship entries:'));
            const list = element('ol');
            rowMessages.forEach(text => list.appendChild(element('li', text.split(/\n\s*\n/)[0])));
            body.append(list, element('p', 'Please confirm the selected mentee, topic and visit date. If the learning session has already taken place, check that it is recorded with a date earlier than this mentorship visit.'));
        } else {
            body.appendChild(element('p', matched.find(text => text.startsWith('This change would leave')) ||
                'Please review the highlighted mentorship entries. A previous Learning Session (LS) for the same mentee and topic must be recorded before PC or MC can be saved.'));
        }
        const actions = element('div', '', 'mls-actions');
        const review = element('button', 'Review affected entries'); review.type = 'button'; review.autofocus = true;
        const close = element('button', 'Close', 'mls-close'); close.type = 'button';
        actions.append(review, close); dialog.append(header, body, actions); document.body.appendChild(dialog);
        let shade;
        const previousFocus = document.activeElement;
        const oldOverflow = document.body.style.overflow;
        function dismiss(goToRows) {
            if (typeof dialog.close === 'function' && dialog.open) dialog.close();
            dialog.remove(); if (shade) shade.remove(); document.body.style.overflow = oldOverflow;
            if (goToRows) {
                const targetRow = errorRows[0] && errorRows[0].nextElementSibling;
                const target = (targetRow && targetRow.querySelector('select[name$="-menteename"], select, input:not([type="hidden"])')) || groups[0];
                target.scrollIntoView({block:'center', behavior:'smooth'});
                if (!target.hasAttribute('tabindex') && target === groups[0]) target.tabIndex = -1;
                target.focus({preventScroll:true});
            } else if (previousFocus && previousFocus.focus) previousFocus.focus();
        }
        review.addEventListener('click', () => dismiss(true));
        close.addEventListener('click', () => dismiss(false));
        dialog.addEventListener('cancel', event => {event.preventDefault(); dismiss(false);});
        dialog.addEventListener('keydown', event => {
            if (event.key === 'Escape') {event.preventDefault(); dismiss(false);}
            if (event.key === 'Tab') {
                if (event.shiftKey && document.activeElement === review) {event.preventDefault(); close.focus();}
                else if (!event.shiftKey && document.activeElement === close) {event.preventDefault(); review.focus();}
            }
        });
        document.body.style.overflow = 'hidden';
        if (typeof dialog.showModal === 'function') dialog.showModal();
        else {shade = element('div', '', 'mls-fallback-shade'); document.body.appendChild(shade); dialog.classList.add('mls-fallback'); dialog.setAttribute('open','');}
        review.focus();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
    else start();
}());
