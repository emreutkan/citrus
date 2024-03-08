
import os
import signal
import subprocess
import time

from color import (red,
                   green)

terminals = ['x-terminal-emulator', 'gnome-terminal', 'konsole', 'xfce4-terminal']

def clear():
    """
    runs clear command in shell

    clear command is used to clear the terminal screen
    """
    subprocess.run('clear')


def run_command(command):
    """
     This command will execute in the main terminal and display both its input and output.
     It is intended for calling commands that do not require termination

    :param command:
    :return: returns the stdout or stderr
    """
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        return result.stdout
    else:
        return result.stderr

def run_command_print_output(command):
    """
     This command will execute in the main terminal and display both its input and output.
     It is intended for calling commands that do not require termination

    :param command:
    :return: returns the stdout or stderr
    """
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    print(f"Command: {command}")
    if result.returncode == 0:
        print(f"{green('Output')}   :   " + result.stdout)
        print("-" * 30)
        return result.stdout
    else:
        print(f"{red('Error')}      :   " + result.stderr)
        print("-" * 30)
        return result.stderr

def popen_command(command,killtime=0):
    """
    Similar to run_command(), but it returns the process, so we can terminate it if necessary. This can be used for a
    process that needs to be stopped after some time, like airodump-ng.

    :return : stdout, stderr if killtime exist
    """
    print(f'running {command} for {killtime} seconds')
    process = subprocess.Popen(command, shell=True,preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if killtime:
        time.sleep(killtime)
        os.killpg(process.pid, signal.SIGTERM)
        process.wait()
        output, error = process.communicate()
        return output, error


def popen_command_new_terminal(command):
    """
    This function is used for commands that require simultaneous execution (designed for the evil twin attack). With
    this update, child terminals are not bound to the parent terminal, allowing us to see the stderr and stdout. If
    we were to use the old logic of creating child terminals, an error would cause the child terminal to close
    immediately, causing us to lose any output that could be useful for troubleshooting.

    :return : Returns the PID of the subprocess if successful, otherwise returns None.

    """
    for terminal in terminals:
        try:
            terminal_command = ""
            if terminal == 'gnome-terminal':
                terminal_command = f"{terminal} -e /bin/sh -c '{command}; exec bash'"
            elif terminal == 'konsole':
                terminal_command = f"{terminal} -e /bin/sh -c '{command}; exec bash'"
            elif terminal == 'xfce4-terminal':
                terminal_command = f"{terminal} -e 'bash -c \"{command}; exec bash\"'"
            else:
                terminal_command = f"{terminal} -e 'bash -c \"{command}; exec bash\"'"
            print(f"Executing command: {terminal_command}\n")

            # Start the subprocess and get its PID
            process = subprocess.Popen(terminal_command, shell=True, preexec_fn=os.setsid)
            return process

        except Exception as e:
            print(f"Failed to execute command in {terminal}: {e} \n")
