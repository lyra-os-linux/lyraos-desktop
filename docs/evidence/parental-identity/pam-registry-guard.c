/* Experimental PAM admission against a root-owned lifecycle registry.
 * Never install in a real PAM stack. */
#define _GNU_SOURCE
#include <security/pam_ext.h>
#include <security/pam_modules.h>
#include <selinux/selinux.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <pwd.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <syslog.h>
#include <unistd.h>

#define MAX_ACCOUNTS 32
#define MAX_RECORDS 64
#define MAX_REGISTRY 8192
#define STATE_DIR "/var/lib/lyra-parental-test"
#define STATE_FILE "identity-registry"

struct identity {
    char user[64], group[64], generation[33];
    uid_t uid;
    gid_t gid;
    int active, tombstone;
};
static const char expected[] = "lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0";
static const char lock_data_key[] = "lyra_parental_registry_session_lock";

struct session_lock { int fd; };

static void session_lock_cleanup(pam_handle_t *pamh, void *data, int error_status) {
    (void)pamh; (void)error_status;
    struct session_lock *lock = data;
    if (lock) {
        if (lock->fd >= 0) close(lock->fd);
        free(lock);
    }
}

static int acquire_session_lock(pam_handle_t *pamh, int *fd_out) {
    struct stat st;
    const void *existing = NULL;
    if (pam_get_data(pamh, lock_data_key, &existing) == PAM_SUCCESS && existing) return 0;
    int dfd = open("/var/lib/lyra-parental-test", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (dfd < 0 || fstat(dfd, &st) || !S_ISDIR(st.st_mode) || st.st_uid != 0 || (st.st_mode & 077)) {
        if (dfd >= 0) close(dfd);
        return 0;
    }
    int fd = openat(dfd, ".transaction.lock", O_RDONLY | O_CREAT | O_CLOEXEC | O_NOFOLLOW, 0600);
    close(dfd);
    if (fd < 0 || fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid != 0 ||
        (st.st_mode & 077) || st.st_nlink != 1 || flock(fd, LOCK_SH) < 0) {
        if (fd >= 0) close(fd);
        return 0;
    }
    struct session_lock *lock = malloc(sizeof(*lock));
    if (!lock) { close(fd); return 0; }
    lock->fd = fd;
    if (pam_set_data(pamh, lock_data_key, lock, session_lock_cleanup) != PAM_SUCCESS) {
        session_lock_cleanup(pamh, lock, 0);
        return 0;
    }
    *fd_out = fd;
    return 1;
}

static void release_session_lock(pam_handle_t *pamh) {
    const void *data = NULL;
    if (pam_get_data(pamh, lock_data_key, &data) == PAM_SUCCESS && data) {
        struct session_lock *lock = (struct session_lock *)data;
        if (lock->fd >= 0) {
            close(lock->fd);
            lock->fd = -1;
        }
    }
}

static int name_ok(const char *s) {
    size_t n = strlen(s);
    if (!n || n >= 64 || !((s[0] >= 'a' && s[0] <= 'z') || s[0] == '_')) return 0;
    for (size_t i = 1; i < n; i++)
        if (!((s[i] >= 'a' && s[i] <= 'z') || (s[i] >= '0' && s[i] <= '9') || s[i] == '_' || s[i] == '-')) return 0;
    return 1;
}

static int decimal_id(const char *s, uint32_t *value) {
    if (!*s || *s == '0') return 0;
    for (const char *p = s; *p; p++) if (*p < '0' || *p > '9') return 0;
    errno = 0;
    char *end;
    unsigned long n = strtoul(s, &end, 10);
    if (errno || *end || n >= UINT32_MAX) return 0;
    *value = (uint32_t)n;
    return 1;
}

static int generation_ok(const char *s) {
    if (strlen(s) != 32) return 0;
    for (size_t i = 0; i < 32; i++)
        if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f'))) return 0;
    return 1;
}

static int parse_identity(char *line, struct identity *out) {
    char *rest = line, *part[6];
    for (size_t i = 0; i < 6; i++) {
        part[i] = strsep(&rest, "|");
        if (!part[i] || !*part[i]) return 0;
    }
    uint32_t uid, gid;
    if (rest || (strcmp(part[0], "active") && strcmp(part[0], "tombstone") &&
                 strcmp(part[0], "blocked") && strcmp(part[0], "provisioning") &&
                 strcmp(part[0], "transitioning") && strcmp(part[0], "recovering")) ||
        !name_ok(part[1]) || !decimal_id(part[2], &uid) || !decimal_id(part[3], &gid) ||
        !name_ok(part[4]) || !generation_ok(part[5])) return 0;
    strcpy(out->user, part[1]); strcpy(out->group, part[4]); strcpy(out->generation, part[5]);
    out->uid = (uid_t)uid; out->gid = (gid_t)gid;
    out->active = !strcmp(part[0], "active"); out->tombstone = !strcmp(part[0], "tombstone");
    return 1;
}

static int load_registry(struct identity *rows, size_t *count) {
    struct stat st;
    int dfd = -1, fd = -1, ok = 0;
    char data[MAX_REGISTRY + 1];
    ssize_t n;
    dfd = open("/var/lib", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (dfd < 0 || fstat(dfd, &st) || !S_ISDIR(st.st_mode) || st.st_uid != 0 || (st.st_mode & 022)) goto done;
    int statefd = openat(dfd, "lyra-parental-test", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (statefd < 0) goto done;
    if (fstat(statefd, &st) || !S_ISDIR(st.st_mode) || st.st_uid != 0 || (st.st_mode & 077)) { close(statefd); goto done; }
    fd = openat(statefd, STATE_FILE, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    close(statefd);
    if (fd < 0 || fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid != 0 ||
        (st.st_mode & 077) || st.st_nlink != 1 || st.st_size <= 0 || st.st_size > MAX_REGISTRY) goto done;
    n = read(fd, data, (size_t)st.st_size);
    if (n != st.st_size || memchr(data, '\0', (size_t)n)) goto done;
    data[n] = '\0';
    if (strncmp(data, "LYRA-ID-REGISTRY-V1\n", 20)) goto done;
    char *cursor = data + 20, *line;
    *count = 0;
    while ((line = strsep(&cursor, "\n")) != NULL) {
        if (!*line) continue;
        if (*count == MAX_RECORDS || !parse_identity(line, &rows[*count])) goto done;
        for (size_t i = 0; i < *count; i++)
            if (!strcmp(rows[i].generation, rows[*count].generation)) goto done;
        (*count)++;
    }
    if (!*count) goto done;
    ok = 1;
done:
    if (fd >= 0) close(fd);
    if (dfd >= 0) close(dfd);
    return ok;
}

static int parse_arguments(int argc, const char **argv, struct identity *bindings) {
    if (argc < 1 || argc > MAX_ACCOUNTS) return 0;
    for (int i = 0; i < argc; i++) {
        if (strncmp(argv[i], "account=", 8) || strnlen(argv[i], 256) >= 256) return 0;
        char buf[256]; strcpy(buf, argv[i] + 8);
        if (!parse_identity(buf, &bindings[i])) return 0;
        /* PAM configuration may only describe a desired active generation. */
        if (!bindings[i].active || bindings[i].tombstone) return 0;
        for (int j = 0; j < i; j++)
            if (!strcmp(bindings[i].user, bindings[j].user) || bindings[i].uid == bindings[j].uid ||
                bindings[i].gid == bindings[j].gid) return 0;
    }
    return 1;
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)flags;
    struct identity bindings[MAX_ACCOUNTS], rows[MAX_RECORDS];
    size_t row_count = 0;
    if (!parse_arguments(argc, argv, bindings)) return PAM_SERVICE_ERR;
    const char *user = NULL;
    struct passwd account, *pw = NULL;
    struct group group, *gr = NULL;
    char pb[65536], gb[65536], *context = NULL;
    int result = PAM_SESSION_ERR, matches = 0, found = 0, lock_fd = -1;
    const struct identity *selected = NULL;
    if (pam_get_user(pamh, &user, NULL) != PAM_SUCCESS || !user) goto done;
    if (getpwnam_r(user, &account, pb, sizeof(pb), &pw) != 0 || !pw) goto done;
    for (int i = 0; i < argc; i++)
        if (!strcmp(user, bindings[i].user) || !strcmp(pw->pw_name, bindings[i].user) ||
            pw->pw_uid == bindings[i].uid || pw->pw_gid == bindings[i].gid) {
            matches++; selected = &bindings[i];
        }
    if (!matches) { result = PAM_SUCCESS; goto done; }
    if (matches != 1 || strcmp(user, selected->user) || strcmp(pw->pw_name, selected->user) ||
        pw->pw_uid != selected->uid || pw->pw_gid != selected->gid) goto done;
    if (getgrgid_r(pw->pw_gid, &group, gb, sizeof(gb), &gr) != 0 || !gr || strcmp(gr->gr_name, selected->group)) goto done;
    if (!acquire_session_lock(pamh, &lock_fd)) goto done;
    if (!load_registry(rows, &row_count)) goto done;
    for (size_t i = 0; i < row_count; i++) {
        if (strcmp(rows[i].user, selected->user) || rows[i].uid != selected->uid || rows[i].gid != selected->gid ||
            strcmp(rows[i].group, selected->group) || strcmp(rows[i].generation, selected->generation)) continue;
        if (++found > 1 || !rows[i].active || rows[i].tombstone) goto done;
    }
    if (found != 1) goto done;
    if (is_selinux_enabled() != 1 || security_getenforce() != 1) goto done;
    security_class_t cls = string_to_security_class("process");
    access_vector_t permission = string_to_av_perm(cls, "transition");
    struct av_decision decision;
    if (getexeccon(&context) != 0 || !context || strcmp(context, expected) || !cls || !permission ||
        security_compute_av_flags(context, context, cls, permission, &decision) < 0 ||
        (decision.flags & SELINUX_AVD_FLAGS_PERMISSIVE)) goto done;
    result = PAM_SUCCESS;
done:
    if (result != PAM_SUCCESS && lock_fd >= 0) release_session_lock(pamh);
    if (context) freecon(context);
    if (result != PAM_SUCCESS) pam_syslog(pamh, LOG_ERR, "Experimental registry-backed admission rejected session");
    return result;
}

PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)flags; (void)argc; (void)argv;
    release_session_lock(pamh);
    return PAM_SUCCESS;
}
