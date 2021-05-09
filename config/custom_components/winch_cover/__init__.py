"""Support for controlling GPIO pins of a Raspberry Pi."""
from RPi import GPIO  # pylint: disable=import-error
from enum import Enum

from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP

DOMAIN = "rpi_gpio"
PLATFORMS = ["binary_sensor", "cover", "switch"]


def setup(hass, config):
    """Set up the Raspberry PI GPIO component."""

    def cleanup_gpio(event):
        """Stuff to do before stopping."""
        GPIO.cleanup()

    def prepare_gpio(event):
        """Stuff to do when Home Assistant starts."""
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, cleanup_gpio)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, prepare_gpio)
    GPIO.setmode(GPIO.BCM)
    return True


def setup_output(port):
    """Set up a GPIO as output."""
    GPIO.setup(port, GPIO.OUT)


class PullMode:
    UP = 1,
    DOWN = 2,
    OFF = 3


def setup_input(port, pull_mode: PullMode):
    """Set up a GPIO as input."""
    if pull_mode == PullMode.OFF:
        GPIO.setup(port, GPIO.IN, GPIO.PUD_OFF)
    elif pull_mode == PullMode.DOWN:
        GPIO.setup(port, GPIO.IN, GPIO.PUD_DOWN)
    elif pull_mode == PullMode.UP:
        GPIO.setup(port, GPIO.IN, GPIO.PUD_UP)
    else:
        raise ValueError(f'Unknown value for pull_mode: {pull_mode}')


def write_output(port, value):
    """Write a value to a GPIO."""
    GPIO.output(port, value)


def read_input(port):
    """Read a value from a GPIO."""
    return GPIO.input(port)


class EdgeType:
    RISING = 1,
    FALLING = 2,
    BOTH = 3


def edge_detect(port, event_callback, bounce, edge_type: EdgeType = EdgeType.BOTH):
    """Add detection for RISING and FALLING events."""
    if edge_type == EdgeType.RISING:
        GPIO.add_event_detect(port, GPIO.RISING, callback=event_callback, bouncetime=bounce)
    elif edge_type == EdgeType.FALLING:
        GPIO.add_event_detect(port, GPIO.FALLING, callback=event_callback, bouncetime=bounce)
    elif edge_type == EdgeType.BOTH:
        GPIO.add_event_detect(port, GPIO.BOTH, callback=event_callback, bouncetime=bounce)
    else:
        raise ValueError(f'Unknown value for edge_type: {edge_type}')
