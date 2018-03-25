#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import time
import sys
import urllib2
from boto.route53.connection import Route53Connection
from boto.route53.exception import DNSServerError
from boto.route53.record import ResourceRecordSets
import logging

logger = logging.getLogger(__name__)

console = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('[%(asctime)s] (%(levelname)s) %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

handler = logging.FileHandler('/tmp/dyndns_route53.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.DEBUG)


def get_change_id(response):
    return response['ChangeInfo']['Id'].split('/')[-1]


def get_change_status(response):
    return response['ChangeInfo']['Status']


def get_args():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("hosted_zone", help="The AWS Hosted Zone")
    parser.add_argument("domain_name", help="The domain to update")
    parser.add_argument("ipv4", nargs="?",
                        help="""IPv4 manually assigned
                                ('disable' to disable IPv4 updating)""")
    parser.add_argument("ipv6", nargs="?",
                        help="""IPv6 manually assigned
                                ('disable' to disable IPv6 updating)""")
    args = parser.parse_args()

    logger.debug(args)

    return args


def resolve_name_ip(name, resource_type):
    import dns.resolver

    resolver = dns.resolver.Resolver()
    resolver.nameservers = [
        '205.251.194.115',
        '8.8.8.8',
        '8.8.4.4'
    ]
    try:
        answer = resolver.query(name, resource_type)

        """
        >>> answer.response.answer[0].to_text()
        home.mydomain.com. 60 IN A 192.168.0.2'
        >>> answer.response.answer[0].items
        [<DNS IN A rdata: 192.168.0.2>]
        >>> answer.response.answer[0].items[0].address
        '192.168.0.2'
        """
        # return answer.response.answer[0].items[0].address
        return answer[0].address
    except Exception, e:
        logger.error("Exception trying to solve %s (%s): %s", name,
                     resource_type, e)


def update_dns(args):

    resources = [(4, {"ip": args.ipv4, "resource_type": "A"}),
                 (6, {"ip": args.ipv6, "resource_type": "AAAA"})]
    conn = None
    changes = None

    for family, data in resources:
        current_ip = data["ip"]
        resource_type = data["resource_type"]

        if current_ip == "disable":
            logger.warn("Family IPv%d disabled." % family)
            continue

        # Avoid to hit the Route53 API if is not necessary.
        # so compare first to a DNS server if the IP changed
        logger.debug("My IPv%d: %s", family, current_ip)
        resolved_ip = resolve_name_ip(args.domain_name, resource_type)
        if resolved_ip == current_ip:
            logger.debug('My IP = IP in DNS, nothing to do.')
            continue
        else:
            logger.debug("IP in DNS is different (%s), updating.", resolved_ip)

        if not conn:
            conn = Route53Connection()
            changes = ResourceRecordSets(conn, args.hosted_zone, '')

        try:
            zone = conn.get_hosted_zone(args.hosted_zone)
        except DNSServerError, e:
            logger.error(e)
            sys.exit(1)

        logger.debug(zone)

        response = conn.get_all_rrsets(args.hosted_zone, resource_type,
                                       args.domain_name, maxitems=1)[0]

        logger.debug(response)

        if current_ip not in response.resource_records:
            logger.info('Found new IP: %s' % current_ip)

            # Delete the old record, and create a new one.
            # This code is from route53.py script, the change record command
            change1 = changes.add_change("DELETE", args.domain_name,
                                         resource_type, response.ttl)
            for old_value in response.resource_records:
                change1.add_value(old_value)

            change2 = changes.add_change("CREATE", args.domain_name,
                                         resource_type, response.ttl)
            change2.add_value(current_ip)

    if conn:
        logger.warn("Changed detected, contacting AWS Route53 API")
        try:
            commit = changes.commit()
            logger.debug('%s' % commit)
        except Exception as e:
            logger.error("Changes %s can't be made: %s" % (changes, e))
            sys.exit(1)
        else:

            change = conn.get_change(
                        get_change_id(
                            commit['ChangeResourceRecordSetsResponse']
                        )
                     )
            logger.debug('%s' % change)

            while get_change_status(change['GetChangeResponse']) == 'PENDING':
                time.sleep(10)
                change = conn.get_change(
                             get_change_id(change['GetChangeResponse'])
                )
                logger.debug('%s' % change)
            if get_change_status(change['GetChangeResponse']) == 'INSYNC':
                logger.info('Change %s %s from %s -> %s',
                            args.domain_name, resource_type,
                            response.resource_records[0], current_ip)
                logger.warn("IP%s updated: %s" % (family, current_ip))
            else:
                logger.warning('Unknown status for the change: %s' % change)
                logger.debug('%s' % change)
    else:
        logger.debug("No changed detected.")


def get_external_ipv4():
    return urllib2.urlopen("http://whatismyip.akamai.com").read()


def get_external_ipv6():
    import netifaces
    for iface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(iface)
        ipv6s = addresses.get(netifaces.AF_INET6)
        if not ipv6s:
            continue

        for ipv6 in ipv6s:
            ipv6_addr = ipv6["addr"]
            if not ipv6_addr.startswith("f") and not ipv6_addr.startswith(":"):
                return ipv6_addr


def update_ips(args):
    if not args.ipv4:
        args.ipv4 = get_external_ipv4()

    if not args.ipv6:
        args.ipv6 = get_external_ipv6()


if __name__ == '__main__':
    args = get_args()
    update_ips(args)
    update_dns(args)
