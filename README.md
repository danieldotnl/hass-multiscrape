# HA MultiScrape custom component
This Home Assistant custom component can scrape multiple fields (using CSS selectors) from a single HTTP request (the existing scrape sensor can scrape a single field only).

It is based on both the existing [Rest sensor](https://www.home-assistant.io/integrations/rest/) and the [Scrape sensor](https://www.home-assistant.io/integrations/scrape).
The scraped fields are added as attributes on the sensor and using template sensors, you can see them as separate sensors.
Most properties of the Rest and Scrape sensor apply.

<a href="https://www.buymeacoffee.com/danieldotnl" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-blue.png" alt="Buy Me A Coffee" style="height: 51px !important;width: 217px !important;" ></a>


### Installation
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/danieldotnl/hass-multiscrape)

Via HACS as a custom repository (https://github.com/danieldotnl/hass-multiscrape) or install manually by copying the files in a new 'custom_components/multiscrape' directory.

### Example configuration

```yaml

  - platform: multiscrape
    name: home assistant scraper
    resource: https://www.home-assistant.io
    scan_interval: 30
    selectors:
      version:
        name: Current version
        select: '.current-version > h1:nth-child(1)'
        value_template: '{{ (value.split(":")[1]) }}'
      releasedate:
        name: Release date
        select: '.release-date'
```
### Roadmap
- create a separate sensor for each field instead of attributes
- make it async
