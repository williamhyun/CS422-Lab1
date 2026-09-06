#!/usr/bin/env python3
"""Return the public iperf3 server list as a plain list of IP addresses.

The upstream site (https://iperf3serverlist.net/) is a React app that loads its
table from a static export, so we pull the export directly:

    https://export.iperf3serverlist.net/listed_iperf3_servers.json
    https://export.iperf3serverlist.net/listed_iperf3_servers.csv

Roughly half of the listed entries are DNS names (e.g. speedtestfl.telecom.mu)
rather than IP literals, so those are resolved to IPv4 addresses. A name the
system resolver rejects is retried against public resolvers over the wire,
which is what recovers names that mDNSResponder has negatively cached; anything
still unresolved after that is reported on stderr rather than dropped silently.
Duplicates are dropped, so every element is a distinct address that
ping/traceroute/geolocation can be pointed at directly.

Use as a library:

    from fetch_servers import fetch_ips
    ips = fetch_ips()                      # all servers
    five = fetch_ips(sample=5, seed=422)   # reproducible random subset

or as a CLI, which prints one address per line:

    ./fetch_servers.py
    ./fetch_servers.py --sample 5 --seed 422 > ips.txt

Standard library only; no pip install required.
"""

from __future__ import annotations

import argparse
import csv
import io
import ipaddress
import json
import random
import socket
import struct
import sys
import time
import urllib.error
import urllib.request

JSON_URL = "https://export.iperf3serverlist.net/listed_iperf3_servers.json"
CSV_URL = "https://export.iperf3serverlist.net/listed_iperf3_servers.csv"

# The export host rejects the default urllib agent.
USER_AGENT = "Mozilla/5.0 (compatible; CS422-Lab1/1.0)"

HOST_KEYS = ("IP/HOST", "IP", "HOST", "HOSTNAME")

# Queried directly, over the wire, when the system resolver fails a name.
PUBLIC_DNS_SERVERS = ("8.8.8.8", "1.1.1.1")

# Extra passes over the names that failed. The first retry is immediate, since
# it goes straight to a public resolver and has no cache to wait out; later
# rounds pause a growing amount to let a genuinely flaky server recover.
DNS_RETRY_ROUNDS = 4
DNS_RETRY_DELAY = 2.0


def fetch_ips(sample: int = 0, seed: int | None = None, timeout: float = 20.0) -> list[str]:
    """Download the server list and return distinct IP addresses.

    Hostnames are resolved to IPv4 and anything that cannot be resolved is
    skipped. Pass sample to take a random subset, and seed alongside it to make
    that subset reproducible across runs.
    """
    hosts = _download_hosts(timeout=timeout)
    resolved = _resolve_hosts(hosts)

    unresolved = [h for h, ip in resolved.items() if not ip]
    if unresolved:
        print(
            f"warning: {len(unresolved)} host(s) still unresolved after "
            f"{DNS_RETRY_ROUNDS} retry round(s) and excluded: "
            f"{', '.join(unresolved)}",
            file=sys.stderr,
        )

    ips: list[str] = []
    seen: set[str] = set()
    for host in hosts:
        ip = resolved.get(host)
        # Distinct hostnames sometimes share one machine, and at least one
        # address is listed both as a literal and behind a name.
        if ip and ip not in seen:
            seen.add(ip)
            ips.append(ip)

    if sample:
        random.Random(seed).shuffle(ips)
        ips = ips[:sample]
    return ips


def _download_hosts(timeout: float = 20.0) -> list[str]:
    """Return the raw IP/HOST column: a mix of IP literals and DNS names.

    Tries the JSON export first and falls back to the CSV export, which carries
    the same rows in a different shape.
    """
    errors: list[str] = []
    for url in (JSON_URL, CSV_URL):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append(f"{url}: {exc}")
            continue
        try:
            hosts = _parse_hosts(payload, url)
        except (json.JSONDecodeError, csv.Error, ValueError) as exc:
            errors.append(f"{url}: malformed data ({exc})")
            continue
        if hosts:
            return hosts
        errors.append(f"{url}: no hosts found")
    raise RuntimeError("could not fetch the iperf3 server list -> " + "; ".join(errors))


def _parse_hosts(payload: bytes, source: str = "") -> list[str]:
    """Pull the host column out of a JSON or CSV export body."""
    text = payload.decode("utf-8-sig", errors="replace").strip()
    if source.endswith(".json") or text[:1] in "[{":
        data = json.loads(text)
        records = data.get("servers", data) if isinstance(data, dict) else data
        if not isinstance(records, list):
            raise ValueError("expected a list of server records")
    else:
        records = list(csv.DictReader(io.StringIO(text)))

    hosts = []
    for record in records:
        if isinstance(record, dict):
            host = _host_of(record)
            if host:
                hosts.append(host)
    return hosts


def _host_of(record: dict) -> str:
    """Read the host field, tolerating upstream header drift."""
    for key in HOST_KEYS:
        for actual, value in record.items():
            if actual and actual.strip().upper() == key:
                return str(value or "").strip().rstrip(".")
    return ""


