#!/usr/bin/env python3
"""
route53_routing_lab.py — simulate Amazon Route 53 routing policies OFFLINE.

No AWS account needed. This lab models the decision logic behind the policies
from the README so you can *feel* how each one answers DNS queries, including
how health checks flip a failover record and why weighted answers drift.

Policies covered: simple, failover, weighted, latency-based, geolocation,
multivalue answer. (Geoproximity needs Route 53 Traffic Flow bias — noted only.)

Run:  python3 route53_routing_lab.py
"""

import random
from dataclasses import dataclass, field

random.seed(53)


# ----------------------------------------------------------------------------
# Building blocks
# ----------------------------------------------------------------------------
@dataclass
class Endpoint:
    name: str
    ip: str
    region: str          # aws region code
    country: str         # geolocation routing
    weight: int = 0      # weighted routing
    healthy: bool = True


@dataclass
class HealthCheck:
    """Simplified Route 53 health check: unhealthy after 3 consecutive failures."""
    endpoint: Endpoint
    failures_needed: int = 3
    _streak: int = field(default=0, init=False)

    def probe(self, observed_up: bool) -> bool:
        if observed_up:
            self._streak = 0
            self.endpoint.healthy = True
        else:
            self._streak += 1
            if self._streak >= self.failures_needed:
                self.endpoint.healthy = False
        return self.endpoint.healthy


# ----------------------------------------------------------------------------
# Routing policies
# ----------------------------------------------------------------------------
def simple(endpoints):
    """Simple: always the first configured value (no health checks)."""
    return endpoints[0].ip


def failover(primary, secondary):
    """Failover: primary while healthy, else secondary."""
    return primary.ip if primary.healthy else secondary.ip


def weighted(endpoints):
    """Weighted: random pick proportional to weight (only healthy endpoints)."""
    healthy = [e for e in endpoints if e.healthy]
    total = sum(e.weight for e in healthy)
    r = random.uniform(0, total)
    upto = 0
    for e in healthy:
        upto += e.weight
        if r <= upto:
            return e.ip
    return healthy[-1].ip  # pragma: no cover


LATENCY_MS = {  # simulated network latency from client region -> endpoint region
    ("us", "us-east-1"): 20, ("us", "eu-west-1"): 90, ("us", "ap-southeast-1"): 180,
    ("de", "us-east-1"): 95, ("de", "eu-west-1"): 15, ("de", "ap-southeast-1"): 190,
    ("id", "us-east-1"): 220, ("id", "eu-west-1"): 180, ("id", "ap-southeast-1"): 25,
}


def latency_based(endpoints, client_country):
    """Latency-based: the healthy endpoint with the lowest network latency."""
    healthy = [e for e in endpoints if e.healthy]
    return min(healthy, key=lambda e: LATENCY_MS[(client_country, e.region)]).ip


def geolocation(endpoints, client_country, default):
    """Geolocation: exact country match, else the default record."""
    for e in endpoints:
        if e.healthy and e.country == client_country:
            return e.ip
    return default.ip


def multivalue(endpoints):
    """Multivalue answer: return ALL healthy records (client picks one)."""
    return [e.ip for e in endpoints if e.healthy]


# ----------------------------------------------------------------------------
# Demo
# ----------------------------------------------------------------------------
def main():
    print("=== Failover policy: primary dies, DNS flips ===")
    primary = Endpoint("primary", "203.0.113.10", "ap-southeast-1", "sg")
    secondary = Endpoint("secondary", "198.51.100.20", "ap-southeast-3", "id")
    check = HealthCheck(primary)
    # probes 1-3: primary up; probe 4-6: primary down (3 fails -> unhealthy)
    for probe, observed_up in enumerate([True, True, True, False, False, False], 1):
        check.probe(observed_up)
        print(f"probe {probe}: primary={'HEALTHY' if primary.healthy else 'UNHEALTHY':9s}"
              f" -> answer {failover(primary, secondary)}")
    print()

    print("=== Weighted policy: 80/20 canary over 1000 queries ===")
    blue = Endpoint("blue", "203.0.113.11", "ap-southeast-1", "sg", weight=80)
    green = Endpoint("green", "203.0.113.12", "ap-southeast-1", "sg", weight=20)
    counts = {blue.ip: 0, green.ip: 0}
    for _ in range(1000):
        counts[weighted([blue, green])] += 1
    print(f"blue={counts[blue.ip]} green={counts[green.ip]}  (~80/20 as configured)")
    print("note: DNS caching means real splits drift — weights are guidance, not exact.")
    print()

    print("=== Latency-based: same endpoints, three different users ===")
    va = Endpoint("virginia", "203.0.113.21", "us-east-1", "us")
    ie = Endpoint("ireland", "203.0.113.22", "eu-west-1", "ie")
    sg = Endpoint("singapore", "203.0.113.23", "ap-southeast-1", "sg")
    for user in ["us", "de", "id"]:
        print(f"user in {user:3s} -> {latency_based([va, ie, sg], user)}")
    print()

    print("=== Geolocation: German users get the Frankfurt record ===")
    frankfurt = Endpoint("frankfurt", "203.0.113.24", "eu-central-1", "de")
    for user in ["de", "id", "br"]:
        print(f"user in {user:3s} -> {geolocation([frankfurt, sg], user, default=va)}")
    print()

    print("=== Multivalue answer: dead records are dropped ===")
    ie.healthy = False  # one endpoint down
    print(f"answers returned: {multivalue([va, ie, sg])}  (unhealthy record excluded)")
    print()

    print("=== Simple policy caveat ===")
    print(f"answer: {simple([va, ie, sg])}  (no health checks — dead endpoint = dead answer)")


if __name__ == "__main__":
    main()
