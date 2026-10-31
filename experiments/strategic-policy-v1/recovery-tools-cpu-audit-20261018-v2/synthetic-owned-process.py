import subprocess, sys, time
subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'], start_new_session=True)
time.sleep(2.2)
