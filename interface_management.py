from terminal import (clear,
                      run_command,
                      run_command_print_output,
                      popen_command,
                      popen_command_new_terminal)

from color import red, green


def change_interface():
    """
    selects/changes the interface that`s going to be used in wireless attacks

    :return:
    """
    print("Available Networks Interfaces : ")
    interfaces = run_command("iw dev | grep Interface | awk '{print $2}'")
    for interface in interfaces.split('\n'):
        print(f'\n{green(interface)}')
    while 1:
        selection = input(f"Enter the name of the interface {green('(leave blank to exit)')} : ")
        if selection not in interfaces:
            print(f'Selected interface ({selection}) {red("does not exist")}')
        else:
            return selection
            break


def is_interface_monitor(interface):
    interface_settings = run_command(f'iwconfig {interface}')
    if 'monitor' in interface_settings.lower():
        return True
    else:
        return False


def switch_interface_to_monitor_mode(interface):
    print('Setting ' + interface + ' to monitor mode ')
    run_command(f'ifconfig {interface} down')
    run_command(f'iwconfig {interface} mode monitor')
    run_command(f'ifconfig {interface} up')


def switch_interface_to_managed_mode(interface):
    print('Setting ' + interface + ' to managed mode ')
    run_command(f'ifconfig {interface} down')
    run_command(f'iwconfig {interface} mode managed')
    run_command(f'ifconfig {interface} up')


def switch_interface_channel(interface, target_channel):
    run_command_print_output(f'iwconfig {interface} channel {target_channel}')
    print(f'{green(interface)} set to channel {target_channel}')
    return
