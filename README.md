# Component ipx800v3 for Home Assistant

## Installation

### Manually

Copy `custom_components/ipx800v3` directory in `config/custom_components` in your Home Assistant deployment (you should have `*.py` python files in `config/custom_components/ipx800v3`).
Edit your `configuration.yml` according to the following example.

L'IPX800 V3 must be online and reachable during at the starting process of Home Assistant.
Ensure your IPX800 V3 is not overload with request from other tools.

## Deps

[pypix800v3 python package](https://github.com/Xavieto/pypx800v3_async) (should be install by Home assistant. If not : `python3 -m pip install pyipx800v3_async`)

## Description

For now, this integration is able to use this type of component :

- `Output` en tant que switch ou light (avec https://www.gce-electronics.com/fr/nos-produits/314-module-diode-fil-pilote-.html)
- `Input` en tant que binarysensor

## Push state from l'IPX800 V3

First, if you want to use the push feature of your IPX800 V3, you should set the `push_password` variable in your configuration. The login will always be `ipx800`, in so, put `ipx800:<your password>` in the login field of your IPX800 V3.

2 types of refresh is available : 

- Global refresh using the url `/api/ipx800v3_refresh/on` : Home Assistant will refresh all IPX800 V3 devices.
- Specific refresh using the `entity_id` : In `URL ON` and `URL_OFF`, put `/api/ipx800v3/<entity_id>/state`  (`state` will take `on` or `off`)

## Example of configuration

```yaml
# Example configuration.yaml entry
ipx800v4:
  - name: IPX800 V3
    host: "192.168.1.2"
    username: !secret ipx800v3_username
    password: !secret ipx800v3_password
    push_password: !secret ipx800v3_push_password
    devices:
      - name: Water Boiler
        icon: mdi:water-boiler
        type: "relay"
        component: "switch"
        id: 1
      - name: Light Garage
        type: relay
        component: light
        id: 7
      - component: binary_sensor
        device_class: motion
        name: Motion Garage
        type: digitalin
        id: 1
```
