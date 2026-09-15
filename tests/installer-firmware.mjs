// Exercise the real disk renderer and locale catalogs without disk operations.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../installer/ui/app.js', import.meta.url), 'utf8');
const catalog = fs.readFileSync(new URL('../installer/ui/i18n.js', import.meta.url), 'utf8');
function declaration(name) {
    return source.slice(source.indexOf(`function ${name}(`)).split(/\n(?:async )?function /)[0];
}
for (const [locale, message] of [
    ['en-US', 'requires UEFI boot'], ['pt-BR', 'requer inicialização UEFI'],
    ['es-ES', 'requiere arranque UEFI'],
]) {
    const elements = Object.fromEntries(['#disk-list', '#disk-count', '#disk-plan'].map(key => [key, {}]));
    const context = vm.createContext({
        window: {}, document: {documentElement: {}, querySelector: key => elements[key]},
        next: {disabled: false, style: {}}, current: 5, installing: false, installationTerminal: false,
        selectedPlan: {old: true}, selectedDiskPath: '/dev/vda',
        storageSnapshot: {uefi: false, disks: [{path: '/dev/vda'}]},
    });
    vm.runInContext(catalog, context);
    context.i18n = context.window.LyraI18n;
    context.i18n.apply(locale);
    vm.runInContext(['diskIneligibleReason', 'updateNextButtonState', 'renderDiskCards'].map(declaration).join('\n'), context);
    for (const firmware of [false, undefined]) {
        context.storageSnapshot.uefi = firmware;
        context.selectedPlan = {old: true};
        context.selectedDiskPath = '/dev/vda';
        context.renderDiskCards();
        assert.match(elements['#disk-list'].innerHTML, new RegExp(message));
        assert.equal(context.selectedPlan, null);
        assert.equal(context.selectedDiskPath, null);
        assert.equal(context.next.disabled, true);
        assert.equal(elements['#disk-plan'].hidden, true);
        assert.match(context.diskIneligibleReason({}), new RegExp(message));
    }
    context.storageSnapshot.uefi = true;
    assert.equal(context.diskIneligibleReason({role: 'Free', is_live_media: false}), null);
    assert.notEqual(context.diskIneligibleReason({role: 'Free', is_live_media: true}), null);
}
console.log('PASS: BIOS/unknown firmware clears stale plans and disables Continue in PT/EN/ES; UEFI eligibility preserved');
