import subprocess
import logging
import sys

logger = logging.getLogger("hsts.scheduler_utils")

def register_square_off_task():
    """
    Registers a Windows Task Scheduler task to trigger at 3:15 PM (15:15) daily.
    Executes 'py main.py square-off-intraday'.
    """
    task_name = "HSTS_Intraday_SquareOff"
    # Get absolute path of main.py
    import os
    main_path = os.path.abspath("main.py")
    cwd = os.path.dirname(main_path)
    
    # Command to execute
    cmd = f'schtasks /create /tn "{task_name}" /tr "py {main_path} square-off-intraday" /sc daily /st 15:15 /f'
    
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            logger.info("Successfully registered Windows Task Scheduler task for 3:15 PM Square-Off.")
            print("[SCHEDULER] Registered Windows Task Scheduler task for 3:15 PM Square-Off.")
            return True
        else:
            logger.error(f"Failed to register Windows Task Scheduler task: {res.stderr}")
            print(f"[SCHEDULER] Failed to register Task: {res.stderr}")
            return False
    except Exception as e:
        logger.error(f"Exception registering Task: {e}")
        print(f"[SCHEDULER] Exception registering Task: {e}")
        return False

def deregister_square_off_task():
    """
    Removes the Windows Task Scheduler task HSTS_Intraday_SquareOff.
    """
    task_name = "HSTS_Intraday_SquareOff"
    cmd = f'schtasks /delete /tn "{task_name}" /f'
    
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            logger.info("Successfully deleted Windows Task Scheduler task.")
            print("[SCHEDULER] Deleted Windows Task Scheduler task.")
            return True
        else:
            # Task might not exist, which is fine
            logger.info(f"Task deletion returned: {res.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"Exception deleting Task: {e}")
        return False
