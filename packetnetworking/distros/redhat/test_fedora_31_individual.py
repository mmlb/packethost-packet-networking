from textwrap import dedent
import os
import pytest


@pytest.fixture
def fedora_31_individual_network(generic_redhat_individual_network):
    def _builder(**kwargs):
        return generic_redhat_individual_network("fedora", "31", **kwargs)

    return _builder


def test_fedora_31_public_individual_task_etc_sysconfig_network(
    fedora_31_individual_network
):
    """Validates /etc/sysconfig/network for a public bond"""
    builder = fedora_31_individual_network(public=True)
    tasks = builder.render()
    result = dedent(
        """\
        NETWORKING=yes
        HOSTNAME={hostname}
        GATEWAY={gateway}
        GATEWAYDEV=enp0
        NOZEROCONF=yes
    """
    ).format(hostname=builder.metadata.hostname, gateway=builder.ipv4pub.first.gateway)
    assert tasks["etc/sysconfig/network"] == result


# pylama:ignore=E501


def test_fedora_31_public_individual_task_etc_sysconfig_network_scripts_ifcfg_enp0(
    fedora_31_individual_network
):
    """Validates /etc/sysconfig/network-scripts/ifcfg-enp0 for a public bond"""
    builder = fedora_31_individual_network(public=True)
    tasks = builder.render()
    result = dedent(
        """\
        DEVICE=enp0
        NAME=enp0
        IPADDR={ipv4pub.address}
        NETMASK={ipv4pub.netmask}
        GATEWAY={ipv4pub.gateway}
        BOOTPROTO=none
        ONBOOT=yes
        USERCTL=no

        IPV6INIT=yes
        IPV6ADDR={ipv6pub.address}/{ipv6pub.cidr}
        IPV6_DEFAULTGW={ipv6pub.gateway}
        DNS1={dns1}
        DNS2={dns2}
    """
    ).format(
        ipv4pub=builder.ipv4pub.first,
        ipv6pub=builder.ipv6pub.first,
        dns1=builder.network.resolvers[0],
        dns2=builder.network.resolvers[1],
    )
    assert tasks["etc/sysconfig/network-scripts/ifcfg-enp0"] == result


def test_fedora_31_private_individual_task_etc_sysconfig_network_scripts_ifcfg_enp0(
    fedora_31_individual_network
):
    """
    When no public ip is assigned, we should see the private ip details in the
    /etc/sysconfig/network-scripts/ifcfg-enp0 interface file.
    """
    builder = fedora_31_individual_network(public=False)
    tasks = builder.render()
    result = dedent(
        """\
        DEVICE=enp0
        NAME=enp0
        IPADDR={ipv4priv.address}
        NETMASK={ipv4priv.netmask}
        GATEWAY={ipv4priv.gateway}
        BOOTPROTO=none
        ONBOOT=yes
        USERCTL=no

        DNS1={dns1}
        DNS2={dns2}
    """
    ).format(
        ipv4priv=builder.ipv4priv.first,
        dns1=builder.network.resolvers[0],
        dns2=builder.network.resolvers[1],
    )
    assert tasks["etc/sysconfig/network-scripts/ifcfg-enp0"] == result


def test_fedora_31_private_alias_task_etc_sysconfig_network_scripts_ifcfg_enp0_0(
    fedora_31_individual_network
):
    """
    When a public ip is assigned, the private ip address should become an
    alias, this validates /etc/sysconfig/network-scripts/ifcfg-enp0:0 alias
    has been created for the private ip
    """
    builder = fedora_31_individual_network(public=True)
    tasks = builder.render()
    result = dedent(
        """\
        DEVICE=enp0:0
        NAME=enp0:0
        IPADDR={ipv4priv.address}
        NETMASK={ipv4priv.netmask}
        GATEWAY={ipv4priv.gateway}
        BOOTPROTO=none
        ONBOOT=yes
        USERCTL=no
        DNS1={dns1}
        DNS2={dns2}
    """
    ).format(
        ipv4priv=builder.ipv4priv.first,
        dns1=builder.network.resolvers[0],
        dns2=builder.network.resolvers[1],
    )
    assert tasks["etc/sysconfig/network-scripts/ifcfg-enp0:0"] == result


