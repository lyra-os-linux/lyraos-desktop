/* Reserved VM: parent and child stay alive for two seconds after SIGTERM. */
#include <signal.h>
#include <unistd.h>
static volatile sig_atomic_t stop;
static void request(int number) { (void)number; stop = 1; }
int main(void) {
    sigset_t blocked, previous;
    sigemptyset(&blocked); sigaddset(&blocked, SIGTERM);
    if (sigprocmask(SIG_BLOCK, &blocked, &previous) < 0) return 2;
    struct sigaction action = {0}; action.sa_handler = request;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGTERM, &action, 0) < 0) return 2;
    if (fork() < 0) return 3;
    while (!stop) sigsuspend(&previous);
    if (sigprocmask(SIG_SETMASK, &previous, 0) < 0) return 2;
    sleep(2);
    return 0;
}
