# DomoticzXiaomiPlugins

This project is an attempt to make Python plugins for Xiaomi devices in Domoticz, using the python-miio library.

Plugin | Device compatibility
------------ | -------------
MiioAirPurifier | Xiaomi Mi Air Purifier 
MiioAirPurifierMiot | Xiaomi Mi Air Purifier 3H
MiioChuangmiPlug |
MiioPhilipsBulb |
MiioPowerStrip |

# Use

Raspberry Pi/Ubuntu installation:

```curl -L https://github.com/xiaoyao9184/DomoticzXiaomiPlugins/raw/master/install.sh | bash```

**NOTE:** must updated domoticz to version 4.10 (now is beta version)

# See

- Domoticz : https://github.com/domoticz/domoticz
- python-miio : https://github.com/rytilahti/python-miio

# Troubleshooting

- Device[X].Update() crash domoticz if called whith implicit parameters. See https://github.com/domoticz/domoticz/issues/2092
- Calling python-miio seems to freeze domoticz's plugin system. Don't know why but similar project faced the same issue. See https://github.com/mrin/domoticz-mirobot-plugin
- Data Push with `status` Type like `Selector Switch / Dimmer` device cant push `Level`, `Selector Switch / Dimmer` has 3 status for command `On` is 1, `Off` is 0, `Set Level` is 2. If it have shared `On` and `Off` for multiple `Selector Switch / Dimmer` devices, will cause confusion. Like `MiioPhilipsBulb`

# Help

- Domoticz device types : https://github.com/domoticz/domoticz/blob/development/hardware/hardwaretypes.h
