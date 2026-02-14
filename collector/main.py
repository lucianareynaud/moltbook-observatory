from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EndpointSpec:
    """
    Declarative endpoint template.

    Examples (templates depend on the platform API you are targeting):
      - "/api/public/trending"
      - "/api/public/submolt/{name}/posts?limit={limit}"
      - "/api/public/user/{user_id}/activity?limit={limit}"
    """
    name: str
    path_template: str
    params: Dict[str, Any]


@dataclass
class CollectorConfig:
    base_url: str
    user_agent: str
    timeout_s: float
    max_concurrency: int
    rps_per_host: float
    max_retries: int
    backoff_base_s: float
    backoff_cap_s: float
    jitter_ratio: float
    sqlite_path: str
    auth_bearer: Optional[str]


class RateLimiter:
    """
    Minimum-interval limiter (per process). In MVP contexts, this is deliberately simple
    and easier to audit than scattered sleeps. For distributed collection, replace with
    a shared token bucket.
    """
    def __init__(self, rps_per_host: float) -> None:
        if rps_per_host <= 0:
            raise ValueError("rps_per_host must be > 0")
        self._min_interval = 1.0 / rps_per_host
        self._lock = asyncio.Lock()
        self._last_ts = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_ts
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_ts = time.monotonic()


class SQLiteStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS request_log (
                    id TEXT PRIMARY KEY,
                    ts_utc TEXT NOT NULL,
                    endpoint_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    status_code INTEGER,
                    elapsed_ms INTEGER,
                    attempt INTEGER NOT NULL,
                    error TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_events (
                    id TEXT PRIMARY KEY,
                    ts_utc TEXT NOT NULL,
                    endpoint_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

    def log_request(
        self,
        endpoint_name: str,
        url: str,
        status_code: Optional[int],
        elapsed_ms: int,
        attempt: int,
        error: Optional[str],
    ) -> None:
        ts = utc_now_iso()
        key = sha256_hex(f"{ts}|{endpoint_name}|{url}|{attempt}|{status_code}|{error or ''}")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO request_log
                (id, ts_utc, endpoint_name, url, status_code, elapsed_ms, attempt, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (key, ts, endpoint_name, url, status_code, elapsed_ms, attempt, error),
            )

    def store_payload(self, endpoint_name: str, url: str, payload: Dict[str, Any]) -> None:
        ts = utc_now_iso()
        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        key = sha256_hex(f"{endpoint_name}|{url}|{ts}|{sha256_hex(payload_json)}")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO raw_events
                (id, ts_utc, endpoint_name, url, payload_json)
                VALUES (?, ?, ?, ?, ?);
                """,
                (key, ts, endpoint_name, url, payload_json),
            )


def build_url(base_url: str, path_template: str, params: Dict[str, Any]) -> str:
    path = path_template.format(**params)
    if not base_url.endswith("/"):
        base_url += "/"
    if path.startswith("/"):
        path = path[1:]
    return base_url + path


def compute_backoff_s(attempt: int, base: float, cap: float, jitter_ratio: float) -> float:
    exp = min(cap, base * (2 ** max(0, attempt - 1)))
    jitter = exp * jitter_ratio * random.random()
    return exp + jitter


async def fetch_json_with_retries(
    client: httpx.AsyncClient,
    limiter: RateLimiter,
    cfg: CollectorConfig,
    endpoint_name: str,
    url: str,
    store: SQLiteStore,
) -> Optional[Dict[str, Any]]:
    """
    Conservative semantics:
      - Retry 429 and 5xx with exponential backoff + jitter
      - Treat 401/403 as non-retryable in-loop, but log them as observations
      - Log JSON parse failures and continue
    """
    for attempt in range(1, cfg.max_retries + 1):
        await limiter.wait()

        t0 = time.monotonic()
        status_code: Optional[int] = None
        err: Optional[str] = None

        try:
            resp = await client.get(url)
            status_code = resp.status_code
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            if status_code in (401, 403):
                err = f"auth_status:{status_code}"
                store.log_request(endpoint_name, url, status_code, elapsed_ms, attempt, err)
                return None

            if status_code == 429 or 500 <= status_code <= 599:
                err = f"retryable_status:{status_code}"
                store.log_request(endpoint_name, url, status_code, elapsed_ms, attempt, err)
                await asyncio.sleep(compute_backoff_s(attempt, cfg.backoff_base_s, cfg.backoff_cap_s, cfg.jitter_ratio))
                continue

            resp.raise_for_status()

            try:
                data = resp.json()
            except Exception as je:
                err = f"json_parse:{type(je).__name__}"
                store.log_request(endpoint_name, url, status_code, elapsed_ms, attempt, err)
                return None

            store.log_request(endpoint_name, url, status_code, elapsed_ms, attempt, None)
            return data

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            err = f"network:{type(e).__name__}"
            store.log_request(endpoint_name, url, status_code, elapsed_ms, attempt, err)
            await asyncio.sleep(compute_backoff_s(attempt, cfg.backoff_base_s, cfg.backoff_cap_s, cfg.jitter_ratio))

        except httpx.HTTPStatusError as e:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            err = f"http_status:{e.response.status_code}"
            store.log_request(endpoint_name, url, e.response.status_code, elapsed_ms, attempt, err)
            return None

        except Exception as e:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            err = f"unexpected:{type(e).__name__}:{str(e)[:200]}"
            store.log_request(endpoint_name, url, status_code, elapsed_ms, attempt, err)
            return None

    return None


def load_config_from_env() -> CollectorConfig:
    base_url = os.environ.get("MOLTBOOK_BASE_URL", "").strip()
    if not base_url:
        raise RuntimeError("Missing MOLTBOOK_BASE_URL")

    auth_bearer = os.environ.get("MOLTBOOK_AUTH_BEARER", "").strip() or None

    return CollectorConfig(
        base_url=base_url,
        user_agent=os.environ.get("MOLTBOOK_USER_AGENT", "moltbook-observatory/0.1 (public-only)"),
        timeout_s=float(os.environ.get("MOLTBOOK_TIMEOUT_S", "20")),
        max_concurrency=int(os.environ.get("MOLTBOOK_MAX_CONCURRENCY", "4")),
        rps_per_host=float(os.environ.get("MOLTBOOK_RPS_PER_HOST", "1.0")),
        max_retries=int(os.environ.get("MOLTBOOK_MAX_RETRIES", "6")),
        backoff_base_s=float(os.environ.get("MOLTBOOK_BACKOFF_BASE_S", "0.8")),
        backoff_cap_s=float(os.environ.get("MOLTBOOK_BACKOFF_CAP_S", "30")),
        jitter_ratio=float(os.environ.get("MOLTBOOK_JITTER_RATIO", "0.25")),
        sqlite_path=os.environ.get("MOLTBOOK_SQLITE_PATH", "data/observatory.sqlite"),
        auth_bearer=auth_bearer,
    )


def load_endpoint_specs_from_env() -> List[EndpointSpec]:
    raw = os.environ.get("MOLTBOOK_ENDPOINTS_JSON", "").strip()
    if not raw:
        raise RuntimeError("Missing MOLTBOOK_ENDPOINTS_JSON (JSON list of endpoint specs)")
    try:
        items = json.loads(raw)
        specs: List[EndpointSpec] = []
        for it in items:
            specs.append(
                EndpointSpec(
                    name=str(it["name"]),
                    path_template=str(it["path_template"]),
                    params=dict(it.get("params", {})),
                )
            )
        return specs
    except Exception as e:
        raise RuntimeError(f"Invalid MOLTBOOK_ENDPOINTS_JSON: {e}") from e


async def run_once(cfg: CollectorConfig, specs: List[EndpointSpec]) -> None:
    os.makedirs(os.path.dirname(cfg.sqlite_path) or ".", exist_ok=True)
    store = SQLiteStore(cfg.sqlite_path)

    limiter = RateLimiter(cfg.rps_per_host)
    sem = asyncio.Semaphore(cfg.max_concurrency)

    headers = {"User-Agent": cfg.user_agent}
    if cfg.auth_bearer:
        headers["Authorization"] = f"Bearer {cfg.auth_bearer}"

    async with httpx.AsyncClient(timeout=cfg.timeout_s, headers=headers) as client:
        async def worker(spec: EndpointSpec) -> Tuple[str, Optional[Dict[str, Any]]]:
            url = build_url(cfg.base_url, spec.path_template, spec.params)
            async with sem:
                data = await fetch_json_with_retries(client, limiter, cfg, spec.name, url, store)
                if data is not None:
                    store.store_payload(spec.name, url, data)
                return (spec.name, data)

        results = await asyncio.gather(*(worker(s) for s in specs))
        ok = sum(1 for _, data in results if data is not None)
        total = len(results)
        print(f"[collector] completed: {ok}/{total} endpoints stored into {cfg.sqlite_path}")


def main() -> None:
    cfg = load_config_from_env()
    specs = load_endpoint_specs_from_env()
    asyncio.run(run_once(cfg, specs))


if __name__ == "__main__":
    main()
