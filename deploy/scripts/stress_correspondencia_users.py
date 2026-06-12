#!/usr/bin/env python3
"""
Prueba de carga autenticada (sesión Django vía API login) sobre páginas de uso frecuente.

Uso:
  python deploy/scripts/stress_correspondencia_users.py --base-url http://127.0.0.1/registros/correspondencia \\
    --users 4 --duration 45 --label baseline

Requiere: requests (venv del proyecto).
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import requests

# (nombre, path relativo, peso relativo de clics)
USER_PAGES: List[Tuple[str, str, int]] = [
    ("dashboard_usuario", "dashboard/", 12),
    ("bandeja_personal", "bandeja/", 22),
    ("bandeja_oficina", "bandeja-oficina/", 18),
    ("bandeja_respuestas_salientes", "bandeja-salientes/", 14),  # Mis respuestas (sidebar)
    ("bandeja_interoficina", "bandeja-interoficina/", 6),
    ("historial", "historial/", 10),
    ("pendientes_distribuir", "pendientes-distribuir/", 5),
]

VENTANILLA_PAGES: List[Tuple[str, str, int]] = [
    ("dashboard_ventanilla", "ventanilla/dashboard/", 10),
    ("bandeja_correos_pendientes", "ventanilla/correos-pendientes/", 12),
    ("bandeja_respuestas_pendientes", "ventanilla/respuestas-pendientes/", 10),
]

DEFAULT_USERS = [
    ("superprueba3", "12345"),
    ("superprueba1", "12345"),
    ("superprueba", "12345"),
    ("usuariopruebas1", "12345"),
    ("usuariopruebas2", "12345"),
    ("USUARIOPRUEBA", "12345"),
]


@dataclass
class Sample:
    page: str
    status: int
    elapsed: float
    error: Optional[str] = None


@dataclass
class RunStats:
    label: str
    users: int
    duration: float
    samples: List[Sample] = field(default_factory=list)
    logins_failed: int = 0

    def merge(self, other: "RunStats") -> None:
        self.samples.extend(other.samples)
        self.logins_failed += other.logins_failed


_lock = threading.Lock()
_global_samples: List[Sample] = []


def _weighted_choice(pages: List[Tuple[str, str, int]]) -> Tuple[str, str]:
    names_paths = [(n, p) for n, p, _ in pages]
    weights = [w for _, _, w in pages]
    return random.choices(names_paths, weights=weights, k=1)[0]


def login_session(base_url: str, username: str, password: str) -> Optional[requests.Session]:
    session = requests.Session()
    session.headers.update({"User-Agent": f"stress-test/{username}"})
    url = f"{base_url.rstrip('/')}/api/auth/login/"
    try:
        r = session.post(url, json={"username": username, "password": password}, timeout=60)
    except requests.RequestException as exc:
        print(f"[login] {username}: red {exc}", file=sys.stderr)
        return None
    if r.status_code != 200:
        print(f"[login] {username}: HTTP {r.status_code} {r.text[:120]}", file=sys.stderr)
        return None
    try:
        body = r.json()
    except json.JSONDecodeError:
        print(f"[login] {username}: respuesta no JSON", file=sys.stderr)
        return None
    if not body.get("success"):
        print(f"[login] {username}: success=false", file=sys.stderr)
        return None
    return session


def virtual_user(
    base_url: str,
    username: str,
    password: str,
    pages: List[Tuple[str, str, int]],
    end_time: float,
    think_min: float,
    think_max: float,
    extra_path: Optional[str],
) -> RunStats:
    stats = RunStats(label="", users=1, duration=0)
    session = login_session(base_url, username, password)
    if session is None:
        stats.logins_failed = 1
        return stats

    pool = list(pages)
    if extra_path:
        pool = pool + [("crear_respuesta", extra_path, 8)]

    while time.time() < end_time:
        name, path = _weighted_choice(pool)
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        t0 = time.perf_counter()
        status = 0
        err: Optional[str] = None
        try:
            r = session.get(url, timeout=65, allow_redirects=True)
            status = r.status_code
        except requests.RequestException as exc:
            err = type(exc).__name__
            status = 0
        elapsed = time.perf_counter() - t0
        sample = Sample(page=name, status=status, elapsed=elapsed, error=err)
        stats.samples.append(sample)
        with _lock:
            _global_samples.append(sample)
        time.sleep(random.uniform(think_min, think_max))
    return stats


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_v) - 1)
    if f == c:
        return sorted_v[f]
    return sorted_v[f] + (sorted_v[c] - sorted_v[f]) * (k - f)


def summarize(stats: RunStats) -> dict:
    samples = stats.samples
    total = len(samples)
    ok = [s for s in samples if 200 <= s.status < 400]
    latencies = [s.elapsed for s in ok]
    by_status = Counter(s.status for s in samples)
    by_page: Dict[str, List[float]] = defaultdict(list)
    for s in ok:
        by_page[s.page].append(s.elapsed)
    errors_net = sum(1 for s in samples if s.error)
    bad_http = sum(1 for s in samples if s.status >= 400 or s.status == 0)
    rps = total / stats.duration if stats.duration > 0 else 0
    return {
        "label": stats.label,
        "concurrent_users": stats.users,
        "duration_s": round(stats.duration, 1),
        "requests": total,
        "rps": round(rps, 2),
        "logins_failed": stats.logins_failed,
        "error_rate_pct": round(100.0 * bad_http / total, 2) if total else 0,
        "network_errors": errors_net,
        "status_counts": dict(sorted(by_status.items())),
        "p50_s": round(percentile(latencies, 50), 3),
        "p95_s": round(percentile(latencies, 95), 3),
        "p99_s": round(percentile(latencies, 99), 3),
        "max_s": round(max(latencies), 3) if latencies else 0,
        "per_page_p95": {
            p: round(percentile(v, 95), 3) for p, v in sorted(by_page.items())
        },
    }


def run_phase(args, users: int, label: str) -> dict:
    global _global_samples
    _global_samples = []
    if args.username:
        creds = [(args.username, args.password)] * users
    else:
        creds = DEFAULT_USERS[:users]
        while len(creds) < users:
            creds.append(creds[len(creds) % len(DEFAULT_USERS)])

    extra_path = args.responder_path
    pages = list(USER_PAGES)
    if args.include_ventanilla:
        pages = pages + VENTANILLA_PAGES

    end_time = time.time() + args.duration
    started = time.time()
    partials: List[RunStats] = []

    with ThreadPoolExecutor(max_workers=users) as pool:
        futures = []
        for i in range(users):
            u, p = creds[i]
            futures.append(
                pool.submit(
                    virtual_user,
                    args.base_url,
                    u,
                    p,
                    pages,
                    end_time,
                    args.think_min,
                    args.think_max,
                    extra_path if i == 0 else None,
                )
            )
        for f in futures:
            partials.append(f.result())

    merged = RunStats(label=label, users=users, duration=time.time() - started)
    for p in partials:
        merged.merge(p)
    return summarize(merged)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stress test correspondencia (sesión autenticada)")
    parser.add_argument("--base-url", default="http://127.0.0.1/registros/correspondencia")
    parser.add_argument("--users", type=int, default=4)
    parser.add_argument("--duration", type=int, default=40, help="segundos por fase")
    parser.add_argument("--label", default="run")
    parser.add_argument("--think-min", type=float, default=0.15)
    parser.add_argument("--think-max", type=float, default=0.45)
    parser.add_argument("--include-ventanilla", action="store_true", default=True)
    parser.add_argument("--no-ventanilla", action="store_false", dest="include_ventanilla")
    parser.add_argument("--responder-path", default="", help="ej. correspondencia/123/responder/")
    parser.add_argument("--phases", default="", help="ej. 2,8,16,30 (usuarios por fase)")
    parser.add_argument("--username", default="", help="Forzar mismo usuario en todos los VUs")
    parser.add_argument("--password", default="12345")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    phases: List[Tuple[int, str]] = []
    if args.phases:
        for i, u in enumerate(p.strip() for p in args.phases.split(",") if p.strip()):
            phases.append((int(u), f"phase_{u}u"))
    else:
        phases = [(args.users, args.label)]

    results = []
    for users, label in phases:
        print(f"\n=== {label}: {users} usuarios, {args.duration}s ===", flush=True)
        results.append(run_phase(args, users, label))
        print(json.dumps(results[-1], indent=2, ensure_ascii=False), flush=True)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)
        print(f"\nGuardado: {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
