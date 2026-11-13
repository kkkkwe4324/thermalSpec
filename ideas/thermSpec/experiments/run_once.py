"""One bounded run. Raw events are written continuously; analysis is a study hook."""
import argparse
import csv
import hashlib
import importlib
import json
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .core.config import load_project
from .core.phone import clear_caps, connected_serial, forward_port, health, sample, set_caps
from .core.storage import EventWriter, write_json


def run(config, run_id):
    if config.get("mode") != "phone_draft":
        raise ValueError("Only phone_draft integration mode is implemented; Orin verification is pending")
    if config["run_duration_s"] <= 0 or config["max_requests"] <= 0:
        raise ValueError("run_duration_s and max_requests must be positive")
    adb_path = config["adb_path"]
    serial = connected_serial(adb_path, config.get("adb_serial"))
    if config.get("require_unplugged", False) and ":" not in serial:
        raise RuntimeError("Unplugged run requires a wireless ADB device")
    project, project_hash = load_project(config.get("project_config"))
    directory = Path(config["output_root"]) / run_id
    if directory.exists():
        raise FileExistsError(f"Run directory already exists: {directory}")
    directory.mkdir(parents=True)
    resolved = {**config, "adb_serial": serial, "adb_transport": "wifi" if ":" in serial else "usb",
                "project": project, "project_sha256": project_hash,
                "prompt_sha256": hashlib.sha256(config["prompt"].encode("utf-8")).hexdigest()}
    write_json(directory / "config.resolved.json", resolved)
    started_utc = datetime.now(timezone.utc).isoformat()
    write_json(directory / "status.json", {"state": "RUNNING", "started_utc": started_utc})
    start_ns = time.monotonic_ns()
    events = EventWriter(directory / "events.jsonl", run_id, start_ns)
    stop = threading.Event()
    readings = []
    telemetry_error = []
    guard_reasons = []
    caps_applied = False
    state = "FAILED"
    error = None
    reason = None
    events.emit("run_start", "controller", {"mode": config["mode"], "adb_serial": serial,
                "project_sha256": project_hash})

    def monitor():
        while not stop.is_set():
            try:
                reading = sample(adb_path, serial=serial)
                sample_ns = time.monotonic_ns()
                row = {"elapsed_s": (sample_ns - start_ns) / 1e9, **reading}
                events.emit("phone_telemetry", "phone_via_adb", reading, sample_ns=sample_ns)
                readings.append(row)
                if (reading["cpu_temp_c"] >= config["stop_cpu_temp_c"] or
                        reading["battery_temp_c"] >= config["stop_battery_temp_c"]):
                    guard_reasons.append("temperature_guard")
                    events.emit("guard_stop", "controller", {"reason": "temperature", "reading": reading})
                    stop.set()
                    break
                if config.get("require_unplugged", False) and reading["usb_online"] != 0:
                    guard_reasons.append("usb_connected")
                    events.emit("guard_stop", "controller", {"reason": "usb_connected", "reading": reading})
                    stop.set()
                    break
            except Exception as exc:
                telemetry_error.append(str(exc))
                events.emit("telemetry_error", "controller", {"message": str(exc)})
                stop.set()
                break
            stop.wait(config.get("sample_interval_s", 1))

    try:
        if config.get("adb_forward_port"):
            forward_port(adb_path, serial, config["adb_forward_port"])
            events.emit("adb_forward", "controller", {"serial": serial, "port": config["adb_forward_port"]})
        health(config["health_url"])
        caps = config.get("frequency_caps_khz")
        if caps is not None:
            set_caps(adb_path, caps, serial=serial)
            caps_applied = True
            events.emit("frequency_request", "controller", {"caps_khz": caps})
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        count = 0
        tokens = 0
        request_ms_total = 0.0
        while (not stop.is_set() and count < config["max_requests"] and
               (time.monotonic_ns() - start_ns) / 1e9 < config["run_duration_s"]):
            payload = json.dumps({"prompt": config["prompt"],
                                  "n_predict": config["tokens_per_request"],
                                  "temperature": project["generation"]["temperature"],
                                  "stream": False, "return_tokens": True}).encode("utf-8")
            request = urllib.request.Request(config["completion_url"], payload,
                                             {"Content-Type": "application/json"})
            request_start_ns = time.monotonic_ns()
            with urllib.request.urlopen(request, timeout=config.get("request_timeout_s", 30)) as response:
                result = json.load(response)
            request_end_ns = time.monotonic_ns()
            elapsed_ms = (request_end_ns - request_start_ns) / 1e6
            n = int(result.get("tokens_predicted", 0))
            events.emit("draft_request", "phone_server", {
                "request_index": count, "prompt_id": config.get("prompt_id", "demo-inline"),
                "requested_tokens": config["tokens_per_request"],
                "generated_tokens": n, "request_start_elapsed_ns": request_start_ns - start_ns,
                "request_end_elapsed_ns": request_end_ns - start_ns,
                "request_wall_ms": elapsed_ms,
                "phone_reported_draft_ms": result.get("timings", {}).get("predicted_ms"),
                "phone_reported_prefill_ms": result.get("timings", {}).get("prompt_ms"),
                "output_sha256": hashlib.sha256(result.get("content", "").encode("utf-8")).hexdigest(),
                "token_ids": result.get("tokens", [])
            }, sample_ns=request_end_ns)
            count += 1
            tokens += n
            request_ms_total += elapsed_ms
        stop.set()
        thread.join(timeout=5)
        if telemetry_error:
            raise RuntimeError(f"Telemetry stopped: {telemetry_error[-1]}")
        if not readings:
            raise RuntimeError("No phone telemetry captured")
        with (directory / "phone_telemetry.csv").open("w", newline="", encoding="utf-8") as stream:
            columns = [key for key in readings[0] if key != "ppm_user_cap_readback"]
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(readings)
        reason = guard_reasons[-1] if guard_reasons else "duration_or_request_limit"
        summary = {"mode": "phone_draft", "requests": count, "valid_tokens": tokens,
                   "total_request_ms": request_ms_total,
                   "amortized_ms_per_token": request_ms_total / tokens if tokens else None,
                   "max_cpu_temp_c": max(r["cpu_temp_c"] for r in readings),
                   "max_battery_temp_c": max(r["battery_temp_c"] for r in readings),
                   "stop_reason": reason, "schema_version": 1}
        write_json(directory / "summary.json", summary)
        if config.get("postprocess_run"):
            module_name, function_name = config["postprocess_run"].split(":", 1)
            getattr(importlib.import_module(module_name), function_name)(directory)
        state = "STOPPED" if guard_reasons else ("PLOTTED" if config.get("postprocess_run") else "SAVED")
        return summary
    except Exception as exc:
        error = str(exc)
        events.emit("run_error", "controller", {"message": error})
        raise
    finally:
        stop.set()
        if caps_applied:
            try:
                clear_caps(adb_path, serial=serial)
                events.emit("frequency_clear", "controller", {})
            except Exception as exc:
                error = f"{error or ''}; frequency cleanup failed: {exc}"
                state = "FAILED"
                events.emit("cleanup_error", "controller", {"message": str(exc)})
        events.emit("run_end", "controller", {"state": state, "reason": reason, "error": error})
        events.close()
        write_json(directory / "status.json", {"state": state, "started_utc": started_utc,
                   "finished_utc": datetime.now(timezone.utc).isoformat(), "reason": reason, "error": error})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(json.dumps(run(config, args.run_id), ensure_ascii=False))


if __name__ == "__main__":
    main()
