"""Sensor platform for FreshTomato router."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import RouterStats
from .const import DOMAIN
from .coordinator import FreshTomatoCoordinator


@dataclass(frozen=True)
class FreshTomatoSensorEntityDescription(SensorEntityDescription):
    """Describes a FreshTomato sensor."""

    value_fn: Callable[[RouterStats], float | int | str | None] = lambda _: None


def _iface_rx(iface: str) -> Callable[[RouterStats], int | None]:
    return lambda s: s.net_rx.get(iface)


def _iface_tx(iface: str) -> Callable[[RouterStats], int | None]:
    return lambda s: s.net_tx.get(iface)


SENSOR_DESCRIPTIONS: tuple[FreshTomatoSensorEntityDescription, ...] = (
    # --- WAN bandwidth ---
    FreshTomatoSensorEntityDescription(
        key="wan_rx_bytes",
        name="WAN Download",
        icon="mdi:download-network",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_iface_rx("vlan2"),
    ),
    FreshTomatoSensorEntityDescription(
        key="wan_tx_bytes",
        name="WAN Upload",
        icon="mdi:upload-network",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_iface_tx("vlan2"),
    ),
    # --- LAN bandwidth ---
    FreshTomatoSensorEntityDescription(
        key="lan_rx_bytes",
        name="LAN RX",
        icon="mdi:lan-connect",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_iface_rx("br0"),
    ),
    FreshTomatoSensorEntityDescription(
        key="lan_tx_bytes",
        name="LAN TX",
        icon="mdi:lan-pending",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_iface_tx("br0"),
    ),
    # --- WiFi 2.4 GHz ---
    FreshTomatoSensorEntityDescription(
        key="wl0_rx_bytes",
        name="WiFi 2.4 GHz RX",
        icon="mdi:wifi-arrow-down",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_iface_rx("eth1"),
    ),
    FreshTomatoSensorEntityDescription(
        key="wl0_tx_bytes",
        name="WiFi 2.4 GHz TX",
        icon="mdi:wifi-arrow-up",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_iface_tx("eth1"),
    ),
    # --- WiFi 5 GHz ---
    FreshTomatoSensorEntityDescription(
        key="wl1_rx_bytes",
        name="WiFi 5 GHz RX",
        icon="mdi:wifi-arrow-down",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_iface_rx("eth2"),
    ),
    FreshTomatoSensorEntityDescription(
        key="wl1_tx_bytes",
        name="WiFi 5 GHz TX",
        icon="mdi:wifi-arrow-up",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_iface_tx("eth2"),
    ),
    # --- System ---
    FreshTomatoSensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.uptime,
    ),
    FreshTomatoSensorEntityDescription(
        key="load_1m",
        name="Load Average 1m",
        icon="mdi:chart-line",
        native_unit_of_measurement=None,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.load_1,
    ),
    FreshTomatoSensorEntityDescription(
        key="load_5m",
        name="Load Average 5m",
        icon="mdi:chart-line",
        native_unit_of_measurement=None,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.load_5,
    ),
    FreshTomatoSensorEntityDescription(
        key="load_15m",
        name="Load Average 15m",
        icon="mdi:chart-line",
        native_unit_of_measurement=None,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.load_15,
    ),
    FreshTomatoSensorEntityDescription(
        key="mem_total",
        name="Memory Total",
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.KILOBYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.mem_total,
    ),
    FreshTomatoSensorEntityDescription(
        key="mem_free",
        name="Memory Free",
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.KILOBYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.mem_free,
    ),
    FreshTomatoSensorEntityDescription(
        key="mem_used",
        name="Memory Used",
        icon="mdi:memory",
        native_unit_of_measurement=UnitOfInformation.KILOBYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: (s.mem_total - s.mem_free) if s.mem_total else None,
    ),
    FreshTomatoSensorEntityDescription(
        key="connected_devices",
        name="Connected Devices",
        icon="mdi:devices",
        native_unit_of_measurement="devices",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: len(s.devices),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FreshTomato sensors."""
    coordinator: FreshTomatoCoordinator = hass.data[DOMAIN][entry.entry_id]
    host = entry.data[CONF_HOST]

    async_add_entities(
        FreshTomatoSensor(coordinator, description, host, entry.entry_id)
        for description in SENSOR_DESCRIPTIONS
    )


class FreshTomatoSensor(CoordinatorEntity[FreshTomatoCoordinator], SensorEntity):
    """A sensor entity for FreshTomato router data."""

    entity_description: FreshTomatoSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FreshTomatoCoordinator,
        description: FreshTomatoSensorEntityDescription,
        host: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._host = host
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"FreshTomato ({host})",
            manufacturer="FreshTomato",
            model="Broadcom Router",
            configuration_url=f"http://{host}",
        )

    @property
    def native_value(self) -> float | int | str | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
