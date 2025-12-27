/* gcc -o gen_filter gen_filter.c -lseccomp */
#include <seccomp.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <sys/ioctl.h>

int main(void) {
    // Initialize filter to ALLOW all by default
    scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_ALLOW);

    // Block the TIOCSTI ioctl (Text Input Injection)
    // We return EPERM (Operation not permitted) if attempted
    seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(ioctl), 1,
                     SCMP_A1(SCMP_CMP_EQ, TIOCSTI));

    // Export the filter to a file descriptor (stdout)
    seccomp_export_bpf(ctx, STDOUT_FILENO);
    seccomp_release(ctx);
    return 0;
}
