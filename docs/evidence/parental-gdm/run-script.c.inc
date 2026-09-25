/* -*- Mode: C; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 8 -*-
 *
 * Copyright (C) 2006 Ray Strode <rstrode@redhat.com>
 * Copyright (C) 2007 William Jon McCann <mccann@jhu.edu>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 */

/* Exact patched run_script extracted for fault injection; see source-provenance.json. */
static gboolean
run_script (GdmSessionWorker *worker,
            const char       *dir)
{
        /* scripts are for non-program sessions only */
        if (worker->is_program_session) {
                return TRUE;
        }

        gboolean result;
#ifdef HAVE_SELINUX
        char *session_exec_context = NULL;
        gboolean restore_exec_context = FALSE;

        /* PAM selects the user's context for the session executable. Root
         * hooks must not consume that context; keep it for the session fork.
         * Refuse to start a session if saving or restoring it fails. */
        if (is_selinux_enabled () > 0) {
                if (getexeccon (&session_exec_context) < 0) {
                        g_warning ("Unable to save SELinux session exec context: %m");
                        return FALSE;
                }
                if (session_exec_context != NULL) {
                        if (setexeccon (NULL) < 0) {
                                g_warning ("Unable to clear SELinux exec context for root hook: %m");
                                freecon (session_exec_context);
                                return FALSE;
                        }
                        restore_exec_context = TRUE;
                }
        }
#endif

        result = gdm_run_script (dir,
                                 worker->username,
                                 worker->x11_display_name,
                                 worker->display_is_local? NULL : worker->hostname,
                                 worker->x11_authority_file);
#ifdef HAVE_SELINUX
        if (restore_exec_context && setexeccon (session_exec_context) < 0) {
                g_warning ("Unable to restore SELinux session exec context: %m");
                result = FALSE;
        }
        freecon (session_exec_context);
#endif
        return result;
}
