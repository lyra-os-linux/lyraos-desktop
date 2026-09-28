/* Experimental PAM-session admission only; never install in a real PAM stack.
 * Root-owned PAM arguments bind account NAME:UID:GID:PRIVATE_GROUP explicitly.
 * Classification uses any matching component; authorization requires all of
 * them to match. Missing group records cannot turn a bound account ordinary. */
#define _GNU_SOURCE
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <selinux/selinux.h>
#include <errno.h>
#include <grp.h>
#include <pwd.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>

#define MAX_ACCOUNTS 32
struct binding { char user[64], group[64]; uid_t uid; gid_t gid; };
static const char expected[] = "lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0";

static int name_ok(const char *s) {
    size_t n = strlen(s);
    if (!n || n >= 64 || !((s[0] >= 'a' && s[0] <= 'z') || s[0] == '_')) return 0;
    for (size_t i = 1; i < n; i++)
        if (!((s[i] >= 'a' && s[i] <= 'z') || (s[i] >= '0' && s[i] <= '9') || s[i] == '_' || s[i] == '-')) return 0;
    return 1;
}
static int id_ok(const char *s, unsigned long *value) {
    if (!*s || *s == '0') return 0;
    for (const char *p = s; *p; p++) if (*p < '0' || *p > '9') return 0;
    errno = 0;
    char *end;
    *value = strtoul(s, &end, 10);
    return !errno && !*end && *value < UINT32_MAX;
}
static int parse(int argc, const char **argv, struct binding *bindings) {
    if (argc < 1 || argc > MAX_ACCOUNTS) return 0;
    for (int i = 0; i < argc; i++) {
        if (strncmp(argv[i], "account=", 8) || strnlen(argv[i], 256) >= 256) return 0;
        char buffer[256]; strcpy(buffer, argv[i] + 8);
        char *rest = buffer, *parts[4];
        for (int j = 0; j < 4; j++) {
            parts[j] = strsep(&rest, ":");
            if (!parts[j] || !*parts[j]) return 0;
        }
        unsigned long uid, gid;
        if (rest || !name_ok(parts[0]) || !name_ok(parts[3]) || !id_ok(parts[1], &uid) || !id_ok(parts[2], &gid)) return 0;
        strcpy(bindings[i].user, parts[0]); strcpy(bindings[i].group, parts[3]);
        bindings[i].uid = (uid_t)uid; bindings[i].gid = (gid_t)gid;
        for (int j = 0; j < i; j++)
            if (!strcmp(bindings[i].user, bindings[j].user) || !strcmp(bindings[i].group, bindings[j].group) ||
                bindings[i].uid == bindings[j].uid || bindings[i].gid == bindings[j].gid) return 0;
    }
    return 1;
}
PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)flags;
    struct binding bindings[MAX_ACCOUNTS];
    if (!parse(argc, argv, bindings)) {
        pam_syslog(pamh, LOG_ERR, "Invalid experimental supervised account bindings");
        return PAM_SERVICE_ERR;
    }
    const char *user = NULL;
    struct passwd account, *pw = NULL;
    struct group group, *gr = NULL;
    char pb[65536], gb[65536], *context = NULL;
    int result = PAM_SESSION_ERR, matches = 0;
    const struct binding *selected = NULL;
    if (pam_get_user(pamh, &user, NULL) != PAM_SUCCESS || !user) goto done;
    if (getpwnam_r(user, &account, pb, sizeof(pb), &pw) != 0 || !pw) goto done;
    for (int i = 0; i < argc; i++) {
        if (!strcmp(user, bindings[i].user) || !strcmp(pw->pw_name, bindings[i].user) || pw->pw_uid == bindings[i].uid || pw->pw_gid == bindings[i].gid) {
            matches++; selected = &bindings[i];
        }
    }
    if (!matches) { result = PAM_SUCCESS; goto done; }
    if (matches != 1 || strcmp(user, selected->user) || strcmp(pw->pw_name, selected->user) ||
        pw->pw_uid != selected->uid || pw->pw_gid != selected->gid) goto done;
    if (getgrgid_r(pw->pw_gid, &group, gb, sizeof(gb), &gr) != 0 || !gr || strcmp(gr->gr_name, selected->group)) goto done;
    if (is_selinux_enabled() != 1 || security_getenforce() != 1) goto done;
    if (getexeccon(&context) != 0 || !context || strcmp(context, expected)) goto done;
    security_class_t cls = string_to_security_class("process");
    access_vector_t permission = string_to_av_perm(cls, "transition");
    struct av_decision decision;
    if (!cls || !permission || security_compute_av_flags(context, context, cls, permission, &decision) < 0 ||
        (decision.flags & SELINUX_AVD_FLAGS_PERMISSIVE)) goto done;
    result = PAM_SUCCESS;
done:
    if (context) freecon(context);
    if (result != PAM_SUCCESS) pam_syslog(pamh, LOG_ERR, "Experimental supervised admission rejected session");
    return result;
}
PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv; return PAM_SUCCESS;
}
