"""One bounded phone-draft integration run; not a speculative-decoding result."""
import argparse
import csv
import json
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .core.phone import clear_caps, health, sample, set_caps
from .core.storage import append_jsonl, write_json
from .studies.motivation.exp1_thermal_degradation.plot_run import plot_run


def run(config, run_id):
    if config.get("mode") != "phone_draft":
        raise ValueError("Only phone_draft integration mode is implemented; Orin verification is pending")
    if config["run_duration_s"] <= 0 or config["max_requests"] <= 0:
        raise ValueError("run_duration_s and max_requests must be positive")
    directory = Path(config["output_root"]) / run_id
    if directory.exists():
        raise FileExistsError(f"Run directory already exists: {directory}")
    directory.mkdir(parents=True)
    write_json(directory / "config.resolved.json", config)
    write_json(directory / "status.json", {"state": "RUNNING", "started_utc": datetime.now(timezone.utc).isoformat()})
    adb_path = config["adb_path"]
    stop = threading.Event()
    telemetry_error = []
    start = time.monotonic()
    readings = []

    def monitor():
        while not stop.is_set():
            try:
                row = {"elapsed_s": round(time.monotonic() - start, 3), **sample(adb_path)}
                readings.append(row)
                if (row["cpu_temp_c"] >= config["stop_cpu_temp_c"] or
                        row["battery_temp_c"] >= config["stop_battery_temp_c"]):
                    stop.set()
                    break
            except Exception as exc:
                telemetry_error.append(str(exc))
                stop.set()
                break
            stop.wait(config.get("sample_interval_s", 1))

    caps = config.get("frequency_caps_khz")
    caps_applied = False
    state = "FAILED"
    try:
        health(config["health_url"])
        if caps is not None:
            set_caps(adb_path, caps)
            caps_applied = True
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        count = 0
        tokens = 0
        total_ms = 0.0
        while not stop.is_set() and count < config["max_requests"] and time.monotonic() - start < config["run_duration_s"]:
            payload = json.dumps({"prompt": config["prompt"], "n_predict": config["tokens_per_request"],
                                  "temperature": 0, "stream": False}).encode("utf-8")
            request = urllib.request.Request(config["completion_url"], payload, {"Content-Type": "application/json"})
            t0 = time.monotonic()
            with urllib.request.urlopen(request, timeout=config.get("request_timeout_s", 30)) as response:
                result = json.load(response)
            elapsed_ms = (time.monotonic() - t0) * 1000
            n = int(result.get("tokens_predicted", 0))
            append_jsonl(directory / "rounds.jsonl", {"elapsed_s": round(time.monotonic() - start, 3),
                         "request": count, "valid_tokens": n, "elapsed_ms": elapsed_ms,
                         "draft_compute_ms": result.get("timings", {}).get("predicted_ms")})
            count += 1
            tokens += n
            total_ms += elapsed_ms
        stop.set()
        thread.join(timeout=5)
        if telemetry_error:
            raise RuntimeError(f"Telemetry stopped: {telemetry_error[-1]}")
        if not readings:
            raise RuntimeError("No phone telemetry captured")
        with (directory / "phone_telemetry.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=readings[0].keys())
            writer.writeheader()
            writer.writerows(readings)
        summary = {"mode": "phone_draft", "requests": count, "valid_tokens": tokens,
                   "total_request_ms": total_ms, "amortized_ms_per_token": total_ms / tokens if tokens else None,
                   "max_cpu_temp_c": max(r["cpu_temp_c"] for r in readings),
                   "max_battery_temp_c": max(r["battery_temp_c"] for r in readings),
                   "stop_reason": "temperature_guard" if readings[-1]["cpu_temp_c"] >= config["stop_cpu_temp_c"] or
                   readings[-1]["battery_temp_c"] >= config["stop_battery_temp_c"] else "duration_or_request_limit"}
        write_json(directory / "summary.json", summary)
        plot_run(directory)
        state = "PLOTTED"
        return summary
    finally:
        stop.set()
        if caps_applied:
            clear_caps(adb_path)
        write_json(directory / "status.json", {"state": state, "finished_utc": datetime.now(timezone.utc).isoformat()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(json.dumps(run(config, args.run_id), ensure_ascii=False))


if __name__ == "__main__":
    main()
