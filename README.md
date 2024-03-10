# citrus

## TODO
- Develop custom captive portal landing pages.
  - fake router firmware update,
- Save user inputs (passwords) in the captive portal to a text file, and while saving:
  - Either check the passwords against a capture file (if the user has one), then immediately end the attack if a password matches. If not a match, redirect to an HTML page that displays "Wrong Password enter password again".
  - Or simply close immediately if no capture file is available.
