"""Read-only phone telemetry and health checks through ADB."""
import json
import subprocess
import urllib.request


def connected_serial(adb_path, requested=None):
    result = subprocess.run([adb_path, "devices"], capture_output=True, text=True,
                            timeout=10, check=True)
    devices = [line.split()[0] for line in result.stdout.splitlines()[1:]
               if line.split() and line.split()[-1] == "device"]
    if requested:
        if requested not in devices:
            raise RuntimeError(f"ADB device {requested} is not connected")
        return requested
    if len(devices) != 1:
        raise RuntimeError(f"Expected exactly one ADB device, found {devices!r}; set adb_serial")
    return devices[0]


def forward_port(adb_path, serial, port):
    subprocess.run([adb_path, "-s", serial, "forward", f"tcp:{port}", f"tcp:{port}"],
                   capture_output=True, text=True, timeout=10, check=True)


def adb(adb_path, shell, timeout=10, serial=None):
    command = [adb_path]
    if serial:
        command += ["-s", serial]
    command += ["shell", "su", "-c", "'" + shell + "'"]
    result = subprocess.run(command, capture_output=True,
                            text=True, timeout=timeout, check=True)
    return result.stdout.strip()


def sample(adb_path, serial=None):
    paths = [
        "/sys/class/thermal/thermal_zone4/temp",
        "/sys/class/power_supply/battery/temp",
        "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq",
        "/sys/devices/system/cpu/cpufreq/policy4/scaling_cur_freq",
        "/sys/devices/system/cpu/cpufreq/policy7/scaling_cur_freq",
        "/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq",
        "/sys/devices/system/cpu/cpufreq/policy4/scaling_max_freq",
        "/sys/devices/system/cpu/cpufreq/policy7/scaling_max_freq",
        "/sys/class/power_supply/battery/status",
        "/sys/class/power_supply/usb/online",
        "/proc/ppm/policy/thermal_limit",
        "/proc/ppm/policy/userlimit_max_cpu_freq",
    ]
    values = adb(adb_path, "set -e; " + "; ".join(f"cat {p}" for p in paths), serial=serial).splitlines()
    if len(values) != 15:
        raise RuntimeError(f"Expected fifteen telemetry values, got {values!r}")
    return {
        "cpu_temp_c": int(values[0]) / 1000,
        "battery_temp_c": int(values[1]) / 10,
        "freq_little_khz": int(values[2]),
        "freq_mid_khz": int(values[3]),
        "freq_big_khz": int(values[4]),
        "policy_max_little_khz": int(values[5]),
        "policy_max_mid_khz": int(values[6]),
        "policy_max_big_khz": int(values[7]),
        "battery_status": values[8],
        "usb_online": int(values[9]),
        "thermal_limited_power": values[10],
        "thermal_active": "PPM thermal activate = 1" in values[11],
        "ppm_user_cap_readback": values[12:15],
    }


def set_caps(adb_path, caps, serial=None):
    if caps is None:
        return
    if len(caps) != 3 or any(not isinstance(v, int) or v <= 0 for v in caps):
        raise ValueError("frequency_caps_khz must contain three positive integer OPP values")
    node = "/proc/ppm/policy/userlimit_max_cpu_freq"
    existing = adb(adb_path, f"cat {node}", serial=serial).splitlines()
    if len(existing) != 3 or any("max_freq_idx = -1" not in line for line in existing):
        raise RuntimeError("Another PPM user cap is active; refusing to overwrite it")
    for policy, value in zip((0, 4, 7), caps):
        available = {int(part) for part in adb(adb_path, f"cat /sys/devices/system/cpu/cpufreq/policy{policy}/scaling_available_frequencies", serial=serial).split()}
        if value not in available:
            raise ValueError(f"{value} is not a supported OPP for CPU policy {policy}")
    applied = []
    try:
        for cluster, value in enumerate(caps):
            adb(adb_path, f"echo '{cluster} {value}' > {node}", serial=serial)
            applied.append(cluster)
    except Exception:
        for cluster in applied:
            adb(adb_path, f"echo '{cluster} -1' > {node}", serial=serial)
        raise


def clear_caps(adb_path, serial=None):
    node = "/proc/ppm/policy/userlimit_max_cpu_freq"
    for cluster in range(3):
        adb(adb_path, f"echo '{cluster} -1' > {node}", serial=serial)


def health(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.load(response)
    if data.get("status") != "ok":
        raise RuntimeError(f"Phone server unhealthy: {data!r}")
