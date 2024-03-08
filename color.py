def red(string):
    """
    inputs a string and returns it with the color red

    use when in need for errors during print commands

    param string
    """
    return f'\033[91m{string}\033[0m'


def green(string):
    """
    inputs a string and returns it with the color green

    use when in need for better visibility during print commands

    param string
    """
    return f'\033[92m{string}\033[0m'
