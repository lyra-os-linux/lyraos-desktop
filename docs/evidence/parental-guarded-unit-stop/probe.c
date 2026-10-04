/* Reserved VM payload: exec another binary on a root-selected interleaving. */
#include <signal.h>
#include <unistd.h>
static volatile sig_atomic_t change;
static void request(int number) { (void)number; change = 1; }
int main(void) {
    sigset_t blocked, previous;
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGUSR1);
    if (sigprocmask(SIG_BLOCK, &blocked, &previous) < 0) return 2;
    struct sigaction action = {0};
    action.sa_handler = request;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGUSR1, &action, 0) < 0) return 2;
    while (!change) sigsuspend(&previous);
    if (sigprocmask(SIG_SETMASK, &previous, 0) < 0) return 2;
    execl("/usr/bin/sleep", "/usr/bin/sleep", "120", (char *)0);
    return 3;
}
