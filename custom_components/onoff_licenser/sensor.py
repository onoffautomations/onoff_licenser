"""Sensor platform for OnOff Licenser integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import platform
import subprocess

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the OnOff Licenser sensor platform."""
    async_add_entities(
        [
            PingSensor(hass, "8.8.8.8", "Google DNS"),
            PingSensor(hass, "api.onoffapi.com", "OnOff API"),
        ],
        True,
    )


class PingSensor(SensorEntity):
    """Representation of a ping sensor."""

    def __init__(self, hass: HomeAssistant, target: str, name: str) -> None:
        """Initialize the ping sensor."""
        self.hass = hass
        self._target = target
        self._attr_name = f"Ping {name}"
        self._attr_unique_id = f"onoff_licenser_ping_{target.replace('.', '_')}"
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = "ms"
        self._attr_icon = "mdi:network"

    async def async_update(self) -> None:
        """Update the sensor."""
        result = await self._async_ping()
        self._attr_native_value = result

    async def _async_ping(self) -> float | None:
        """Ping the target and return the response time in milliseconds."""
        try:
            # Determine the ping command based on the platform
            param = "-n" if platform.system().lower() == "windows" else "-c"

            # Run ping command
            command = ["ping", param, "1", self._target]

            result = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                # Parse the output to extract the ping time
                output = stdout.decode()

                # Parse ping time based on platform
                if platform.system().lower() == "windows":
                    # Windows format: "Average = XXms" or "time=XXms"
                    for line in output.split("\n"):
                        if "Average" in line or "time=" in line.lower():
                            if "Average" in line:
                                parts = line.split("=")
                                if len(parts) > 1:
                                    time_str = parts[-1].strip().replace("ms", "")
                                    return float(time_str)
                            elif "time=" in line.lower():
                                # Extract time=XXms
                                time_start = line.lower().find("time=") + 5
                                time_end = line.lower().find("ms", time_start)
                                if time_end > time_start:
                                    return float(line[time_start:time_end])
                else:
                    # Linux/Mac format: "time=XX.X ms"
                    for line in output.split("\n"):
                        if "time=" in line:
                            parts = line.split("time=")
                            if len(parts) > 1:
                                time_str = parts[1].split()[0]
                                return float(time_str)

                _LOGGER.warning("Could not parse ping output for %s", self._target)
                return None
            else:
                _LOGGER.error("Ping failed for %s: %s", self._target, stderr.decode())
                return None

        except Exception as err:
            _LOGGER.error("Error pinging %s: %s", self._target, err)
            return None
