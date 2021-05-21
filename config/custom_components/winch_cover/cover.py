from time import sleep

import voluptuous as vol
import logging
from homeassistant.components.cover import PLATFORM_SCHEMA, CoverEntity, SUPPORT_OPEN, SUPPORT_CLOSE, DEVICE_CLASS_SHADE
from homeassistant.const import CONF_COVERS, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.exceptions import HomeAssistantError
from .winch_cover_driver import *

CONF_MOTOR_DIR = "dir_pin"
CONF_MOTOR_PWM = "pwm_pin"
CONF_MOTOR_FAULT = "fault_pin"
CONF_RED_LED = "red_led_pin"
CONF_GREEN_LED = "green_led_pin"
CONF_ENCODER_LED = "encoder_led_pin"
CONF_ENCODER_DETECTOR = "encoder_detector_pin"
CONF_POSITION_UPPER = "pos_upper_pin"
CONF_POSITION_UPPER_MODE = "pos_upper_mode"
CONF_POSITION_BOTTOM = "pos_bottom_pin"
CONF_POSITION_BOTTOM_MODE = "pos_bottom_mode"

DEFAULT_STATE_PULL_MODE = "UP"

_LOGGER = logging.getLogger(__package__)

_COVERS_SCHEMA = vol.All(
    cv.ensure_list,
    [
        vol.Schema(
            {
                CONF_NAME: cv.string,
                CONF_MOTOR_DIR: cv.positive_int,
                CONF_MOTOR_PWM: cv.positive_int,
                CONF_MOTOR_FAULT: cv.positive_int,
                CONF_RED_LED: cv.positive_int,
                CONF_GREEN_LED: cv.positive_int,
                CONF_ENCODER_LED: cv.positive_int,
                CONF_ENCODER_DETECTOR: cv.positive_int,
                CONF_POSITION_UPPER: cv.positive_int,
                # CONF_POSITION_UPPER_MODE: cv.positive_int,
                CONF_POSITION_BOTTOM: cv.positive_int,
                # CONF_POSITION_BOTTOM_MODE: cv.positive_int,
            }
        )
    ],
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_COVERS): _COVERS_SCHEMA,
        # vol.Optional(CONF_STATE_PULL_MODE, default=DEFAULT_STATE_PULL_MODE): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the RPi cover platform."""
    _LOGGER.warning("Setup WIESZOK platform")
    covers_conf = config.get(CONF_COVERS)
    # pull_mode = config.get(CONF_STATE_PULL_MODE)
    covers = []
    for cover in covers_conf:
        motor = Motor(dir_pin=cover[CONF_MOTOR_DIR], pwm_pin=cover[CONF_MOTOR_PWM], fault_pin=cover[CONF_MOTOR_FAULT])
        upper_sensor = PositionSensor(sensor_pin=cover[CONF_POSITION_UPPER], pull_mode=PullMode.UP)
        bottom_sensor = PositionSensor(sensor_pin=cover[CONF_POSITION_BOTTOM], pull_mode=PullMode.UP)
        green_led = LED(cover[CONF_GREEN_LED])
        red_led = LED(cover[CONF_RED_LED])
        covers.append(
            WinchCover(
                cover[CONF_NAME],
                WinchCoverDriver(motor, upper_sensor, bottom_sensor, green_led, red_led)
            )
        )
    async_add_entities(covers)


class GateBusy(HomeAssistantError):
    """Wait for registration to the HomematicIP Cloud server."""


class WinchCover(CoverEntity):
    """Representation of a Raspberry GPIO cover."""

    def __init__(
            self,
            name,
            driver: WinchCoverDriver,
    ):
        """Initialize the cover."""
        self._name = name
        self._is_closed = False
        self._is_closing = False
        self._is_opening = False
        self._driver = driver
        self._driver.set_on_state_changed(lambda: self.async_write_ha_state())

    @property
    def name(self):
        """Return the name of the cover if any."""
        return self._name

    async def async_update(self):
        """Update the state of the cover."""
        _LOGGER.warning("Update!")
        # self._state = rpi_gpio.read_input(self._state_pin)

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def is_closed(self):
        """Return true if cover is closed."""
        _LOGGER.warning("Is closed")
        return self._driver.state == WinchState.CLOSED



    @property
    def is_closing(self):
        """Return true if cover is closed."""
        _LOGGER.warning("Is closing")
        return self._driver.state == WinchState.CLOSING

    @property
    def is_opening(self):
        """Return true if cover is closed."""
        _LOGGER.warning("Is opening")
        return self._driver.state == WinchState.OPENING

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE

    # check!!!
    @property
    def device_class(self):
        """Flag supported features."""
        return DEVICE_CLASS_SHADE

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.warning("Closing cover")
        if self.is_opening or self.is_closing:
            raise GateBusy("Gate is busy!")
        if not self.is_closed:
            # await self.hass.async_add_executor_job(self._driver.close_cover)
            await self._driver.close_cover()

    async def async_stop_cover(self, **kwargs):
        _LOGGER.warning("Stopping cover")
        await self.hass.async_add_executor_job(self._driver.stop)

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.warning("Opening cover")
        if self.is_opening or self.is_closing:
            raise GateBusy("Gate is busy!")
        if self.is_closed:
            # await self.hass.async_add_executor_job(self._driver.open_cover)
            await self._driver.open_cover()

