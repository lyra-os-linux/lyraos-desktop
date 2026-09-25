// Exercise real disk/boot-plan renderers and catalogs without disk operations.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source = fs.readFileSync(new URL('../installer/ui/app.js', import.meta.url), 'utf8');
const catalog = fs.readFileSync(new URL('../installer/ui/i18n.js', import.meta.url), 'utf8');
function declaration(name) {
    return source.slice(source.indexOf(`function ${name}(`)).split(/\n(?:async )?function /)[0];
}
for (const locale of ['en-US', 'pt-BR', 'es-ES']) {
    const elements = Object.fromEntries(['#disk-list', '#disk-count', '#disk-plan'].map(key => [key, {}]));
    const disk = {path: '/dev/vda', kname: 'vda', transport: 'Virtio', role: 'Free', is_live_media: false,
        size_bytes: 40 * 1024 ** 3, partitions: []};
    const context = vm.createContext({
        window: {}, document: {documentElement: {}, querySelector: key => elements[key]},
        next: {disabled: false, style: {}}, current: 5, installing: false, installationTerminal: false,
        selectedPlan: {old: true}, selectedDiskPath: '/dev/vda',
        storageSnapshot: {uefi: false, disks: [disk]},
    });
    vm.runInContext(catalog, context);
    context.i18n = context.window.LyraI18n;
    context.i18n.apply(locale);
    vm.runInContext(source.split('\n').find(line => line.startsWith('const transportLabel=')), context);
    vm.runInContext(['diskIneligibleReason', 'updateNextButtonState', 'renderDiskCards', 'diskTitle',
        'diskStatus', 'formatBytes', 'localizedErasedItems', 'renderPlan'].map(declaration).join('\n'), context);
    for (const firmware of [false, true]) {
        context.storageSnapshot.uefi = firmware;
        context.renderDiskCards();
        assert.match(elements['#disk-list'].innerHTML, /\/dev\/vda/);
        assert.equal(context.diskIneligibleReason(disk), null);
        assert.notEqual(context.diskIneligibleReason({...disk, is_live_media: true}), null);
        const plan = {firmware: firmware ? 'Uefi' : 'Bios',
            esp: firmware ? {Create: {size_bytes: 300 * 1024 ** 2}} : 'NotRequired',
            swap: 'Zram', root_filesystem: {Btrfs: {subvolumes: []}}};
        context.renderPlan(plan);
        assert.match(elements['#disk-plan'].innerHTML, firmware ? /UEFI.*NVRAM/ : /BIOS.*2 MiB/);
    }
    for (const unknown of [undefined, null, 'false']) {
        context.storageSnapshot.uefi = unknown;
        context.selectedPlan = {old: true};
        context.selectedDiskPath = '/dev/vda';
        context.renderDiskCards();
        assert.equal(context.selectedPlan, null);
        assert.equal(context.selectedDiskPath, null);
        assert.equal(context.next.disabled, true);
        assert.equal(elements['#disk-plan'].hidden, true);
    }
}
console.log('PASS: BIOS/UEFI boot plans in PT/EN/ES; unknown firmware clears stale plans and blocks Continue; live disk protected');
