"""Read-only phone telemetry and health checks through ADB."""
import json
import subprocess
import urllib.request


def adb(adb_path, shell, timeout=10):
    result = subprocess.run([adb_path, "shell", "su", "-c", "'" + shell + "'"], capture_output=True,
                            text=True, timeout=timeout, check=True)
    return result.stdout.strip()


def sample(adb_path):
    paths = [
        "/sys/class/thermal/thermal_zone4/temp",
        "/sys/class/power_supply/battery/temp",
        "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq",
        "/sys/devices/system/cpu/cpufreq/policy4/scaling_cur_freq",
        "/sys/devices/system/cpu/cpufreq/policy7/scaling_cur_freq",
    ]
    values = adb(adb_path, "; ".join(f"cat {p}" for p in paths)).splitlines()
    if len(values) != 5:
        raise RuntimeError(f"Expected five telemetry values, got {values!r}")
    return {
        "cpu_temp_c": int(values[0]) / 1000,
        "battery_temp_c": int(values[1]) / 10,
        "freq_little_khz": int(values[2]),
        "freq_mid_khz": int(values[3]),
        "freq_big_khz": int(values[4]),
    }


def set_caps(adb_path, caps):
    if caps is None:
        return
    if len(caps) != 3 or any(not isinstance(v, int) or v <= 0 for v in caps):
        raise ValueError("frequency_caps_khz must contain three positive integer OPP values")
    node = "/proc/ppm/policy/userlimit_max_cpu_freq"
    existing = adb(adb_path, f"cat {node}").splitlines()
    if len(existing) != 3 or any("max_freq_idx = -1" not in line for line in existing):
        raise RuntimeError("Another PPM user cap is active; refusing to overwrite it")
    for policy, value in zip((0, 4, 7), caps):
        available = {int(part) for part in adb(adb_path, f"cat /sys/devices/system/cpu/cpufreq/policy{policy}/scaling_available_frequencies").split()}
        if value not in available:
            raise ValueError(f"{value} is not a supported OPP for CPU policy {policy}")
    applied = []
    try:
        for cluster, value in enumerate(caps):
            adb(adb_path, f"echo '{cluster} {value}' > {node}")
            applied.append(cluster)
    except Exception:
        for cluster in applied:
            adb(adb_path, f"echo '{cluster} -1' > {node}")
        raise


def clear_caps(adb_path):
    node = "/proc/ppm/policy/userlimit_max_cpu_freq"
    for cluster in range(3):
        adb(adb_path, f"echo '{cluster} -1' > {node}")


def health(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.load(response)
    if data.get("status") != "ok":
        raise RuntimeError(f"Phone server unhealthy: {data!r}")
