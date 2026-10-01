/* VM-only minimal GDM session: ends normally; no compositor/logout UI. */
#include <time.h>
#include <errno.h>
int main(void) {
    struct timespec remaining = {30, 0};
    while (nanosleep(&remaining, &remaining) != 0) {
        if (errno != EINTR) return 1;
    }
    return 0;
}
