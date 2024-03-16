# citrus

An Automated Evil Twin Framework designed to impersonate legitimate wireless networks with `dnsmasq` and `hostapd`. Citrus sets up a foundation for executing Man-in-the-Middle (MITM) attacks. It also has an option to deploy a captive portal using `apache2`, complete with a fake credentials page for phishing attacks. 

In the future, I plan on updating the captive portal HTML template. Currently, a temporary solution is in place. Until then, you can transfer your own phishing template to `/var/www/html/{your_folder_name}` (replace {your_folder_name} with your actual folder name) and modify the line `DocumentRoot /var/www/html/temp` in `000-default.conf` to `DocumentRoot /var/www/html/{your_folder_name}` for customization
### [Installation](https://github.com/emreutkan/citrus/releases/tag/v1.0.0)

![citrus](https://github.com/emreutkan/citrus/assets/127414322/d3dfd626-c568-46f3-a77f-4da0433c1f86)
