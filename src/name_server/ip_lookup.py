from ipaddress import IPv4Network
from typing import List, Set, Union
import re


def clean_ip(ip: str) -> str:
    http_pattern = r"https?://"
    port_pattern = r":\d+"
    return re.sub(port_pattern, "", re.sub(http_pattern, "", ip))


def find_closest_ip(self_ip: str, ips: Union[List[str], Set[str]]) -> str:
    """Selects the closest IP from a list of IPs.

    Args:
        self_ip: The ip to make the lookup for
        ips: An iterable of ips to select the closest one to self_ip

    Returns:
        An IP address which has the largest matching sub network of self_ip
    """
    clean_self_ip = clean_ip(self_ip)
    clean_ips = list(map(clean_ip, ips))

    if clean_self_ip in clean_ips:
        # If the same IP has a server. Return that IP
        return self_ip

    # Start with the largest posible subnet mask
    mask = 24
    while mask:
        self_net = IPv4Network(f"{clean_self_ip}/{mask}", strict=False)

        # Check if any IP has the same subnet as self_ip
        for i, other_ip in enumerate(clean_ips):
            other_net = IPv4Network(f"{other_ip}/{mask}", strict=False)
            if self_net == other_net:
                return ips[i]

        mask -= 1


if __name__ == "__main__":

    ips = ["192.168.2.124", "http://127.0.0.1:3000", "http://192.168.2.168:5000"]
    self_ip = "192.168.1.0:3030"
    print(find_closest_ip(self_ip, ips))
