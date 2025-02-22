from textwrap import dedent
from ... import utils
import os
import pytest


@pytest.fixture
def rhel_8_bonded_network(generic_redhat_bonded_network):
    def _builder(**kwargs):
        return generic_redhat_bonded_network("redhatenterprise", "8", **kwargs)

    return _builder


def test_rhel_8_public_bonded_task_etc_sysconfig_network(rhel_8_bonded_network):
    """Validates /etc/sysconfig/network for a public bond"""
    builder = rhel_8_bonded_network(public=True)
    tasks = builder.render()
    result = dedent(
        """\
        NETWORKING=yes
        HOSTNAME={hostname}
        GATEWAY={gateway}
        GATEWAYDEV=bond0
        NOZEROCONF=yes
    """
    ).format(hostname=builder.metadata.hostname, gateway=builder.ipv4pub.first.gateway)
    assert tasks["etc/sysconfig/network"] == result


def test_rhel_8_private_bonded_task_etc_sysconfig_network(rhel_8_bonded_network):
    """Validates /etc/sysconfig/network for a private only bond"""
    builder = rhel_8_bonded_network(public=False)
    tasks = builder.render()
    result = dedent(
        """\
        NETWORKING=yes
        HOSTNAME={hostname}
        GATEWAY={gateway}
        GATEWAYDEV=bond0
        NOZEROCONF=yes
    """
    ).format(hostname=builder.metadata.hostname, gateway=builder.ipv4priv.first.gateway)
    assert tasks["etc/sysconfig/network"] == result


def test_rhel_8_bonded_task_etc_modprobe_d_bonding(rhel_8_bonded_network):
    """Validates /etc/modprobe.d/bonding.conf has correct bonding mode"""
    builder = rhel_8_bonded_network()
    tasks = builder.render()
    result = dedent(
        """\
        alias bond0 bonding
        options bond0 mode={mode} miimon=100 downdelay=200 updelay=200 xmit_hash_policy=layer3+4 lacp_rate=1
    """
    ).format(mode=builder.network.bonding.mode)
    assert tasks["etc/modprobe.d/bonding.conf"] == result


def test_rhel_8_public_bonded_task_etc_sysconfig_network_scripts_ifcfg_bond0(
    rhel_8_bonded_network,
):
    """Validates /etc/sysconfig/network-scripts/ifcfg-bond0 for a public bond"""
    builder = rhel_8_bonded_network(public=True)
    tasks = builder.render()
    result = dedent(
        """\
        DEVICE=bond0
        NAME=bond0
        IPADDR={ipv4pub.address}
        NETMASK={ipv4pub.netmask}
        GATEWAY={ipv4pub.gateway}
        BOOTPROTO=none
        ONBOOT=yes
        USERCTL=no
        TYPE=Bond
        BONDING_OPTS="mode={bonding_mode} miimon=100 downdelay=200 updelay=200"

        IPV6INIT=yes
        IPV6ADDR={ipv6pub.address}/{ipv6pub.cidr}
        IPV6_DEFAULTGW={ipv6pub.gateway}
        DNS1={dns1}
        DNS2={dns2}
    """
    ).format(
        ipv4pub=builder.ipv4pub.first,
        ipv6pub=builder.ipv6pub.first,
        bonding_mode=builder.network.bonding.mode,
        dns1=builder.network.resolvers[0],
        dns2=builder.network.resolvers[1],
    )
    assert tasks["etc/sysconfig/network-scripts/ifcfg-bond0"] == result


def test_rhel_8_private_bonded_task_etc_sysconfig_network_scripts_ifcfg_bond0(
    rhel_8_bonded_network,
):
    """
    When no public ip is assigned, we should see the private ip details in the
    /etc/sysconfig/network-scripts/ifcfg-bond0 interface file.
    """
    builder = rhel_8_bonded_network(public=False)
    tasks = builder.render()
    result = dedent(
        """\
        DEVICE=bond0
        NAME=bond0
        IPADDR={ipv4priv.address}
        NETMASK={ipv4priv.netmask}
        GATEWAY={ipv4priv.gateway}
        BOOTPROTO=none
        ONBOOT=yes
        USERCTL=no
        TYPE=Bond
        BONDING_OPTS="mode={bonding_mode} miimon=100 downdelay=200 updelay=200"

        DNS1={dns1}
        DNS2={dns2}
    """
    ).format(
        ipv4priv=builder.ipv4priv.first,
        bonding_mode=builder.network.bonding.mode,
        dns1=builder.network.resolvers[0],
        dns2=builder.network.resolvers[1],
    )
    assert tasks["etc/sysconfig/network-scripts/ifcfg-bond0"] == result


