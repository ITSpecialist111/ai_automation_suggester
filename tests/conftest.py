"""Lightweight stubs for coordinator unit tests without a Home Assistant runtime."""

from __future__ import annotations

import sys
import types
from pathlib import Path


def _install_homeassistant_stubs() -> None:
    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    persistent_notification = types.ModuleType("homeassistant.components.persistent_notification")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    area_registry = types.ModuleType("homeassistant.helpers.area_registry")
    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
    storage = types.ModuleType("homeassistant.helpers.storage")
    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class HomeAssistant:
        pass

    class DataUpdateCoordinator:
        def __init__(self, hass, logger, *, config_entry=None, name, update_interval=None):
            self.hass = hass
            self.logger = logger
            self.config_entry = config_entry
            self.name = name
            self.update_interval = update_interval
            self.data = None
            self.last_update_success = True

        async def async_request_refresh(self):
            self.data = await self._async_update_data()

        async def async_refresh(self):
            self.data = await self._async_update_data()

    class Store:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, version, key):
            self.data = None

        async def async_load(self):
            return self.data

        async def async_save(self, data):
            self.data = data

    core.HomeAssistant = HomeAssistant
    aiohttp_client.async_get_clientsession = lambda hass: hass.session
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    storage.Store = Store
    area_registry.AreaRegistry = object
    area_registry.async_get = lambda hass: None
    device_registry.DeviceRegistry = object
    device_registry.async_get = lambda hass: None
    entity_registry.EntityRegistry = object
    entity_registry.async_get = lambda hass: None

    components.persistent_notification = persistent_notification
    helpers.area_registry = area_registry
    helpers.device_registry = device_registry
    helpers.entity_registry = entity_registry
    homeassistant.components = components
    homeassistant.core = core
    homeassistant.helpers = helpers

    modules = {
        "homeassistant": homeassistant,
        "homeassistant.components": components,
        "homeassistant.components.persistent_notification": persistent_notification,
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.area_registry": area_registry,
        "homeassistant.helpers.device_registry": device_registry,
        "homeassistant.helpers.entity_registry": entity_registry,
        "homeassistant.helpers.aiohttp_client": aiohttp_client,
        "homeassistant.helpers.storage": storage,
        "homeassistant.helpers.update_coordinator": update_coordinator,
    }
    for name, module in modules.items():
        sys.modules.setdefault(name, module)


if "homeassistant" not in sys.modules:
    _install_homeassistant_stubs()


PACKAGE_NAME = "custom_components.ai_automation_suggester"
PACKAGE_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "ai_automation_suggester"
custom_components_package = types.ModuleType("custom_components")
custom_components_package.__path__ = [str(PACKAGE_PATH.parent)]
integration_package = types.ModuleType(PACKAGE_NAME)
integration_package.__path__ = [str(PACKAGE_PATH)]
sys.modules.setdefault("custom_components", custom_components_package)
sys.modules.setdefault(PACKAGE_NAME, integration_package)
