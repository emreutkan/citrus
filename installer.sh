#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]
  then echo -e "${RED}run as root (sudo ./installer.sh)${NC}"
  exit
fi

if command -v pacman &> /dev/null; then
    PACKAGE_MANAGER_INSTALL="sudo pacman -S --noconfirm"
    PACKAGE_MANAGER_UPDATE="sudo pacman -Syu"
  echo -e "${GREEN} Arch Based Distro detected.${NC}"
elif command -v apt-get &> /dev/null; then
    PACKAGE_MANAGER_INSTALL="sudo apt-get install -y"
    echo -e "${GREEN} Debian Based Distro detected.${NC}"
else
    echo -e "${RED}Supported package manager not found. Install packages manually.${NC}"
    exit 1
fi

echo -e "${GREEN}Updating package manager${NC}"
$PACKAGE_MANAGER_UPDATE

if ! command -v aircrack-ng &> /dev/null
then
    echo -e "${GREEN}Installing aircrack-ng${NC}"
    $PACKAGE_MANAGER_INSTALL aircrack-ng
else
    echo -e "${GREEN}aircrack-ng already installed.${NC}"
fi

if ! command -v hostapd &> /dev/null
then
    echo -e "${GREEN}Installing hostapd${NC}"
    $PACKAGE_MANAGER_INSTALL hostapd
else
    echo -e "${GREEN}hostapd already installed.${NC}"
fi

if ! command -v dnsmasq &> /dev/null
then
    echo -e "${GREEN}Installing dnsmasq${NC}"
    $PACKAGE_MANAGER_INSTALL dnsmasq
else
    echo -e "${GREEN}dnsmasq already installed.${NC}"
fi

if ! command -v dhclient &> /dev/null
then
    echo -e "${GREEN}Installing dhclient${NC}"
    $PACKAGE_MANAGER_INSTALL dhclient
else
    echo -e "${GREEN}dhclient already installed.${NC}"
fi

if ! command -v apache2 &> /dev/null
then
    echo -e "${GREEN}Installing apache2${NC}"
    $PACKAGE_MANAGER_INSTALL apache2
else
    echo -e "${GREEN}apache2 already installed.${NC}"
fi

if ! command -v ifconfig &> /dev/null
then
    echo -e "${GREEN}Installing net-tools${NC}"
    $PACKAGE_MANAGER_INSTALL net-tools
else
    echo -e "${GREEN}ifconfig already installed.${NC}"
fi

if ! command -v python3 &> /dev/null
then
    echo -e "${GREEN}Installing python3${NC}"
    $PACKAGE_MANAGER_INSTALL python3
fi

if ! command -v pip3 &> /dev/null
then
    echo -e "${GREEN}Installing pip3${NC}"
    $PACKAGE_MANAGER_INSTALL python3-pip
fi

chmod +x main.py

# Create a citrus command
echo -e "${GREEN}Creating a citrus command...${NC}"
echo "#!/bin/bash
# Check if running as root
if [ \"\$EUID\" -ne 0 ]; then
  echo 'run as root (sudo citrus)'
  exit
fi
cd /path/to/your/project
source venv/bin/activate
python main.py" > citrus

# Make the citrus command executable and move it to the user's bin directory
chmod +x citrus
sudo mv citrus /usr/local/bin/citrus

echo -e "${GREEN}Installation complete. You can now run by typing 'sudo citrus' in the terminal.${NC}"