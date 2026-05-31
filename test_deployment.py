#!/usr/bin/env python3
"""
End-to-end smoke test for the deployed microservice stack (EKS / us-east-2).

Exercises every public flow with zero third-party dependencies (stdlib only):

  * Direct health checks on each LoadBalancer (exchange, account, order, prometheus)
  * Full authenticated journey through the API gateway:
        register -> login (JWT cookie) -> GET /exchanges/{from}/{to}
  * Negative paths: unauthenticated (401) and unknown currency pair (404)
  * The exchange service directly (gateway injects `id-account`; here we send it)
  * The published documentation site

Run:   python3 test_deployment.py
Override any URL via environment variable (see URLS below).
"""

import json
import os
import sys
import urllib.error
import urllib.request
import uuid

# --------------------------------------------------------------------------- #
# Public URLs (override with env vars, e.g. GATEWAY_URL=...)                   #
# --------------------------------------------------------------------------- #
GATEWAY = os.getenv(
    "GATEWAY_URL",
    "http://a8a5a52c3759b4445b70707e9588a7a7-533079005.us-east-2.elb.amazonaws.com:8080",
)
EXCHANGE = os.getenv(
    "EXCHANGE_URL",
    "http://a3e8441a46e46422b91b1590b6ec794a-1746181786.us-east-2.elb.amazonaws.com:8080",
)
ACCOUNT = os.getenv(
    "ACCOUNT_URL",
    "http://a0f024a28f96a4f3db130b906509bd2b-1516612164.us-east-2.elb.amazonaws.com:8080",
)
ORDER = os.getenv(
    "ORDER_URL",
    "http://a1d740839a66e4181a9178ad4ec244bb-832020739.us-east-2.elb.amazonaws.com:8080",
)
PROMETHEUS = os.getenv(
    "PROMETHEUS_URL",
    "http://a316d5efe29fa41ecb04d9a6b724d760-987524877.us-east-2.elb.amazonaws.com:9090",
)
DOCS = os.getenv("DOCS_URL", "https://cynthia-valente-microsservicos.github.io/Root/")

TIMEOUT = float(os.getenv("TIMEOUT", "15"))
COOKIE_NAME = "__store_jwt_token"

# ANSI colours (disabled when output is not a TTY)
_C = sys.stdout.isatty()
GREEN, RED, YELLOW, DIM, RESET = (
    ("\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m") if _C else ("",) * 5
)

_passed = 0
_failed = 0


def request(method, url, body=None, headers=None):
    """Perform an HTTP request, returning (status, headers, text). Never raises on HTTP errors."""
    data = None
    headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - connection/timeout errors
        return None, {}, f"<connection error: {e}>"


def check(name, ok, detail=""):
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  {GREEN}PASS{RESET}  {name}{('  ' + DIM + detail + RESET) if detail else ''}")
    else:
        _failed += 1
        print(f"  {RED}FAIL{RESET}  {name}{('  ' + YELLOW + detail + RESET) if detail else ''}")
    return ok


def section(title):
    print(f"\n{title}")
    print("-" * len(title))


def main():
    print("Deployed stack smoke test")
    print("=" * 60)
    print(f"{DIM}Gateway   : {GATEWAY}{RESET}")
    print(f"{DIM}Exchange  : {EXCHANGE}{RESET}")
    print(f"{DIM}Account   : {ACCOUNT}{RESET}")
    print(f"{DIM}Order     : {ORDER}{RESET}")
    print(f"{DIM}Prometheus: {PROMETHEUS}{RESET}")
    print(f"{DIM}Docs      : {DOCS}{RESET}")

    # 1) Direct health checks ------------------------------------------------- #
    section("1. Service health checks (direct LoadBalancers)")
    for name, url in [
        ("exchange  /exchanges/health-check", f"{EXCHANGE}/exchanges/health-check"),
        ("account   /accounts/actuator/health", f"{ACCOUNT}/accounts/actuator/health"),
        ("order     /orders/health-check", f"{ORDER}/orders/health-check"),
        ("prometheus /-/healthy", f"{PROMETHEUS}/-/healthy"),
    ]:
        status, _, _ = request("GET", url)
        check(name, status == 200, f"HTTP {status}")

    # 2) Full authenticated flow through the gateway -------------------------- #
    section("2. Authenticated flow through the gateway")
    email = f"smoke-{uuid.uuid4().hex[:12]}@test.com"
    password = "pass123"

    status, _, _ = request(
        "POST", f"{GATEWAY}/auth/register",
        body={"name": "Smoke Test", "email": email, "password": password},
    )
    check(f"register ({email})", status == 201, f"HTTP {status}")

    status, headers, _ = request(
        "POST", f"{GATEWAY}/auth/login",
        body={"email": email, "password": password},
    )
    token = ""
    set_cookie = headers.get("Set-Cookie", "")
    if COOKIE_NAME + "=" in set_cookie:
        token = set_cookie.split(COOKIE_NAME + "=", 1)[1].split(";", 1)[0]
    check("login returns JWT cookie", status == 200 and len(token) > 20, f"HTTP {status}, token len {len(token)}")

    auth_cookie = {"Cookie": f"{COOKIE_NAME}={token}"}

    for pair in ("USD/EUR", "USD/BRL"):
        status, _, text = request("GET", f"{GATEWAY}/exchanges/{pair}", headers=auth_cookie)
        ok = status == 200
        detail = f"HTTP {status}"
        if ok:
            try:
                d = json.loads(text)
                detail = f"buy={d['buy']} sell={d['sell']} id-account={d['id-account'][:8]}…"
                ok = d["sell"] >= d["buy"] and bool(d["id-account"])
            except Exception:  # noqa: BLE001
                ok = False
        check(f"GET /exchanges/{pair} (authed)", ok, detail)

    # Negative: unknown currency pair -> 404
    status, _, _ = request("GET", f"{GATEWAY}/exchanges/USD/XYZ", headers=auth_cookie)
    check("GET /exchanges/USD/XYZ unknown pair -> 404", status == 404, f"HTTP {status}")

    # Negative: no auth -> 401
    status, _, _ = request("GET", f"{GATEWAY}/exchanges/USD/EUR")
    check("GET /exchanges/USD/EUR without auth -> 401", status == 401, f"HTTP {status}")

    # 3) Exchange service directly (simulating the gateway-injected header) ---- #
    section("3. Exchange service directly (with id-account header)")
    fake_account = str(uuid.uuid4())
    status, _, text = request(
        "GET", f"{EXCHANGE}/exchanges/USD/EUR", headers={"id-account": fake_account}
    )
    ok = status == 200
    detail = f"HTTP {status}"
    if ok:
        try:
            d = json.loads(text)
            detail = f"buy={d['buy']} sell={d['sell']}"
            ok = d["id-account"] == fake_account
        except Exception:  # noqa: BLE001
            ok = False
    check("direct GET /exchanges/USD/EUR", ok, detail)

    status, _, _ = request("GET", f"{EXCHANGE}/exchanges/USD/EUR")
    check("direct GET without id-account -> 401", status == 401, f"HTTP {status}")

    # 4) Documentation site --------------------------------------------------- #
    section("4. Documentation site")
    status, _, _ = request("GET", DOCS)
    check("docs site reachable", status == 200, f"HTTP {status}")

    # Summary ----------------------------------------------------------------- #
    print("\n" + "=" * 60)
    total = _passed + _failed
    colour = GREEN if _failed == 0 else RED
    print(f"{colour}{_passed}/{total} checks passed{RESET}")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
