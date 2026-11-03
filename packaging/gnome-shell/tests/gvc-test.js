// Open a Gvc.MixerControl, as gnome-shell's volume indicator does, and keep
// the main loop running long enough to process the card list.
imports.gi.versions.Gvc = '1.0';
const {GLib, Gvc} = imports.gi;
const loop = new GLib.MainLoop(null, false);
const control = new Gvc.MixerControl({name: 'lyra-shell01-test'});
control.connect('card-added', (c, id) => print(`card-added ${id}`));
control.connect('state-changed', (c, s) => print(`state ${s}`));
control.open();
GLib.timeout_add(GLib.PRIORITY_DEFAULT, 3000, () => { print('SURVIVED'); loop.quit(); return false; });
loop.run();