def test_fedora_31_private_alias_task_missing_for_private_only_enp(
    fedora_31_individual_network
):
    """
    When no public ip is assigned, we should not see an alias created
    therefore /etc/sysconfig/network-scripts/ifcfg-enp0:0 should not exist.
    """
    builder = fedora_31_individual_network(public=False)
    tasks = builder.render()
    assert "etc/sysconfig/network-scripts/ifcfg-enp0:0" not in tasks


def test_fedora_31_private_route_task_etc_sysconfig_network_scripts_route_enp0(
    fedora_31_individual_network
):
    """
    When using a public ip, the private ip is assigned as an alias, this
    validates the /etc/sysconfig/network-scripts/route-enp0 route is created
    for the private subnet.
    """
    builder = fedora_31_individual_network(public=True)
    tasks = builder.render()
    result = dedent(
        """\
        10.0.0.0/8 via {ipv4priv.gateway} dev enp0:0
    """
    ).format(ipv4priv=builder.ipv4priv.first)
    assert tasks["etc/sysconfig/network-scripts/route-enp0"] == result


# pylama:ignore=E501
def test_fedora_31_private_route_task_etc_sysconfig_network_scripts_route_enp0_with_custom_private_subnets(
    fedora_31_individual_network
):
    """
    When using a public ip, the private ip is assigned as an alias, this
    validates the /etc/sysconfig/network-scripts/route-enp0 route is created
    for the private subnet.
    """
    subnets = {"private_subnets": ["192.168.5.0/24", "172.16.0.0/12"]}
    builder = fedora_31_individual_network(public=True, metadata=subnets)
    tasks = builder.render()
    result = dedent(
        """\
        192.168.5.0/24 via {ipv4priv.gateway} dev enp0:0
        172.16.0.0/12 via {ipv4priv.gateway} dev enp0:0
    """
    ).format(ipv4priv=builder.ipv4priv.first)
    assert tasks["etc/sysconfig/network-scripts/route-enp0"] == result


def test_fedora_31_private_route_task_missing_for_private_only_enp(
    fedora_31_individual_network
):
    """
    When no public ip is assigned, we should not see a route file created
    therefore /etc/sysconfig/network-scripts/route-enp0 should not exist.
    """
    builder = fedora_31_individual_network(public=False)
    tasks = builder.render()
    assert "etc/sysconfig/network-scripts/route-enp0" not in tasks


def test_fedora_31_etc_resolvers_configured(fedora_31_individual_network, fake):
    """
    Validates /etc/resolv.conf is configured correctly
    """
    builder = fedora_31_individual_network()
    resolver1 = fake.ipv4()
    resolver2 = fake.ipv4()
    builder.network.resolvers = (resolver1, resolver2)
    tasks = builder.render()
    result = dedent(
        """\
        nameserver {resolver1}
        nameserver {resolver2}
    """
    ).format(resolver1=resolver1, resolver2=resolver2)
    assert tasks["etc/resolv.conf"] == result


def test_fedora_31_etc_hostname_configured(fedora_31_individual_network):
    """
    Validates /etc/hostname is configured correctly
    """
    builder = fedora_31_individual_network()
    tasks = builder.render()
    result = dedent(
        """\
        {hostname}
    """
    ).format(hostname=builder.metadata.hostname)
    assert tasks["etc/hostname"] == result


def test_fedora_31_etc_hosts_configured(fedora_31_individual_network):
    """
    Validates /etc/hosts is configured correctly
    """
    builder = fedora_31_individual_network()
    tasks = builder.render()
    result = dedent(
        """\
        127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
        ::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
    """
    )
    assert tasks["etc/hosts"] == result


def test_fedora_31_network_manager_is_disabled(fedora_31_individual_network):
    """
    When using certain operating systems, we want to disable Network Manager,
    here we make sure those distros remove the necessary files
    """
    builder = fedora_31_individual_network()
    tasks = builder.render()
    for service in (
        "dbus-org.freedesktop.NetworkManager",
        "dbus-org.freedesktop.nm-dispatcher",
        "multi-user.target.wants/NetworkManager",
    ):
        assert tasks[os.path.join("etc/systemd/system", service + ".service")] is None


def test_fedora_31_persistent_interface_names_does_not_exist(
    fedora_31_individual_network
):
    """
    When using certain operating systems, we want to bypass driver interface name,
    here we make sure the /etc/udev/rules.d/70-persistent-net.rules is generated.
    """
    builder = fedora_31_individual_network()
    tasks = builder.render()
    assert "etc/udev/rules.d/70-persistent-net.rules" not in tasks
