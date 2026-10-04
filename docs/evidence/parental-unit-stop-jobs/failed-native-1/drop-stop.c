/* Actual unread-reply disconnect, restricted by the trusted VM caller. */
#include <systemd/sd-bus.h>
#include <stdio.h>
#include <unistd.h>
int main(int argc, char **argv) {
    sd_bus *bus = NULL;
    sd_bus_message *message = NULL;
    int status = 1;
    if (argc != 2) return 2;
    if (sd_bus_open_system(&bus) < 0) goto done;
    if (sd_bus_message_new_method_call(bus, &message, "org.freedesktop.systemd1",
        "/org/freedesktop/systemd1", "org.freedesktop.systemd1.Manager", "StopUnit") < 0) goto done;
    if (sd_bus_message_append(message, "ss", argv[1], "fail") < 0) goto done;
    if (sd_bus_send(bus, message, NULL) < 0 || sd_bus_flush(bus) < 0) goto done;
    /* Never process/read the method reply; give the manager time to accept. */
    usleep(200000);
    puts("request-flushed-reply-unread-connection-closed");
    status = 0;
done:
    sd_bus_message_unref(message);
    sd_bus_flush_close_unref(bus);
    return status;
}