def test_rhel_8_private_alias_task_etc_sysconfig_network_scripts_ifcfg_bond0_0(
    rhel_8_bonded_network,
):
    """
    When a public ip is assigned, the private ip address should become an
    alias, this validates /etc/sysconfig/network-scripts/ifcfg-bond0:0 alias
    has been created for the private ip
    """
    builder = rhel_8_bonded_network(public=True)
    tasks = builder.render()
    result = dedent(
        """\
        DEVICE=bond0:0
        NAME=bond0:0
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
    assert tasks["etc/sysconfig/network-scripts/ifcfg-bond0:0"] == result


def test_rhel_8_private_alias_task_missing_for_private_only_bond(rhel_8_bonded_network):
    """
    When no public ip is assigned, we should not see an alias created
    therefore /etc/sysconfig/network-scripts/ifcfg-bond0:0 should not exist.
    """
    builder = rhel_8_bonded_network(public=False)
    tasks = builder.render()
    assert "etc/sysconfig/network-scripts/ifcfg-bond0:0" not in tasks


def test_rhel_8_private_route_task_etc_sysconfig_network_scripts_route_bond0(
    rhel_8_bonded_network,
):
    """
    When using a public ip, the private ip is assigned as an alias, this
    validates the /etc/sysconfig/network-scripts/route-bond0 route is created
    for the private subnet.
    """
    builder = rhel_8_bonded_network(public=True)
    tasks = builder.render()
    result = dedent(
        """\
        10.0.0.0/8 via {ipv4priv.gateway} dev bond0:0
    """
    ).format(ipv4priv=builder.ipv4priv.first)
    assert tasks["etc/sysconfig/network-scripts/route-bond0"] == result


def test_rhel_8_private_route_task_etc_sysconfig_network_scripts_route_bond0_with_custom_private_subnets(
    rhel_8_bonded_network,
):
    """
    When using a public ip, the private ip is assigned as an alias, this
    validates the /etc/sysconfig/network-scripts/route-bond0 route is created
    for the private subnet.
    """
    subnets = {"private_subnets": ["192.168.5.0/24", "172.16.0.0/12"]}
    builder = rhel_8_bonded_network(public=True, metadata=subnets)
    tasks = builder.render()
    result = dedent(
        """\
        192.168.5.0/24 via {ipv4priv.gateway} dev bond0:0
        172.16.0.0/12 via {ipv4priv.gateway} dev bond0:0
    """
    ).format(ipv4priv=builder.ipv4priv.first)
    assert tasks["etc/sysconfig/network-scripts/route-bond0"] == result


def test_rhel_8_private_route_task_missing_for_private_only_bond(rhel_8_bonded_network):
    """
    When no public ip is assigned, we should not see a route file created
    therefore /etc/sysconfig/network-scripts/route-bond0 should not exist.
    """
    builder = rhel_8_bonded_network(public=False)
    tasks = builder.render()
    assert "etc/sysconfig/network-scripts/route-bond0" not in tasks


def test_rhel_8_individual_interface_files_created(rhel_8_bonded_network):
    """
    For each interface, we should see the corresponding ifcfg file
    located at /etc/sysconfig/network-scripts/ifcfg-*
    """
    builder = rhel_8_bonded_network(public=True)
    tasks = builder.render()
    for interface in builder.network.interfaces:
        result = dedent(
            """\
            DEVICE={iface}
            ONBOOT=yes
            HWADDR={mac}
            MASTER=bond0
            SLAVE=yes
            BOOTPROTO=none
        """
        ).format(iface=interface.name, mac=interface.mac)
        assert tasks["etc/sysconfig/network-scripts/ifcfg-" + interface.name] == result


def test_rhel_8_etc_resolvers_configured(rhel_8_bonded_network, fake):
    """
    Validates /etc/resolv.conf is configured correctly
    """
    builder = rhel_8_bonded_network()
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


def test_rhel_8_etc_hostname_configured(rhel_8_bonded_network):
    """
    Validates /etc/hostname is configured correctly
    """
    builder = rhel_8_bonded_network()
    tasks = builder.render()
    result = dedent(
        """\
        {hostname}
    """
    ).format(hostname=builder.metadata.hostname)
    assert tasks["etc/hostname"] == result


def test_rhel_8_etc_hosts_configured(rhel_8_bonded_network):
    """
    Validates /etc/hosts is configured correctly
    """
    builder = rhel_8_bonded_network()
    tasks = builder.render()
    result = dedent(
        """\
        127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
        ::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
    """
    )
    assert tasks["etc/hosts"] == result


def test_rhel_8_sbin_ifup_pre_local(rhel_8_bonded_network):
    """
    Validates /sbin/ifup-pre-local is created correctly
    """
    builder = rhel_8_bonded_network()
    tasks = builder.render()
    result = dedent(
        """\
        #!/bin/bash

        set -o errexit -o nounset -o pipefail -o xtrace

        iface=${{1#*-}}
        case "$iface" in
        bond0 | {interface0.name}) ip link set "$iface" address {interface0.mac} ;;
                {interface1.name}) ip link set "$iface" address {interface1.mac} && sleep 4 ;;
        *) echo "ignoring unknown interface $iface" && exit 0 ;;
        esac
    """
    ).format(
        interface0=builder.network.interfaces[0],
        interface1=builder.network.interfaces[1],
    )
    assert tasks["sbin/ifup-pre-local"]["content"] == result
    assert tasks["sbin/ifup-pre-local"]["mode"] == 0o755


def test_rhel_8_network_manager_is_disabled(rhel_8_bonded_network):
    """
    When using certain operating systems, we want to disable Network Manager,
    here we make sure those distros remove the necessary files
    """
    builder = rhel_8_bonded_network()
    tasks = builder.render()
    for service in (
        "dbus-org.freedesktop.NetworkManager",
        "dbus-org.freedesktop.nm-dispatcher",
        "multi-user.target.wants/NetworkManager",
    ):
        assert os.path.join("etc/systemd/system", service + ".service") not in tasks


def test_rhel_8_persistent_interface_names(rhel_8_bonded_network):
    """
    When using certain operating systems, we want to bypass driver interface name,
    here we make sure the /etc/udev/rules.d/70-persistent-net.rules is generated.
    """
    builder = rhel_8_bonded_network()
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
