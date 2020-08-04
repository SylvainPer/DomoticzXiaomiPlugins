# coding=UTF-8
# Python Plugin for Xiaomi Miio AirPurifier Miot
#
# Author: xiaoyao9184 & SylvainPer
#
"""
<plugin 
    key="Xiaomi-Miio-AirPurifier-Miot" 
    name="Xiaomi Miio AirPurifier Miot" 
    author="xiaoyao9184 & SylvainPer" 
    version="0.1" 
    externallink="https://github.com/SylvainPer/DomoticzXiaomiPlugins">
    <params>
        <param field="Mode1" label="Debug" width="200px">
            <options>
                <option label="None" value="none" default="none"/>
                <option label="Debug(Only Domoticz)" value="debug"/>
                <option label="Debug(Attach by ptvsd)" value="ptvsd"/>
                <option label="Debug(Attach by rpdb)" value="rpdb"/>
            </options>
        </param>
        <param field="Mode2" label="Repeat Time(s)" width="30px" required="true" default="120"/>
        <param field="Address" label="IP" width="100px" required="true"/>
        <param field="Mode3" label="Token" width="250px" required="true"/>
    </params>
</plugin>
"""

# Fix import of libs installed with pip as PluginSystem has a wierd pythonpath...
import os
import sys
import site
for mp in site.getsitepackages():
    sys.path.append(mp)

import Domoticz
import miio
import functools


class Heartbeat():

    def __init__(self, interval):
        self.callback = None
        self.count = 0
        # stage interval
        self.seek = 0
        self.interval = 10
        # real interval
        self.total = 10
        if (interval < 0):
            pass
        elif (0 < interval and interval < 30):
            self.interval = interval
            self.total = interval
        else:
            result = self.show_factor(interval, self.filter_factor, self.bast_factor)
            self.seek = result["repeat"]
            self.interval = result["factor"]
            self.total = result["number"]

    def setHeartbeat(self, func_callback):
        Domoticz.Heartbeat(self.interval)
        Domoticz.Log("Heartbeat total interval set to: " + str(self.total) + ".")
        self.callback = func_callback
            
    def beatHeartbeat(self):
        self.count += 1
        if (self.count >= self.seek):
            self.count = 0
            if self.callback is not None:
                Domoticz.Log("Calling heartbeat handler " + str(self.callback.__name__) + ".")
                self.callback()
        else:
            Domoticz.Log("Skip heartbeat handler because stage not enough " + str(self.count) + "/" + str(self.seek) + ".")

    def filter_factor(self, factor):
        return factor < 30 and factor > 5

    def show_factor(self, number, func_filter, func_prime):
        factor = number // 2
        while factor > 1:
            if number % factor == 0 and func_filter(factor):
                return {
                    "number": number,
                    "factor": factor,
                    "repeat": int(number / factor)
                }
            factor-=1
        else:
            return func_prime(number)

    def next_factor(self, number):
        return self.show_factor(number + 1, self.filter_factor, self.next_factor)

    def last_factor(self, number):
        return self.show_factor(number - 1, self.filter_factor, self.last_factor)

    def bast_factor(self, number):
        n = self.next_factor(number)
        l = self.last_factor(number)

        if n["factor"] >= l["factor"]:
            return n
        else:
            return l


class CacheStatus(object):
    def __init__(self, status):
      self.status = status
      self.cache = {}

    def __getattr__(self, name):
        if name not in self.cache:
            value = getattr(self.status, name)
            if value is not None:
                self.cache[name] = value
            else:
                return None
        return self.cache[name]

    def __setattr__(self, name, value):
        if(name == 'status' or name == 'cache'):
            super(CacheStatus, self).__setattr__(name, value)
            return
        self.cache[name] = value

    def toString(self):
        l = []
        for attr in dir(self.status):
            if(attr[:1] != "_" and attr != 'data'):
                value = getattr(self.status, attr)
                l.append(str(attr + ' = ' + str(value)) )
        return ', '.join(l)


