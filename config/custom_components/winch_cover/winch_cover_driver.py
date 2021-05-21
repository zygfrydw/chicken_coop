from typing import Callable, Optional
from . import setup_input, setup_output, read_input, write_output, edge_detect, PullMode, EdgeType
import logging
from enum import Enum
from threading import Condition
import asyncio
_LOGGER = logging.getLogger(__package__)


class PositionSensor:
    sensor_pin: int
    pull_mode: PullMode
    on_position_reached: Optional[Callable[[bool], None]]

    def __init__(self, sensor_pin: int, pull_mode: PullMode):
        self.sensor_pin = sensor_pin
        self.pull_mode = pull_mode
        self.on_position_reached = None
        setup_input(self.sensor_pin, self.pull_mode)
        edge_detect(self.sensor_pin, self.event_callback, 50, EdgeType.BOTH)

    def set_on_position_reached(self, callback: Callable[[], None]):
        self.on_position_reached = callback

    def event_callback(self, port):
        if port != self.sensor_pin:
            return

        state = read_input(self.sensor_pin)

        _LOGGER.warning(f'GPIO INPUT | Port: {port}; state: {state}')
        if self.on_position_reached is not None:
            self.on_position_reached(state)

    def get_state(self) -> bool:
        return read_input(self.sensor_pin)


class Encoder:
    def __init__(self, led_pin: int, detector_pin: int):
        """
        Represents an encoder detecting if engine is rotating
        :param led_pin: led input number
        :param detector_pin: detector pin number
        """
        self.in_pin_number = detector_pin
        self.out_pin_number = led_pin

    def detect(self, on_edge):
        pass

    def turn_off(self):
        pass


class Motor:
    def __init__(self, dir_pin: int, pwm_pin: int, fault_pin: int):
        self.pwm_pin_number = pwm_pin
        self.dir_pin_number = dir_pin
        setup_output(self.pwm_pin_number)
        setup_output(self.dir_pin_number)
        setup_input(fault_pin, PullMode.OFF)
        write_output(self.dir_pin_number, 0)
        write_output(self.pwm_pin_number, 0)

    def run_forward(self):
        write_output(self.dir_pin_number, 1)
        # write_output(self.pwm_pin_number, 1)

    def run_backward(self):
        write_output(self.dir_pin_number, 0)
        # write_output(self.pwm_pin_number, 1)

    def stop(self):
        write_output(self.pwm_pin_number, 0)


class LED:
    def __init__(self, pin: int):
        self.pin = pin
        setup_output(pin)
        self.turn_off()

    def turn_off(self):
        write_output(self.pin, 0)

    def turn_on(self):
        write_output(self.pin, 1)


class WinchState(Enum):
    OPENED = 1,
    OPENING = 2,
    CLOSING = 3,
    CLOSED = 4,
    ERROR = 5


class WinchCoverDriver:
    _red_led: LED
    _green_led: LED
    _closing_timeout: float
    _opening_timeout: float
    _encoder: Optional[Encoder]
    _bottom_sensor: PositionSensor
    _upper_sensor: PositionSensor
    _motor: Motor
    _is_working: bool
    _state: WinchState
    _target_state: WinchState
    _on_state_changed: Optional[Callable[[], None]]

    def __init__(self,
                 motor: Motor,
                 upper_sensor: PositionSensor,
                 bottom_sensor: PositionSensor,
                 green_led: LED,
                 red_led: LED,
                 encoder: Encoder = None,
                 opening_timeout: float = 5,
                 closing_timeout: float = 5):

        self._red_led = red_led
        self._green_led = green_led
        self._closing_timeout = closing_timeout
        self._opening_timeout = opening_timeout
        self._encoder = encoder
        self._bottom_sensor = bottom_sensor
        self._bottom_sensor.set_on_position_reached(self.bottom_position_reached)
        self._upper_sensor = upper_sensor
        self._upper_sensor.set_on_position_reached(self.upper_position_reached)
        self._motor = motor
        self._is_working = False
        if self._upper_sensor.get_state():
            self._state = WinchState.OPENED
        elif self._bottom_sensor.get_state():
            self._state = WinchState.CLOSED
        else:
            self._state = WinchState.CLOSING
        self._target_state = WinchState.OPENED
        self.cond = asyncio.Condition()

    async def open_cover(self):
        _LOGGER.warning("Open cover driver!")
        async with self.cond:
            self._is_working = True
            self.state = WinchState.OPENING
            self._green_led.turn_on()
            self._motor.run_forward()
            _LOGGER.warning("Entering wait")
            wait_res = await asyncio.wait_for(self.cond.wait(), self._opening_timeout)
            self._motor.stop()
            self._green_led.turn_off()
            self._is_working = False
            if wait_res:
                _LOGGER.warning("Open cover finished!")
            else:
                _LOGGER.error("Cover was not opened within given time limit!")
                self.on_error()

    async def close_cover(self):
        _LOGGER.warning("Close cover driver!")
        # async with self.cond:
        async with self.cond:
            self._is_working = True
            self.state = WinchState.CLOSING
            self._motor.run_backward()
            _LOGGER.warning("Entering wait")
            wait_res = await asyncio.wait_for(self.cond.wait(), self._closing_timeout)
            self._motor.stop()
            self._green_led.turn_off()
            self._is_working = False
            if wait_res:
                _LOGGER.warning("Close cover finished!")
            else:
                _LOGGER.error("Close was not closed within given time limit!")
                self.on_error()

    def stop(self):
        self.cond.notify_all()

    def bottom_position_reached(self, state: bool):
        if state == 0:
            with self.cond:
                self.state = WinchState.CLOSED
                self.cond.notify_all()

    def upper_position_reached(self, state: bool):
        if state == 0:
            with self.cond:
                self.state = WinchState.OPENED
                self.cond.notify_all()

    def on_error(self):
        self._red_led.turn_on()

    @property
    def state(self):
        # asyncio with self.cond:
        return self._state

    @state.setter
    def state(self, value):
        # TODO: should I add sychronization here?
        if self._state != value:
            self._state = value
            if self._on_state_changed is not None:
                self._on_state_changed()

    def set_on_state_changed(self, on_state_changed: Callable[[], None]):
        self._on_state_changed = on_state_changed
