set pagination off
set confirm off
set print thread-events off
set print elements 80
set disable-randomization off
set follow-fork-mode parent
set detach-on-fork on
handle SIGABRT stop print nopass
handle SIGSEGV stop print nopass
run
echo \n=== DIAGNOSTIC STOP OR NORMAL EXIT: NOT A GAME RESULT ===\n
info program
info threads
thread apply all bt full
info sharedlibrary
info proc mappings
quit
