"""Wait for a sustained cool starting condition before the next run."""
import time
from .phone import adb, sample


def wait_for_cool(adb_path, gate, on_sample=lambda _: None):
    deadline = time.monotonic() + gate["max_wait_s"]
    good_since = None
    while time.monotonic() < deadline:
        reading = sample(adb_path)
        on_sample(reading)
        cool = (reading["cpu_temp_c"] <= gate["cpu_temp_max_c"] and
                reading["battery_temp_c"] <= gate["battery_temp_max_c"])
        if gate.get("thermal_cap_must_be_clear", True):
            cool = cool and "PPM thermal activate = 0" in adb(adb_path, "cat /proc/ppm/policy/thermal_limit")
        if cool:
            good_since = good_since or time.monotonic()
            if time.monotonic() - good_since >= gate["stable_hold_s"]:
                return reading
        else:
            good_since = None
        time.sleep(gate.get("poll_s", 2))
    raise TimeoutError("Phone did not cool to the configured starting temperatures")