class AirPurifierMiotPlugin:

    def MapEnumStatus(self, unit, status):
        try:
            value = None
            text = None
            if "map_status_value" in unit.keys():
                value = unit["map_status_value"][status]
            else:
                value = status

            if "map_status_text" in unit.keys():
                text = unit["map_status_text"][status]
            else:
                text = status
            
        except Exception as updateError :
            Domoticz.Error("MapEnumStatus: " + repr(updateError))

        return {
            "value": value,
            "text": text
        }

    def MapStatus(self, unit, status):
        try:
            value = None
            text = None
            if "map_status_value" in unit.keys():
                mapStatusValue = unit["map_status_value"]
                if mapStatusValue == None:
                    value = status
                elif type(mapStatusValue) is int:
                    value = mapStatusValue
                else:
                    value = mapStatusValue(self, unit, status)
            else:
                value = status

            if "map_status_text" in unit.keys():
                mapStatusText = unit["map_status_text"]
                if mapStatusText == None:
                    text = str(status)
                elif type(mapStatusText) is str:
                    text = mapStatusText
                elif type(mapStatusText) is dict:
                    text = unit["map_status_text"][status]
                else:
                    text = mapStatusText(self, unit, status)
            else:
                text = status
                
        except Exception as updateError :
            Domoticz.Error("MapEnumStatus: " + repr(updateError))
            
        return {
            "value": value,
            "text": text
        }
    
    def MapStatusWithFactor(self, unit, status):
        try:
            value = None
            text = None
            if "map_status_value" in unit.keys():
                mapStatusValue = unit["map_status_value"]
                if mapStatusValue == None:
                    value = status
                elif type(mapStatusValue) is int:
                    value = mapStatusValue
                else:
                    value = mapStatusValue(self, unit, status)
            else:
                value = status

            if "map_status_text" in unit.keys():
                mapStatusText = unit["map_status_text"]
                if mapStatusText == None:
                    if unit["map_factor"] != None:
                        status = max(0,min(100,status*unit["map_factor"]))
                    text = str(status)
                elif type(mapStatusText) is str:
                    text = mapStatusText
                elif type(mapStatusText) is dict:
                    text = unit["map_status_text"][status]
                else:
                    text = mapStatusText(self, unit, status)
            else:
                if unit["map_factor"] != None:
                        status = max(0,min(100,status*unit["map_factor"]))
                text = status
        except Exception as updateError :
            Domoticz.Error("MapEnumStatus: " + repr(updateError))
            
        return {
            "value": value,
            "text": text
        }

    def MapEnumCommandToMethod(self, unit, command, level):
        field = unit["bindingStatusField"]
        status_old = getattr(self.status, field)
        status_new = unit["map_command_status"][command]

        if status_old == status_new:
            Domoticz.Log("The command is consistent with the status:" + str(command))
            return None

        method = unit["map_command_method"][command]
        method = rgetattr(self, method)
        try :
            result = method()
            Domoticz.Log("Method call result:" + str(result))
            if (result[0]['code'] == 0):
                return status_new

        except Exception as updateError :
            Domoticz.Error("MapEnumCommandToMethod: " + repr(updateError))

        
        return None

    def MapEnumCommandToMethodParam(self, unit, command, level):
        field = unit["bindingStatusField"]
        status_old = getattr(self.status, field)
        status_new = unit["map_command_status"][command]

        if status_old == status_new:
            Domoticz.Log("The command is consistent with the status:" + str(command))
            return None

        method = unit["map_command_method"]
        method = rgetattr(self, method)
        param = unit["map_command_method_param"][command]

        try :
            result = method(param)
        
            Domoticz.Log("Method call result:" + str(result))
            if (result[0]['code'] == 0):
                return status_new

        except Exception as updateError :
            Domoticz.Error("MapEnumCommandToMethodParam: " + repr(updateError))

        return None

    def MapEnumLevelToMethodParam(self, unit, command, level):
        field = unit["bindingStatusField"]
        status_old = getattr(self.status, field)
        status_new = unit["map_level_status"][level]
        Domoticz.Log("The level asked :" + str(status_new))
        if status_old == status_new:
            Domoticz.Log("The level is consistent with the status:" + str(command))
            return None

        method = unit["map_level_method"]
        method = rgetattr(self, method)
        param = unit["map_level_param"][level]
        
        try :
            result = method(param)
        
            Domoticz.Log("Method call result:" + str(result))
            if (result[0]['code'] == 0):
                return status_new

        except Exception as updateError :
            Domoticz.Error("MapEnumLevelToMethodParam: " + repr(updateError))

        return None

    def MapLevelToMethodParam(self, unit, command, level):
        field = unit["bindingStatusField"]
        status_old = getattr(self.status, field)
        status_new = level

        mapLevelStatus = unit["map_level_status"]
        if mapLevelStatus != None:
            status_new = mapLevelStatus(self, unit, level)
            if status_new == status_old:
                Domoticz.Log("The command is consistent with the status:" + str(command))
                return None

        method = unit["map_level_method"]
        method = rgetattr(self, method)
        param = level
        mapLevelParam = unit["map_level_param"]
        if mapLevelParam != None:
            param = mapLevelParam(self, unit, level)

        try :
            result = method(param)
        
            Domoticz.Log("Method call result:" + str(result))
            if (result[0]['code'] == 0):
                return status_new

        except Exception as updateError :
            Domoticz.Error("MapLevelToMethodParam: " + repr(updateError))


        return None
        
        
    def MapLevelToMethodParamWithFactor(self, unit, command, level):
        field = unit["bindingStatusField"]
        status_old = getattr(self.status, field)
        status_new = level

        mapLevelStatus = unit["map_level_status"]
        if mapLevelStatus != None:
            status_new = mapLevelStatus(self, unit, level)
            if status_new == status_old:
                Domoticz.Log("The command is consistent with the status:" + str(command))
                return None

        method = unit["map_level_method"]
        method = rgetattr(self, method)
        param = level
        if unit["map_factor"] != None:
            param = round(param / unit["map_factor"])
        mapLevelParam = unit["map_level_param"]
        if mapLevelParam != None:
            param = mapLevelParam(self, unit, param)

        try :
            result = method(param)
        
            Domoticz.Log("Method call result:" + str(result))
            if (result[0]['code'] == 0):
                return param

        except Exception as updateError :
            Domoticz.Error("MapLevelToMethodParam: " + repr(updateError))


        return None

    # fix humidity
    def MapTextHumidity(self, unit, status):
        sValue = 0
        n = int(getattr(self.status,"humidity"))
        if n < 46:
            sValue = 2        #dry
        elif n > 70:
            sValue = 3        #wet
        else:
            sValue = 1        #comfortable
        return sValue


    __UNIT_AQI = 1
    __UNIT_AVG_AQI = 2
    __UNIT_FILTER_HOURS_USED = 3
    __UNIT_FILTER_LIFE_REMAINING = 4
    __UNIT_HUMIDITY = 5
    __UNIT_MOTOR_SPEED = 6
    __UNIT_FAN_LEVEL = 7
    __UNIT_PURIFY_VOLUME = 8
    __UNIT_TEMPERATURE = 9
    __UNIT_USED_TIME = 10
    __UNIT_POWER = 11
    __UNIT_BUZZER = 12
    __UNIT_CHILD_LOCK = 13
    __UNIT_FAVORITE_LEVEL = 14
    __UNIT_LED = 15
    __UNIT_BRIGHTNESS = 16
    __UNIT_MODE = 17
    __UNIT_VOLUME = 18
    __UNIT_TEMPERATURE_HUMIDITY = 19
    
    __UNITS = [
        {
            "_Name": "AirPurifier_AQI", 
            "_Unit": __UNIT_AQI, 
            "_TypeName": "Air Quality",
            "_Options": None,
            # {
                # "Custom": "1;μg/m³"
            # },
            "bindingStatusField": "aqi",
            "mapStatus": MapStatus,
            "map_status_value": 1, 
            "map_status_text": None
        },
        {
            "_Name": "AirPurifier_Average_AQI", 
            "_Unit": __UNIT_AVG_AQI, 
            "_TypeName": "Custom",
            "_Options": {
                "Custom": "1;μg/m³"
            }, 
            "bindingStatusField": "average_aqi",
            "mapStatus": MapStatus,
            "map_status_value": 1, 
            "map_status_text": None
        },
        {
            "_Name": "AirPurifier_Filter_Hours_Used", 
            "_Unit": __UNIT_FILTER_HOURS_USED, 
            "_TypeName": "Custom",
            "_Options": {
                "Custom": "1;h"
            }, 
            "bindingStatusField": "filter_hours_used",
            "mapStatus": MapStatus,
            "map_status_value": 1, 
            "map_status_text": None
        },
        {
            "_Name": "AirPurifier_filter_life_remaining", 
            "_Unit": __UNIT_FILTER_LIFE_REMAINING, 
            "_TypeName": "Percentage",
            "_Options": None,
            "bindingStatusField": "filter_life_remaining",
            "mapStatus": MapStatus,
            "map_status_value": 1, 
            "map_status_text": None
        },
        {
            "_Name": "AirPurifier_Humidity", 
            "_Unit": __UNIT_HUMIDITY, 
            "_TypeName": "Humidity",
            "_Options": None,
            "bindingStatusField": "humidity",
            "mapStatus": MapStatus,
            "map_status_value": None, 
            "map_status_text": MapTextHumidity
        },
        {
            "_Name": "AirPurifier_Motor_speed", 
            "_Unit": __UNIT_MOTOR_SPEED, 
            "_TypeName": "Custom",
            "_Options": {
                "Custom": "1;Speed"
            }, 
            "bindingStatusField": "motor_speed",
            "mapStatus": MapStatus,
            "map_status_value": 1, 
            "map_status_text": None
        },
        {
            "_Name": "AirPurifier_Fan_Level", 
            "_Unit": __UNIT_FAN_LEVEL, 
            "_TypeName": "Selector Switch", 
            "_Switchtype": 18,
            "_Image": 7,
            "_Options": {
                "LevelActions"  :"|||" , 
                "LevelNames"    :"Low|Med|High" ,
                "LevelOffHidden":"false",
                "SelectorStyle" :"0"
            },
            "bindingStatusField": "fan_level",
            "mapStatus": MapEnumStatus,
            "map_status_value": {1 : 2, 2 : 2, 3 : 2,}, 
            "map_status_text": { 1 : "0", 2 : "10", 3 : "20" },
            "mapCommand": MapEnumLevelToMethodParam,
            "map_level_status": { 0: 1, 10: 2, 20: 3 },
            "map_level_method": "miio.set_fan_level",
            "map_level_param": { 0: 1, 10: 2, 20: 3 },
        },        
        {
            "_Name": "AirPurifier_Purify_Volume", 
            "_Unit": __UNIT_PURIFY_VOLUME, 
            "_TypeName": "Custom",
            "_Options": {
                "Custom": "1;m³"
            }, 
            "bindingStatusField": "purify_volume",
            "mapStatus": MapStatus,
            "map_status_value": 1, 
            "map_status_text": None
        },
        {
            "_Name": "AirPurifier_Temperature", 
            "_Unit": __UNIT_TEMPERATURE, 
            "_TypeName": "Temperature",
            "_Options": None,
            "bindingStatusField": "temperature",
            "mapStatus": MapStatus,
            "map_status_value": 1, 
            "map_status_text": None
        },
        {
            "_Name": "AirPurifier_Use_time", 
            "_Unit": __UNIT_USED_TIME, 
            "_TypeName": "Custom",
            "_Options": {
                "Custom": "1;Seconds"
            }, 
            "bindingStatusField": "use_time",
            "mapStatus": MapStatus,
            "map_status_value": 1, 
            "map_status_text": None
        },
        # button_pressed
        # filter_rfid_product_id
        # filter_rfid_tag
        # filter_type
        # sleep_mode
        # turbo_mode_supported

        {
            "_Name": "AirPurifier_Power", 
            "_Unit": __UNIT_POWER, 
            "_TypeName": "Selector Switch", 
            # Selector Switch / On/Off
            "_Switchtype": 0,
            "_Image": 7,
            "_Options": None,
            "bindingStatusField": "is_on",
            "mapStatus": MapEnumStatus,
            "map_status_value": { True: 1, False: 0 }, 
            "map_status_text": { True: "On", False: "Off" },
            "mapCommand": MapEnumCommandToMethod,
            "map_command_status": { "On": True, "Off": False },
            "map_command_method": {
                "On": "miio.on",
                "Off": "miio.off"
            }
        },
        {
            "_Name": "AirPurifier_Buzzer", 
            "_Unit": __UNIT_BUZZER, 
            "_TypeName": "Selector Switch", 
            # Selector Switch / On/Off
            "_Switchtype": 0,
            "_Image": 9,
            "_Options": None,
            "bindingStatusField": "buzzer",
            "mapStatus": MapEnumStatus,
            "map_status_value": { True: 1, False: 0 }, 
            "map_status_text": { True: "On", False: "Off" },
            "mapCommand": MapEnumCommandToMethodParam,
            "map_command_status": { "On": True, "Off": False },
            "map_command_method": "miio.set_buzzer",
            "map_command_method_param": { "On": True, "Off": False }
        },
        {
            "_Name": "AirPurifier_Child_Lock", 
            "_Unit": __UNIT_CHILD_LOCK, 
            "_TypeName": "Selector Switch", 
            # Selector Switch / On/Off
            "_Switchtype": 0,
            "_Image": 9,
            "_Options": None,
            "bindingStatusField": "child_lock",
            "mapStatus": MapEnumStatus,
            "map_status_value": { True: 1, False: 0 }, 
            "map_status_text": { True: "On", False: "Off" },
            "mapCommand": MapEnumCommandToMethodParam,
            "map_command_status": { "On": True, "Off": False },
            "map_command_method": "miio.set_child_lock",
            "map_command_method_param": { "On": True, "Off": False }
        },
        {
            "_Name": "AirPurifier_Favorite_Level", 
            "_Unit": __UNIT_FAVORITE_LEVEL, 
            "_TypeName": "Dimmer", 
            # Selector Switch / Dimmer
            #"_Switchtype": 7,
            "_Image": 7,
            "_Options": None,
            "bindingStatusField": "favorite_level",
            "mapStatus": MapStatusWithFactor,
            "map_status_value": 2, 
            "map_status_text": None,
            "mapCommand": MapLevelToMethodParamWithFactor,
            "map_level_status": None,
            "map_level_method": "miio.set_favorite_level",
            "map_level_param": None,
            "map_factor":7
        },
        {
            "_Name": "AirPurifier_LED", 
            "_Unit": __UNIT_LED,
            "_TypeName": "Selector Switch", 
            # Selector Switch / On/Off
            "_Switchtype": 0,
            "_Image": 0,
            "_Options": None,
            "bindingStatusField": "led",
            "mapStatus": MapEnumStatus,
            "map_status_value": { True: 1, False: 0 }, 
            "map_status_text": { True: "On", False: "Off" },
            "mapCommand": MapEnumCommandToMethodParam,
            "map_command_status": { "On": True, "Off": False },
            "map_command_method": "miio.set_led",
            "map_command_method_param": { "On": True, "Off": False }
        },
        {
            "_Name": "AirPurifier_Brightness", 
            "_Unit": __UNIT_BRIGHTNESS, 
            "_TypeName": "Selector Switch", 
            # Selector Switch / Selector
            "_Switchtype": 18,
            "_Image": 7,
            "_Options": {
                "LevelActions"  :"|||" , 
                "LevelNames"    :"Off|Dim|Bright" ,
                "LevelOffHidden":"false",
                "SelectorStyle" :"0"
            },
            "bindingStatusField": "led_brightness",
            "mapStatus": MapEnumStatus,
            "map_status_value": { miio.airpurifier_miot.LedBrightness.Off: 2, miio.airpurifier_miot.LedBrightness.Dim: 2, miio.airpurifier_miot.LedBrightness.Bright: 2 }, 
            "map_status_text": { miio.airpurifier_miot.LedBrightness.Off: "0", miio.airpurifier_miot.LedBrightness.Dim: "10", miio.airpurifier_miot.LedBrightness.Bright: "20"},
            "mapCommand": MapEnumLevelToMethodParam,
            "map_level_status": { 0: miio.airpurifier_miot.LedBrightness.Off, 10: miio.airpurifier_miot.LedBrightness.Dim, 20: miio.airpurifier_miot.LedBrightness.Bright },
            "map_level_method": "miio.set_led_brightness",
            "map_level_param": { 0: miio.airpurifier_miot.LedBrightness.Off, 10: miio.airpurifier_miot.LedBrightness.Dim, 20: miio.airpurifier_miot.LedBrightness.Bright }
        },
        {
            "_Name": "AirPurifier_Mode", 
            "_Unit": __UNIT_MODE, 
            "_TypeName": "Selector Switch", 
            "_Switchtype": 18,
            "_Image": 7,
            "_Options": {
                "LevelActions"  :"|||||" , 
                "LevelNames"    :"Auto|Fan|Favorite|Silent" ,
                "LevelOffHidden":"false",
                "SelectorStyle" :"0"
            },
            "bindingStatusField": "mode",
            "mapStatus": MapEnumStatus,
            "map_status_value": { 
                miio.airpurifier_miot.OperationMode.Auto: 2, 
                miio.airpurifier_miot.OperationMode.Fan: 2, 
                miio.airpurifier_miot.OperationMode.Favorite: 2, 
                miio.airpurifier_miot.OperationMode.Silent: 2 }, 
            "map_status_text": { 
                miio.airpurifier_miot.OperationMode.Auto: "0", 
                miio.airpurifier_miot.OperationMode.Fan: "10", 
                miio.airpurifier_miot.OperationMode.Favorite: "20", 
                miio.airpurifier_miot.OperationMode.Silent: "30" },
            "mapCommand": MapEnumLevelToMethodParam,
            "map_level_status": { 
                0: miio.airpurifier_miot.OperationMode.Auto, 
                10: miio.airpurifier_miot.OperationMode.Fan, 
                20: miio.airpurifier_miot.OperationMode.Favorite,
                30: miio.airpurifier_miot.OperationMode.Silent },
            "map_level_method": "miio.set_mode",
            "map_level_param": { 
                0: miio.airpurifier_miot.OperationMode.Auto, 
                10: miio.airpurifier_miot.OperationMode.Fan, 
                20: miio.airpurifier_miot.OperationMode.Favorite,
                30: miio.airpurifier_miot.OperationMode.Silent }
        },
        {
            "_Name": "AirPurifier_Buzzer_Volume", 
            "_Unit": __UNIT_VOLUME,
            "_TypeName": "Dimmer", 
            # Selector Switch / Dimmer
            #"_Switchtype": 7,
            #"_Image": None,
            "_Options": None,
            "bindingStatusField": "buzzer_volume",
            "mapStatus": MapStatus,
            "map_status_value": 2, 
            "map_status_text": None,
            "mapCommand": MapLevelToMethodParam,
            "map_level_status": None,
            "map_level_method": "miio.set_volume",
            "map_level_param": None
        },
        {
            "_Name": "AirPurifier_Temperature_Humidity", 
            "_Unit": __UNIT_TEMPERATURE_HUMIDITY, 
            "_TypeName": "Temp+Hum",
            "_Options": None,
            "bindingStatusField": ["temperature","humidity",MapTextHumidity],
            "mapStatus": MapStatus,
            "map_status_value": None, 
            "map_status_text": None
        }
    ]

    def __init__(self):
        self.miio = None
        self.status = None
        self.devicesCreated = False
        return

    def onStart(self):
        # Debug
        debug = 0
        if (Parameters["Mode1"] != "none"):
            Domoticz.Debugging(1)
            debug = 1

        if (Parameters["Mode1"] == "ptvsd"):
            Domoticz.Log("Debugger ptvsd started, use 0.0.0.0:5678 to attach")
            import ptvsd
            # signal error on raspberry
            ptvsd.enable_attach()
            ptvsd.wait_for_attach()
        elif (Parameters["Mode1"] == "rpdb"):
            Domoticz.Log("Debugger rpdb started, use 'telnet 127.0.0.1 4444' on host to connect")
            import rpdb
            rpdb.set_trace()
            # signal error on raspberry
            # rpdb.handle_trap("0.0.0.0", 4444)

        # Heartbeat
        self.heartbeat = Heartbeat(int(Parameters["Mode2"]))
        self.heartbeat.setHeartbeat(self.UpdateStatus)

        # Create miio
        ip = Parameters["Address"]
        token = Parameters["Mode3"]
        
        self.miio = miio.airpurifier_miot.AirPurifierMiot(ip, token, 0, debug, True)
        Domoticz.Debug("Xiaomi AirPurifier created with address '" + ip
            + "' and token '" + token + "'")

        # Read function
        self.UpdateStatus(False)

        # Create devices
        if self.status != None :
            self.createDevices()
            self.devicesCreated = True

        # Read initial state
        self.UpdateStatus()

        DumpConfigToLog()

        return
    
    def createDevices(self):
        for unit in self.__UNITS:
            field = unit["bindingStatusField"]
            if type(field) is list :
                field = field[0]
            try :
                value = getattr(self.status, field)
            except :
                value = None
            if value is not None and unit["_Unit"] not in Devices:
                if "_Switchtype" in unit and unit["_Switchtype"] != None:
                    Domoticz.Device(
                        Name = unit["_Name"], 
                        Unit = unit["_Unit"],
                        TypeName = unit["_TypeName"], 
                        Switchtype = unit["_Switchtype"],
                        Image = unit["_Image"],
                        Options = unit["_Options"]).Create()
                else:
                    Domoticz.Device(
                        Name = unit["_Name"], 
                        Unit = unit["_Unit"],
                        TypeName = unit["_TypeName"], 
                        Options = unit["_Options"]).Create()
        return

    def onStop(self):
        Domoticz.Debug("onStop called")
        return

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called: Connection=" + str(Connection) + ", Status=" + str(Status) + ", Description=" + str(Description))
        return

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called: Connection=" + str(Connection) + ", Data=" + str(Data))
        return

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called: Unit=" + str(Unit) + ", Parameter=" + str(Command) + ", Level=" + str(Level))

        unit = FindUnit(self.__UNITS, Unit)
        if unit is not None and "mapCommand" in unit.keys():
            status = unit["mapCommand"](self, unit, Command, Level)
            if status != None:
                # Update device
                field = unit["bindingStatusField"]
                setattr(self.status, field, status)
                vt = unit["mapStatus"](self, unit, status)
                UpdateDevice(unit["_Unit"], vt["value"], str(vt["text"]))
            #return
        # TODO Update devices
        #self.UpdateStatus()
        return

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)
        return

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called")
        return

    def onHeartbeat(self):
        self.heartbeat.beatHeartbeat()
        return
        

    def UpdateStatus(self, updateDevice = True):
        if not hasattr(self, "miio"):
            return
        
        try:
            self.status = self.miio.status()
            self.status = CacheStatus(self.status)
            log = "Status : " + self.status.toString()
            Domoticz.Debug(log)
            
            if self.devicesCreated == False :
                if self.status != None :
                    self.createDevices()
                    self.devicesCreated = True

            # Update devices
            if (updateDevice):
                for unit in self.__UNITS:
                    fields = unit["bindingStatusField"]
                    if type(fields) is list:        #allow to concatenate several informations
                        values = None
                        for field in fields:
                            if type(field) is str:  #for status content
                                status = getattr(self.status, field)
                                if status is None:
                                    pass
                                elif "mapStatus" in unit.keys():
                                    vt = unit["mapStatus"](self, unit, status)
                                else:
                                    vt["text"] = str(status)
                            else:                   #for functions
                                vt["text"] = str(field(self,unit,0))
                            if values == None:
                                values = str(vt["text"])
                            else:
                                values = values + ";" + str(vt["text"])
                        UpdateDevice(unit["_Unit"], 0 , values)
                    else:
                        status = getattr(self.status, fields)
                        if status is None:
                            pass
                        elif "mapStatus" in unit.keys():
                            vt = unit["mapStatus"](self, unit, status)
                            UpdateDevice(unit["_Unit"], vt["value"], str(vt["text"]))
                        else:
                            UpdateDevice(unit["_Unit"], status, str(status))
            return
        except Exception as updateError :
            Domoticz.Error("UpdateStatus: " + repr(updateError))


global _plugin
_plugin = AirPurifierMiotPlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


# Generic helper functions

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def UpdateDevice(Unit, nValue, sValue):
    if (Unit not in Devices): return
    
    if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
        Domoticz.Debug("Update '" + Devices[Unit].Name + "' : " + str(nValue) + " - " + str(sValue))
        # Warning: The lastest beta does not completly support python 3.5
        # and for unknown reason crash if Update methode is called whitout explicit parameters
        Devices[Unit].Update(nValue = nValue, sValue = str(sValue))
    return

def FindUnit(Units, unit):
    for item in Units:
        if item["_Unit"] == unit:
            return item
    return None

def rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition('.')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)

# using wonder's beautiful simplification: https://stackoverflow.com/questions/31174295/getattr-and-setattr-on-nested-objects/31174427?noredirect=1#comment86638618_31174427

def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))
