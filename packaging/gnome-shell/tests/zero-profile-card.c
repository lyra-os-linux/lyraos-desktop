/* LD_PRELOAD shim: before the real card list, report one card in the state
 * pipewire-pulse sent on 2026-11-02 ("profiles inconsistent (0 < 1)"):
 * n_profiles == 0, so libpulse leaves active_profile NULL. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <pulse/introspect.h>

typedef pa_operation *(*list_fn) (pa_context *, pa_card_info_cb_t, void *);

pa_operation *
pa_context_get_card_info_list (pa_context *c, pa_card_info_cb_t cb, void *userdata)
{
        static pa_card_port_info port;
        static pa_card_port_info *ports[2] = { &port, NULL };
        static pa_card_info info;
        list_fn real = (list_fn) dlsym (RTLD_NEXT, "pa_context_get_card_info_list");

        memset (&port, 0, sizeof port);
        port.name = "analog-input-mic";
        port.description = "Microphone";
        port.priority = 8700;
        port.available = PA_PORT_AVAILABLE_UNKNOWN;
        port.direction = PA_DIRECTION_INPUT;
        port.proplist = pa_proplist_new ();
        port.n_profiles = 0;

        memset (&info, 0, sizeof info);
        info.index = 9999;
        info.name = "alsa_card.usb-lyra-shell01-zero-profiles";
        info.owner_module = PA_INVALID_INDEX;
        info.driver = "alsa";
        info.n_profiles = 0;
        info.profiles = NULL;
        info.active_profile = NULL;
        info.proplist = pa_proplist_new ();
        pa_proplist_sets (info.proplist, "device.description", "SHELL-01 zero-profile card");
        info.n_ports = 1;
        info.ports = ports;
        info.profiles2 = NULL;
        info.active_profile2 = NULL;

        fprintf (stderr, "SHIM: injecting card 9999 with n_profiles=0 active_profile=NULL\n");
        cb (c, &info, 0, userdata);
        return real (c, cb, userdata);
}
