import os
import subprocess


def check_root():
    if os.geteuid() != 0:
        exit("Must be run as root.\n")


def message(msg: str):
    print("******************************\n%s\n******************************" % msg)


def run_cmd_with_check(cmd: str):
    code = os.system(cmd)
    if code:
        raise RuntimeError("Return code: %d for `%s`" % (code, cmd))


def run_cmd_with_output(cmd: list[str]):
    return subprocess.run(cmd, capture_output=True).stdout.decode().strip("\n")
