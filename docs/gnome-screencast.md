# GNOME screen recording on Leap 16.1

The next Desktop ISO includes a compatibility launcher for GNOME Shell's
native screen recorder. On the reference system, GNOME Shell 48.8 with
GStreamer 1.28.5 exits during `Gst.init_check(null)` with:

```text
Expected type utf8 for Argument 'argv' but got type 'null'
```

The required `pipewiresrc`, `filesink`, `capsfilter`, `videoconvert`, `queue`,
`vp8enc`, and `webmmux` elements are all present. This failure happens before
the recorder can check them, and GNOME hides the recording control when the
service fails to initialize.

The image supplies a D-Bus session service override under
`/usr/local/share/dbus-1/services`. This standard XDG location takes precedence
over the vendor service under `/usr/share`; RPM-owned files stay intact. The
launcher converts null initialization arguments to an empty argument array,
then loads the installed GNOME service and resources. Native errors, capture
permissions, recording pipelines, and updates remain under GNOME's control.
The adaptation is confined to the recorder process.

Validation must include the real GJS/GStreamer initialization and GNOME
`ScreencastService.canScreencast()` with the image's installed resources. The
ISO smoke test must also open Print Screen, select recording, save a short
clip, and play it back in both the live session and the installed system.

After the official packages support the original launcher with the same
validation, remove the service override and
`/usr/libexec/lyra-gnome-screencast` from the image overlay. Removing those files
also provides rollback to the vendor entry point. No GStreamer downgrade or
replacement GNOME Shell package is required.
