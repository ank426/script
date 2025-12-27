Normally, we use --new-session in bwrap.

       --new-session
           Create a new terminal session for the sandbox (calls setsid()). This disconnects the sandbox from the controlling terminal which means the sandbox
           can't for instance inject input into the terminal.

           Note: In a general sandbox, if you don't use --new-session, it is recommended to use seccomp to disallow the TIOCSTI ioctl, otherwise the
           application can feed keyboard input to the terminal which can e.g. lead to out-of-sandbox command execution (see CVE-2017-5226).

But we can't cuz chafa needs to know the terminal so that it can convert rows/columns to pixels (font size)
So, I'm doing the second approach as per man.
No idea what it does (it's AI-generated)


gcc -o gen_filter gen_filter.c -lseccomp
./gen_filter > bwrap-tiocsti.bpf
