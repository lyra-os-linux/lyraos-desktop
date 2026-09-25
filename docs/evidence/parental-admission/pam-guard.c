/* VM-only prototype. Fixed fictitious private GID/context, never install on a host.
 * Required AFTER pam_selinux.so open. This checks admission, not all-session
 * coverage or runtime changes to a previously opened session. */
#define _GNU_SOURCE
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <selinux/selinux.h>
#include <grp.h>
#include <pwd.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
static const char *expected="lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0";
PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh,int flags,int argc,const char **argv) {
 (void)flags;(void)argc;(void)argv;
 const char *user=NULL;
 struct group group,*gr=NULL;struct passwd account,*pw=NULL;
 char gb[65536],pb[65536];char *context=NULL;
 int result=PAM_SESSION_ERR;
 if(pam_get_user(pamh,&user,NULL)!=PAM_SUCCESS || !user) goto done;
 /* Prototype only: 1004 is parentaltest's existing PRIVATE primary GID.
  * Do not create a shared group or infer membership from a missing catalog.
  * Production needs an allocation/migration contract, not this fixture ID. */
 if(getpwnam_r(user,&account,pb,sizeof(pb),&pw)!=0 || !pw) goto done;
 if(pw->pw_gid!=1004){result=PAM_SUCCESS;goto done;}
 /* Identity remains supervised even if its group lookup is unavailable. */
 if(getgrgid_r(pw->pw_gid,&group,gb,sizeof(gb),&gr)!=0 || !gr ||
    strcmp(gr->gr_name,"parentaltest")) goto done;
 if(is_selinux_enabled()!=1 || security_getenforce()!=1) goto done;
 if(getexeccon(&context)!=0 || !context || strcmp(context,expected)) goto done;
 security_class_t cls=string_to_security_class("process");
 access_vector_t permission=string_to_av_perm(cls,"transition");
 struct av_decision decision;
 if(!cls || !permission || security_compute_av_flags(context,context,cls,permission,&decision)<0) goto done;
 if(decision.flags & SELINUX_AVD_FLAGS_PERMISSIVE) goto done;
 result=PAM_SUCCESS;
 done:
 if(context)freecon(context);
 if(result!=PAM_SUCCESS)pam_syslog(pamh,LOG_ERR,"Disposable supervised admission check rejected session");
 return result;
}
PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh,int flags,int argc,const char **argv) {
 (void)pamh;(void)flags;(void)argc;(void)argv;return PAM_SUCCESS;
}
