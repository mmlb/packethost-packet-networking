from textwrap import dedent
from ... import utils
import pytest


@pytest.fixture
def ubuntu_2004_individual_network(generic_debian_individual_network):
    def _builder(**kwargs):
        return generic_debian_individual_network("ubuntu", "20.04", **kwargs)

    return _builder


def test_ubuntu_2004_public_individual_task_etc_network_interfaces(
    ubuntu_2004_individual_network,
):
    """Validates /etc/network/interfaces for a public bond"""

    builder = ubuntu_2004_individual_network(public=True)
    tasks = builder.render()
    result = dedent(
        """\
        auto lo
        iface lo inet loopback

        auto enp0
        iface enp0 inet static
            address {ipv4pub.address}
            netmask {ipv4pub.netmask}
            gateway {ipv4pub.gateway}
            dns-nameservers {dns1} {dns2}

        iface enp0 inet6 static
            address {ipv6pub.address}
            netmask {ipv6pub.cidr}
            gateway {ipv6pub.gateway}

        auto enp0:0
        iface enp0:0 inet static
            address {ipv4priv.address}
            netmask {ipv4priv.netmask}
            post-up route add -net 10.0.0.0/8 gw {ipv4priv.gateway}
            post-down route del -net 10.0.0.0/8 gw {ipv4priv.gateway}
    """
    ).format(
        ipv4pub=builder.ipv4pub.first,
        ipv6pub=builder.ipv6pub.first,
        ipv4priv=builder.ipv4priv.first,
        dns1=builder.network.resolvers[0],
        dns2=builder.network.resolvers[1],
    )
    assert tasks["etc/network/interfaces"] == result


def test_ubuntu_2004_private_individual_task_etc_network_interfaces(
    ubuntu_2004_individual_network,
):
    """
    When no public ip is assigned, we should see the private ip details in the
    /etc/network/interfaces file.
    """
    builder = ubuntu_2004_individual_network(public=False)
    tasks = builder.render()
    result = dedent(
        """\
        auto lo
        iface lo inet loopback

        auto enp0
        iface enp0 inet static
            address {ipv4priv.address}
            netmask {ipv4priv.netmask}
            gateway {ipv4priv.gateway}
            dns-nameservers {dns1} {dns2}
    """
    ).format(
        ipv4priv=builder.ipv4priv.first,
        dns1=builder.network.resolvers[0],
        dns2=builder.network.resolvers[1],
    )
    assert tasks["etc/network/interfaces"] == result


def test_ubuntu_2004_public_individual_task_etc_network_interfaces_with_custom_private_ip_space(
    ubuntu_2004_individual_network,
):
    """Validates /etc/network/interfaces for a public bond"""
    subnets = {"private_subnets": ["192.168.5.0/24", "172.16.0.0/12"]}
    builder = ubuntu_2004_individual_network(public=True, metadata=subnets)
    tasks = builder.render()
    result = dedent(
        """\
        auto lo
        iface lo inet loopback

        auto enp0
        iface enp0 inet static
            address {ipv4pub.address}
            netmask {ipv4pub.netmask}
            gateway {ipv4pub.gateway}
            dns-nameservers {dns1} {dns2}

        iface enp0 inet6 static
            address {ipv6pub.address}
            netmask {ipv6pub.cidr}
            gateway {ipv6pub.gateway}

        auto enp0:0
        iface enp0:0 inet static
            address {ipv4priv.address}
            netmask {ipv4priv.netmask}
            post-up route add -net 192.168.5.0/24 gw {ipv4priv.gateway}
            post-down route del -net 192.168.5.0/24 gw {ipv4priv.gateway}
            post-up route add -net 172.16.0.0/12 gw {ipv4priv.gateway}
            post-down route del -net 172.16.0.0/12 gw {ipv4priv.gateway}
    """
    ).format(
        ipv4pub=builder.ipv4pub.first,
        ipv6pub=builder.ipv6pub.first,
        ipv4priv=builder.ipv4priv.first,
        dns1=builder.network.resolvers[0],
        dns2=builder.network.resolvers[1],
    )
    assert tasks["etc/network/interfaces"] == result


