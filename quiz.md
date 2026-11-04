# Quiz — AWS Route 53 DNS Guide

5 questions. Think first, then expand the answer.

---

**1. Your `example.com` apex record must point to an ALB. Alias or CNAME?**

<details>
<summary>Answer</summary>

**Alias.** A CNAME cannot exist at the zone apex (RFC rule — the apex must hold
SOA/NS records). Alias records are a Route 53 extension that *can* sit at the
apex and point to AWS resources like ALB, CloudFront, or S3 website endpoints —
with free, health-checked resolution.

</details>

---

**2. Failover to a DR region just happened, but the primary is back. Does Route 53 flip back automatically?**

<details>
<summary>Answer</summary>

**Yes** — with a standard failover record, Route 53 continuously re-evaluates
health checks. Once the primary's health check passes again, new DNS answers
return the primary's IP. (Note: clients that cached the secondary's answer
during its TTL will keep using it until that TTL expires — another reason to
keep failover TTLs short.)

</details>

---

**3. You need "Germany users → Frankfurt, everyone else → Virginia". Which policy?**

<details>
<summary>Answer</summary>

**Geolocation.** Create a geolocation record for country=Germany pointing at
Frankfurt, plus a **default** geolocation record pointing at Virginia. Remember:
geolocation stops at country granularity — it cannot distinguish Berlin from
Munich, and VPNs/traveling users will be misclassified.

</details>

---

**4. A health check on a CloudWatch alarm fails. What does Route 53 treat the endpoint as?**

<details>
<summary>Answer</summary>

**Unhealthy.** Route 53 treats an alarm-based health check as unhealthy when the
alarm is in `ALARM` state. This is how you fail over on *application* signals
(error rate > 1%, queue depth exploding) instead of just "server unreachable" —
DNS reacting to business metrics, not only TCP pings.

</details>

---

**5. Blue-green deploy needs 90/10 traffic. Which policy, and why isn't it exactly 90/10?**

<details>
<summary>Answer</summary>

**Weighted** routing with weights 90 and 10. It is never exact because DNS
resolvers **cache** answers: a resolver that cached "green" serves every client
behind it the same answer until the record's TTL expires. Keep TTLs short
(60s) during canary windows to make the split track the weights more closely.

</details>
