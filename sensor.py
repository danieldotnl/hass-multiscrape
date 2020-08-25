"""Support for RESTful API sensors."""
import logging
from xml.parsers.expat import ExpatError

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import xmltodict
import asyncio
import aiohttp
import async_timeout
import sys 
from bs4 import BeautifulSoup
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_AUTHENTICATION, CONF_FORCE_UPDATE,
                                 CONF_HEADERS, CONF_METHOD, CONF_NAME,
                                 CONF_PASSWORD, CONF_PAYLOAD, CONF_RESOURCE,
                                 CONF_RESOURCE_TEMPLATE, CONF_TIMEOUT,
                                 CONF_UNIT_OF_MEASUREMENT, CONF_USERNAME,
                                 CONF_VALUE_TEMPLATE, CONF_VERIFY_SSL,
                                 HTTP_BASIC_AUTHENTICATION,
                                 HTTP_DIGEST_AUTHENTICATION)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DEFAULT_METHOD = "GET"
DEFAULT_NAME = "Multiscrape Sensor"
DEFAULT_VERIFY_SSL = True
DEFAULT_FORCE_UPDATE = False
DEFAULT_TIMEOUT = 10
DEFAULT_PARSER = "lxml"

CONF_SELECTORS = "selectors"
CONF_ATTR = "attribute"
CONF_SELECT = "select"
CONF_INDEX = "index"
CONF_PARSER = "parser"

CONF_SELECTORS = "selectors"
METHODS = ["POST", "GET"]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Exclusive(CONF_RESOURCE, CONF_RESOURCE): cv.url,
        vol.Exclusive(CONF_RESOURCE_TEMPLATE, CONF_RESOURCE): cv.template,
        vol.Optional(CONF_AUTHENTICATION): vol.In(
            [HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]
        ),
        vol.Optional(CONF_HEADERS): vol.Schema({cv.string: cv.string}),
        vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): vol.In(METHODS),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PAYLOAD): cv.string,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
        vol.Optional(CONF_FORCE_UPDATE, default=DEFAULT_FORCE_UPDATE): cv.boolean,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_PARSER, default=DEFAULT_PARSER): cv.string,
    }
)

SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SELECT): cv.string,
        vol.Optional(CONF_ATTR): cv.string,
        vol.Optional(CONF_INDEX, default=0): cv.positive_int,
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_SELECTORS): cv.schema_with_slug_keys(SENSOR_SCHEMA)}
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Multiscrape sensor."""
    name = config.get(CONF_NAME)
    resource = config.get(CONF_RESOURCE)
    resource_template = config.get(CONF_RESOURCE_TEMPLATE)
    method = config.get(CONF_METHOD)
    payload = config.get(CONF_PAYLOAD)
    verify_ssl = config.get(CONF_VERIFY_SSL)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    headers = config.get(CONF_HEADERS)
    unit = config.get(CONF_UNIT_OF_MEASUREMENT)
    value_template = config.get(CONF_VALUE_TEMPLATE)
    selectors = config.get(CONF_SELECTORS)
    force_update = config.get(CONF_FORCE_UPDATE)
    timeout = config.get(CONF_TIMEOUT)
    parser = config.get(CONF_PARSER)

    if value_template is not None:
        value_template.hass = hass

    if resource_template is not None:
        resource_template.hass = hass
        resource = resource_template.async_render()
 
    # Must update the sensor now (including fetching the rest resource) to
    # ensure it's updating its state.  
    _httpClient = HttpClient(hass, resource, username, password, headers, verify_ssl, method, timeout)
    response = await _httpClient.async_request()
        
    # if response is None or (response.status // 100) in [4, 5]:
    #     _LOGGER.error("Error received: %s", await response.read())
    #     raise PlatformNotReady
    
    async_add_entities(
        [
            MultiscrapeSensor(
                hass,
                _httpClient,
                name,
                unit,
                value_template,
                selectors,
                force_update,
                parser,
            )
        ],
        True,
    )


class MultiscrapeSensor(Entity):
    """Implementation of the Multiscrape sensor."""

    def __init__(
        self,
        hass,
        httpClient,
        name,
        unit_of_measurement,
        value_template,
        selectors,
        force_update,
        parser,
    ):
        """Initialize the sensor."""
        self._hass = hass
        self._httpClient = httpClient
        self._name = name
        self._state = None
        self._unit_of_measurement = unit_of_measurement
        self._value_template = value_template
        self._selectors = selectors
        self._attributes = None
        self._force_update = force_update
        self._parser = parser

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def available(self):
        """Return if the sensor data are available."""
        return True

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def force_update(self):
        """Force update."""
        return self._force_update
    
    async def async_update(self):

        try:
            response = await self._httpClient.async_request()
        except:
            e = sys.exc_info()[0]
            _LOGGER.error(e)
            _LOGGER.error("Unable to retrieve data for %s", self._name)
        
        if response is None:
            _LOGGER.error("Unable to retrieve data for %s", self._name)
            return
            
        #_LOGGER.debug("Data fetched from resource: %s", response)
        
        if self._selectors:
        
            result = BeautifulSoup(response, self._parser)
            result.prettify()
            _LOGGER.debug("Data parsed by BeautifulSoup: %s", result)
        
            self._attributes = {}
            if response:
            
                for device, device_config in self._selectors.items():
                    name = device_config.get(CONF_NAME)
                    select = device_config.get(CONF_SELECT)
                    attr = device_config.get(CONF_ATTR)
                    index = device_config.get(CONF_INDEX)
                    value_template = device_config.get(CONF_VALUE_TEMPLATE)
                    unit = device_config.get(CONF_UNIT_OF_MEASUREMENT)
                    
                    try:
                        if attr is not None:
                            value = result.select(select)[index][attr]
                        else:
                            tag = result.select(select)[index]
                            if tag.name in ("style", "script", "template"):
                                value = tag.string
                            else:
                                value = tag.text
                        
                        _LOGGER.debug("Sensor %s selected: %s", name, value)
                    except IndexError as e:
                        _LOGGER.error("Sensor %s was unable to extract data from HTML", name)
                        _LOGGER.debug("Exception: %s", e)
                        continue

                    if value_template is not None:
                    
                        if value_template is not None:
                            value_template.hass = self._hass

                        try:
                            self._attributes[name] = value_template.async_render_with_possible_json_value(
                                value, None
                            )
                        except:
                            e = sys.exc_info()[0]
                            _LOGGER.error(e)
                        
                    else:
                        self._attributes[name] = value

        self._state = "None"

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes


class HttpClient:
    """Class for handling the data retrieval."""

    def __init__(
        self,
        hass, 
        url: str, 
        username: str = None,   
        password: str = None, 
        headers: str = None,
        verify_ssl: bool = True, 
        method: str ='GET', 
        timeout=DEFAULT_TIMEOUT
    ):
        """Initialize the data object."""
        self._hass = hass
        self.method = method
        self.url = url
        self.username = username
        self.password = password
        self.headers = headers
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.headers = headers

        self._session = async_get_clientsession(hass)

        self._auth = None
        if self.username and self.password:
            self._auth = aiohttp.BasicAuth(self.username, self.password)

    async def async_request(
        self,         
        data=None):
        """Get the latest data from the url with provided method."""

        try:
            with async_timeout.timeout(self.timeout):
                async with self._session.request(
                    self.method,
                    self.url,
                    auth=self._auth,
                    data=data,
                    headers=self.headers,
                    ssl=self.verify_ssl,
                ) as response:
                    return await response.text()

        except asyncio.TimeoutError as exception:
            _LOGGER.error("Timeout occurred while connecting to %s", self.url)
        except (aiohttp.ClientError, socket.gaierror) as exception:
            _LOGGER.error("Error occurred while communicating with %s", self.url)