def test_ubuntu_2004_private_individual_task_etc_network_interfaces_with_custom_private_ip_space(
    ubuntu_2004_individual_network,
):
    """
    When no public ip is assigned, we should see the private ip details in the
    /etc/network/interfaces file.
    """
    subnets = {"private_subnets": ["192.168.5.0/24", "172.16.0.0/12"]}
    builder = ubuntu_2004_individual_network(public=False, metadata=subnets)
    tasks = builder.render()
    result = dedent(
        """\
        auto lo
        iface lo inet loopback

        auto enp0
        iface enp0 inet static
            address {ipv4priv.address}
            netmask {ipv4priv.netmask}
            gateway {ipv4priv.gateway}
            dns-nameservers {dns1} {dns2}
    """
    ).format(
        ipv4priv=builder.ipv4priv.first,
        dns1=builder.network.resolvers[0],
        dns2=builder.network.resolvers[1],
    )
    assert tasks["etc/network/interfaces"] == result


def test_ubuntu_2004_etc_systemd_resolved_configured(
    ubuntu_2004_individual_network, fake
):
    """
    Validates /etc/systemd/resolved.conf is configured correctly
    """
    builder = ubuntu_2004_individual_network()
    resolver1 = fake.ipv4()
    resolver2 = fake.ipv4()
    builder.network.resolvers = (resolver1, resolver2)
    tasks = builder.render()
    result = dedent(
        """\
        [Resolve]
        DNS={resolver1} {resolver2}
    """
    ).format(resolver1=resolver1, resolver2=resolver2)
    assert tasks["etc/systemd/resolved.conf"] == result
    assert "etc/resolv.conf" not in tasks


def test_ubuntu_2004_etc_hostname_configured(ubuntu_2004_individual_network):
    """
    Validates /etc/hostname is configured correctly
    """
    builder = ubuntu_2004_individual_network()
    tasks = builder.render()
    result = dedent(
        """\
        {hostname}
    """
    ).format(hostname=builder.metadata.hostname)
    assert tasks["etc/hostname"] == result


def test_ubuntu_2004_etc_hosts_configured(ubuntu_2004_individual_network):
    """
    Validates /etc/hosts is configured correctly
    """
    builder = ubuntu_2004_individual_network()
    tasks = builder.render()
    result = dedent(
        """\
        127.0.0.1	localhost	{hostname}

        # The following lines are desirable for IPv6 capable hosts
        ::1	localhost ip6-localhost ip6-loopback
        ff02::1	ip6-allnodes
        ff02::2	ip6-allrouters
    """
    ).format(hostname=builder.metadata.hostname)
    assert tasks["etc/hosts"] == result


def test_ubuntu_2004_persistent_interface_names(ubuntu_2004_individual_network):
    """
    When using certain operating systems, we want to bypass driver interface name,
    here we make sure the /etc/udev/rules.d/70-persistent-net.rules is generated.
    """
    builder = ubuntu_2004_individual_network()
    tasks = builder.render()
    result = dedent(
        """\
        {header}
        #
        # You can modify it, as long as you keep each rule on a single
        # line, and change only the value of the NAME= key.

        # PCI device (custom name provided by external tool to mimic Predictable Network Interface Names)
        SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ATTR{{address}}=="{iface0.mac}", ATTR{{dev_id}}=="0x0", ATTR{{type}}=="1", NAME="{iface0.name}"

        # PCI device (custom name provided by external tool to mimic Predictable Network Interface Names)
        SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ATTR{{address}}=="{iface1.mac}", ATTR{{dev_id}}=="0x0", ATTR{{type}}=="1", NAME="{iface1.name}"
    """
    ).format(
        header=utils.generated_header(),
        iface0=builder.network.interfaces[0],
        iface1=builder.network.interfaces[1],
    )
    assert tasks["etc/udev/rules.d/70-persistent-net.rules"] == result


def test_ubuntu_2004_public_individual_dhcp_task_etc_network_interfaces(
    ubuntu_2004_individual_network,
    make_interfaces_dhcp_metadata,
    expected_file_etc_network_interfaces_dhcp_2,
):
    """Validates /etc/network/interfaces for a public dhcp interfaces"""

    builder = ubuntu_2004_individual_network(
        public=True, post_gen_metadata=make_interfaces_dhcp_metadata
    )
    tasks = builder.render()

    result = expected_file_etc_network_interfaces_dhcp_2

    assert tasks["etc/network/interfaces"] == result


def test_ubuntu_2004_etc_resolvers_dhcp(
    ubuntu_2004_individual_network, make_interfaces_dhcp_metadata
):
    """
    Validates /etc/resolv.conf is skipped
    """
    builder = ubuntu_2004_individual_network(
        post_gen_metadata=make_interfaces_dhcp_metadata
    )
    tasks = builder.render()
    assert tasks["etc/resolv.conf"] is None
