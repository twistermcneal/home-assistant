"""
Support for knx covers.

For more details about this platform, please refer to the documentation at ???

"""
import logging
import subprocess
import voluptuous as vol

from homeassistant.helpers.event import track_utc_time_change
from homeassistant.components.knx import (KNXConfig, KNXMultiAddressDevice)
from homeassistant.components.cover import (CoverDevice, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_NAME, CONF_FRIENDLY_NAME)
import homeassistant.helpers.config_validation as cv

CONF_SHORT_ADDRESS = 'short_address'
CONF_LONG_ADDRESS = 'long_address'
CONF_TIME_UP_DOWN = 'time_up_down'

DEFAULT_TIME_UP_DOWN = 5
DEFAULT_NAME = 'KNX Cover'
DEPENDENCIES = ['knx']

_LOGGER = logging.getLogger(__name__)

COVER_SCHEMA = vol.Schema({
	vol.Required(CONF_SHORT_ADDRESS): cv.string,
	vol.Required(CONF_LONG_ADDRESS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TIME_UP_DOWN, default=DEFAULT_TIME_UP_DOWN): int,
    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
})



def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the KNX Cover platform.""" 
    add_devices([KNXCover(hass, config)])
	
	

class KNXCover(KNXMultiAddressDevice, CoverDevice):
    """Representation of a KNX Cover device."""
    
    def __init__(self, hass, config):
        """Initialize the cover."""
        self.hass = hass
        self._config = config
        self._position = 50
        self._set_position = None
        self._set_tilt_position = None
        self._tilt_position = 50
        self._closing = True
        self._closing_tilt = True
        self._unsub_listener_cover = None
        self._unsub_listener_cover_tilt = None
        """Initialize super class"""
        super(KNXCover, self).__init__(hass, KNXConfig(config), ['short', 'long'])
       
    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._position

    @property
    def current_cover_tilt_position(self):
        """Return the current tilt position of the cover."""
        return self._tilt_position

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self._position is not None:
            if self.current_cover_position > 0:
                return False
            else:
                return True
        else:
            return None

    def close_cover(self, **kwargs):
        """Close the cover."""
        """
        This sends a value 1 to the group address of the device
        """     
        self.set_value('long', 1)
        if self._position in (0, None):
            return

        self._listen_cover()
        self._closing = True

    def close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        self.set_value('short', 1)
        if self._tilt_position in (0, None):
            return
        
        self._listen_cover_tilt()
        self._closing_tilt = True
        
        
       
    def open_cover(self, **kwargs):
        """Open the cover."""
        """
        This sends a value 0 to the group address of the device
        """       
        self.set_value('long', 0)
        if self._position in (100, None):
            return

        self._listen_cover()
        self._closing = False

    def open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        self.set_value('short', 0)
        if self._tilt_position in (100, None):
            return
        
        self._listen_cover_tilt()
        self._closing_tilt = False
        
    def set_cover_position(self, position, **kwargs):
        """Move the cover to a specific position."""
        self._set_position = round(position, -1)
        if self._position == position:
            return

        self._listen_cover()
        self._closing = position < self._position

    def set_cover_tilt_position(self, tilt_position, **kwargs):
        """Move the cover til to a specific position."""
        self._set_tilt_position = round(tilt_position, -1)
        if self._tilt_position == tilt_position:
            return

        self._listen_cover_tilt()
        self._closing_tilt = tilt_position < self._tilt_position

    def stop_cover(self, **kwargs):
        """Stop the cover."""	
        self.set_value('short', 1)		
        if self._position is None:
            return
        if self._unsub_listener_cover is not None:
            self._unsub_listener_cover()
            self._unsub_listener_cover = None
            self._set_position = None
			        
    def stop_cover_tilt(self, **kwargs):
        """Stop the cover tilt."""
        self.set_value('short', 1)
        if self._tilt_position is None:
            return

        if self._unsub_listener_cover_tilt is not None:
            self._unsub_listener_cover_tilt()
            self._unsub_listener_cover_tilt = None
            self._set_tilt_position = None
        
    def _listen_cover(self):
        """Listen for changes in cover."""
        if self._unsub_listener_cover is None:
            self._unsub_listener_cover = track_utc_time_change(
                self.hass, self._time_changed_cover)

    def _time_changed_cover(self, now):
        """Track time changes."""
        _LOGGER.debug("Config Time: %s", self._config.config.get(CONF_TIME_UP_DOWN))
        if self._config.config.get(CONF_TIME_UP_DOWN) is None:
            time_up_down = 100/DEFAULT_TIME_UP_DOWN
        else:
            time_up_down = 100/self._config.config.get(CONF_TIME_UP_DOWN)
			
        if self._closing:
            self._position -= time_up_down
        else:
            self._position += time_up_down
        if self._position > 100:
           self._position = 100
        if self._position < 0:
           self._position = 0
        if self._position in (100, 0, self._set_position):
            self.stop_cover()
        self.update_ha_state()

    def _listen_cover_tilt(self):
        """Listen for changes in cover tilt."""
        if self._unsub_listener_cover_tilt is None:
            self._unsub_listener_cover_tilt = track_utc_time_change(
                self.hass, self._time_changed_cover_tilt)

    def _time_changed_cover_tilt(self, now):
        """Track time changes."""
        if self._closing_tilt:
            self._tilt_position -= 10
        else:
            self._tilt_position += 10

        if self._tilt_position in (100, 0, self._set_tilt_position):
            self.stop_cover_tilt()

        self.update_ha_state()
		
    def update(self):
        """Update KNX climate."""
		
        if self.dataChanged == True:
          if self._unsub_listener_cover is None:
            if self.value('long') == [1]:
              self._position = 0			   
            if self.value('long') == [0]:
              self._position = 100
          if self._unsub_listener_cover_tilt is None:
            if self.value('short') == [1]:
              self._tilt_position = 0			   
            if self.value('short') == [0]:
              self._tilt_position = 100
			          
          self.dataChanged = False            
        #super().update()
