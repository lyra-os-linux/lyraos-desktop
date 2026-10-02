/* Fixture-only cron ordinary account guard. Historical session guard unchanged.
 * Account management precedes pam_selinux open: positive proof here does not
 * assert a pending MAC label. The historical session hook checks that label; cron only installs this account hook.
 * No supervised account admission in this account-stage experimental route. */
#include "withdrawal-pam-guard.c"
PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)flags; (void)argv;
    if (argc != 0) return PAM_SERVICE_ERR;
    int result = PAM_PERM_DENIED, gate_fd = -1;
    const char *user = NULL;
    struct passwd account, *pw = NULL;
    struct group group, *gr = NULL;
    char pb[65536], gb[65536], file[32];
    struct identity rows[MAX_RECORDS];
    size_t count = 0;
    if (pam_get_user(pamh, &user, NULL) != PAM_SUCCESS || !user) goto done;
    if (getpwnam_r(user, &account, pb, sizeof(pb), &pw) != 0 || !pw) goto done;
    gate_fd = classification_gate(pw->pw_uid);
    if (gate_fd < 0) goto done;
    snprintf(file, sizeof(file), "%u", (unsigned)pw->pw_uid);
    if (!load_identity_file("lyra-ordinary-attestation-test", file, rows, &count) ||
        count != 1 || !rows[0].ordinary || strcmp(user, rows[0].user) ||
        strcmp(pw->pw_name, rows[0].user) || pw->pw_uid != rows[0].uid ||
        pw->pw_gid != rows[0].gid) goto done;
    if (getgrgid_r(pw->pw_gid, &group, gb, sizeof(gb), &gr) != 0 || !gr ||
        strcmp(gr->gr_name, rows[0].group)) goto done;
    if (is_selinux_enabled() != 1 || security_getenforce() != 1) goto done;
    result = PAM_SUCCESS;
done:
    if (gate_fd >= 0) close(gate_fd);
    if (result != PAM_SUCCESS) pam_syslog(pamh, LOG_ERR, "Experimental ordinary cron admission rejected account");
    return result;
}