def _resolve(host: str) -> str | None:
    """Resolve one host to an address, preferring IPv4. None if it fails.

    IP literals pass through untouched. Otherwise this asks for an A record
    first and only falls back to an unrestricted lookup if that yields nothing,
    so a dual-stack host still comes back as IPv4. This is a single attempt;
    retrying is _resolve_hosts's job.
    """
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        pass

    for want in (socket.AF_INET, socket.AF_UNSPEC):
        try:
            infos = socket.getaddrinfo(host, None, want, socket.SOCK_STREAM)
        except (socket.gaierror, UnicodeError, OSError):
            continue
        # AF_UNSPEC can list IPv6 first; keep preferring IPv4.
        for info in sorted(infos, key=lambda i: 0 if i[0] == socket.AF_INET else 1):
            return info[4][0]
    return None


def _skip_name(reply: bytes, offset: int) -> int:
    """Return the offset just past a (possibly compressed) DNS name."""
    while offset < len(reply):
        length = reply[offset]
        if length & 0xC0 == 0xC0:  # compression pointer: 2 bytes, ends the name
            return offset + 2
        offset += 1
        if length == 0:
            return offset
        offset += length
    return offset


def _first_a_record(reply: bytes, query_id: int) -> str | None:
    """Pull the first A record out of a DNS reply, or None if there is none."""
    try:
        if len(reply) < 12 or struct.unpack("!H", reply[:2])[0] != query_id:
            return None
        flags, qdcount, ancount = struct.unpack("!HHH", reply[2:8])
        if flags & 0x000F:  # RCODE is non-zero, e.g. NXDOMAIN or SERVFAIL
            return None
        offset = 12
        for _ in range(qdcount):  # skip the echoed question section
            offset = _skip_name(reply, offset) + 4
        for _ in range(ancount):
            offset = _skip_name(reply, offset)
            rtype, _rclass, _ttl, rdlength = struct.unpack("!HHIH", reply[offset:offset + 10])
            offset += 10
            if rtype == 1 and rdlength == 4:  # an A record holds a 4-byte address
                return socket.inet_ntoa(reply[offset:offset + 4])
            offset += rdlength  # a CNAME or anything else: keep looking
    except (struct.error, OSError):
        return None
    return None


def _query_public_dns(host: str, timeout: float = 3.0) -> str | None:
    """Ask public resolvers for an A record directly, bypassing the OS resolver.

    macOS routes getaddrinfo through mDNSResponder, which will happily serve a
    stale negative answer for a name that resolves fine upstream, so retrying
    getaddrinfo only re-reads that bad cache entry. Going over the wire is what
    actually recovers those names. Returns None if no server gives an answer.
    """
    try:
        labels = [label.encode("idna") for label in host.rstrip(".").split(".") if label]
    except UnicodeError:
        return None
    question = b"".join(bytes([len(label)]) + label for label in labels) + b"\x00"
    question += struct.pack("!HH", 1, 1)  # QTYPE=A, QCLASS=IN

    for server in PUBLIC_DNS_SERVERS:
        query_id = random.randrange(1 << 16)
        # Flags 0x0100: standard query, recursion desired. One question, no RRs.
        packet = struct.pack("!HHHHHH", query_id, 0x0100, 1, 0, 0, 0) + question
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout)
                sock.sendto(packet, (server, 53))
                reply, _ = sock.recvfrom(4096)
        except OSError:
            continue
        address = _first_a_record(reply, query_id)
        if address:
            return address
    return None


def _resolve_hosts(hosts: list[str]) -> dict[str, str | None]:
    """Resolve every host, then keep retrying the ones that failed.

    Retries query public resolvers directly first, because the usual reason a
    name fails here is the local resolver rather than the name itself. Returns a
    host -> address mapping, where None means the name survived every round.
    """
    resolved: dict[str, str | None] = {host: _resolve(host) for host in dict.fromkeys(hosts)}

    for round_number in range(1, DNS_RETRY_ROUNDS + 1):
        pending = [host for host, ip in resolved.items() if not ip]
        if not pending:
            break
        if round_number > 1:
            time.sleep(DNS_RETRY_DELAY * (round_number - 1))
        print(
            f"retrying {len(pending)} unresolved host(s) over the wire, "
            f"round {round_number}/{DNS_RETRY_ROUNDS}",
            file=sys.stderr,
        )
        for host in pending:
            resolved[host] = _query_public_dns(host) or _resolve(host)

    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the iperf3 server list as one IP address per line.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-n", "--sample", type=int, default=0,
        help="pick this many random addresses (0 keeps all)",
    )
    parser.add_argument("--seed", type=int, help="RNG seed, for a reproducible sample")
    args = parser.parse_args(argv)

    try:
        ips = fetch_ips(sample=args.sample, seed=args.seed)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not ips:
        print("error: server list downloaded but no addresses resolved", file=sys.stderr)
        return 1
    if args.sample and args.sample > len(ips):
        print(f"warning: asked for {args.sample} but only {len(ips)} available", file=sys.stderr)

    print("\n".join(ips))
    print(f"({len(ips)} addresses)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
