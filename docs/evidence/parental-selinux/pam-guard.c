/* VM-only prototype. Fixed fictitious group/context, never install on a host.
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
 char gb[65536],pb[65536];gid_t *groups=NULL;char *context=NULL;
 int count=0,supervised=0,result=PAM_SESSION_ERR;
 if(pam_get_user(pamh,&user,NULL)!=PAM_SUCCESS || !user) goto done;
 /* Missing/unreadable group is a broken registry, never an empty allowlist. */
 if(getgrnam_r("lyra-parental-fixture",&group,gb,sizeof(gb),&gr)!=0 || !gr) goto done;
 if(getpwnam_r(user,&account,pb,sizeof(pb),&pw)!=0 || !pw) goto done;
 getgrouplist(user,pw->pw_gid,NULL,&count);
 if(count<1 || count>65536) goto done;
 groups=calloc((size_t)count,sizeof(*groups));if(!groups) goto done;
 if(getgrouplist(user,pw->pw_gid,groups,&count)<0) goto done;
 for(int i=0;i<count;i++)if(groups[i]==gr->gr_gid)supervised=1;
 if(!supervised){result=PAM_SUCCESS;goto done;}
 if(is_selinux_enabled()!=1 || security_getenforce()!=1) goto done;
 if(getexeccon(&context)!=0 || !context || strcmp(context,expected)) goto done;
 security_class_t cls=string_to_security_class("process");
 access_vector_t permission=string_to_av_perm(cls,"transition");
 struct av_decision decision;
 if(!cls || !permission || security_compute_av_flags(context,context,cls,permission,&decision)<0) goto done;
 if(decision.flags & SELINUX_AVD_FLAGS_PERMISSIVE) goto done;
 result=PAM_SUCCESS;
 done:
 free(groups);if(context)freecon(context);
 if(result!=PAM_SUCCESS)pam_syslog(pamh,LOG_ERR,"Disposable supervised admission check rejected session");
 return result;
}
PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh,int flags,int argc,const char **argv) {
 (void)pamh;(void)flags;(void)argc;(void)argv;return PAM_SUCCESS;
}
