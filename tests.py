
from terminal import (clear,
                      run_command,
                      run_command_print_output,
                      popen_command,
                      popen_command_new_terminal)
from interface_management import (
                                  change_interface,
                                  is_interface_monitor,
                                  switch_interface_to_monitor_mode,
                                  switch_interface_to_managed_mode)

from color import (red,
                   green)
import evil_twin
import captive_portal
if __name__ == "__main__":
    # evil_twin.evil_twin_deauth('wlan0','eth0','SUPERONLINE_Wi-Fi_1248')
    captive_portal.evil_twin_deauth('wlan0','eth0','SUPERONLINE_Wi-Fi_1248')

