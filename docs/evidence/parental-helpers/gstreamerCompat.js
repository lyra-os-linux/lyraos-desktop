// GNOME Shell 48 passes null to Gst.init/init_check. The GStreamer 1.28
// introspection metadata shipped in Leap 16.1 rejects that argument in GJS.
// Normalize only the argument; keep native initialization and errors intact.
// This namespace is private to the screencast service process.
export function installGStreamerCompatibility(Gst) {
    const init = Gst.init;
    const initCheck = Gst.init_check;
    Gst.init = argv => init(argv ?? []);
    Gst.init_check = argv => initCheck(argv ?? []);
}
