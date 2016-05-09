__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
logger = logging.getLogger('mbus')

import mbus.MBusLowLevel as mbusLow
from enum import Enum
from datetime import datetime
#import pytz                             # for daylight saving time encdding
from tzlocal import get_localzone       # for current time zone
import struct                           # for converting byte area to float
import sys                               # for max values

class ValueEncode(Enum):
    """enum for all the possible value encodes"""
    Byte = 1
    ShortDate = 0x6C
    Short = 2
    Int3Byte = 3
    Int = 4
    IntDate = 0x6D
    Float = 5
    Int6Byte = 6
    Long = 7
    BCD2Digit = 9
    BCD4Digit = 0x0A
    BCD6Digit = 0x0B
    BCD8Digit = 0x0C
    BCD12Digit = 0x0E
    Bin = 0x0F
    String = 0x0D
    Unknown = 0xFF

    def getMax(self):
        """retunrs the max value that this number can contain."""
        if self.value == self.Byte.value:
            return 0xFF
        elif self.value == self.ShortDate.value:
            return 0xFFFF
        elif self.value == self.Short.value:
            return 0xFFFF
        elif self.value == self.Int3Byte.value:
            return 0xFFFFFF
        elif self.value == self.Int.value:
            return 0xFFFFFFFF
        elif self.value == self.IntDate.value:
            return 0xFFFFFFFF
        elif self.value == self.Float.value:
            return sys.float_info.max
        elif self.value == self.Int6Byte.value:
            return 0xFFFFFFFFFF
        elif self.value == self.Long.value:
            return 0xFFFFFFFFFFFF
        elif self.value == self.BCD2Digit.value:
            return 99
        elif self.value == self.BCD4Digit.value:
            return 9999
        elif self.value == self.BCD6Digit.value:
            return 999999
        elif self.value == self.BCD8Digit.value:
            return 99999999
        elif self.value == self.BCD12Digit.value:
            return 999999999999
        else:
            return None






def toDict(data, full):
    """convert a list of MBusFrameData objects into a python dictionar object that can be used to
        load the assets and data into the system[
        :type data: array of MBusFrame
        :param data: the data to parse
        :param full: when true, all data will be parsed, otherwise only the values.
    """
    first = data[0]  # use the first record to build the header info.
    result = {}
    if first.type == mbusLow.MBUS_DATA_TYPE_ERROR:
        result['Error'] = _getErrorMsg(first.error)
    elif first.type == mbusLow.MBUS_DATA_TYPE_FIXED:
        _addDataFixed(result, first.data_fix, full)
    elif first.type == mbusLow.MBUS_DATA_TYPE_VARIABLE:
        if full:
            _addDataVariable(result, first.data_var.header)
        result["DataRecord"] = _addVarRecords(data, full)
    return result


def _getErrorMsg(self, error):
    """convert the error number into a string"""
    if error == mbusLow.MBUS_ERROR_DATA_UNSPECIFIED:
        return "Unspecified error"
    elif error == mbusLow.MBUS_ERROR_DATA_UNIMPLEMENTED_CI:
        return "Unimplemented CI-Field"
    elif error == mbusLow.MBUS_ERROR_DATA_BUFFER_TOO_LONG:
        return "Buffer too long, truncated"
    elif error == mbusLow.MBUS_ERROR_DATA_TOO_MANY_RECORDS:
        return "Too many records"
    elif error == mbusLow.MBUS_ERROR_DATA_PREMATURE_END:
        return "Premature end of record"
    elif error == mbusLow.MBUS_ERROR_DATA_TOO_MANY_DIFES:
        return "More than 10 DIFE's"
    elif error == mbusLow.MBUS_ERROR_DATA_TOO_MANY_VIFES:
        return "More than 10 VIFE's"
    elif error == mbusLow.MBUS_ERROR_DATA_RESERVED:
        return "Reserved"
    elif error == mbusLow.MBUS_ERROR_DATA_APPLICATION_BUSY:
        return "Application busy"
    elif error == mbusLow.MBUS_ERROR_DATA_TOO_MANY_READOUTS:
        return "Too many readouts"
    else:
        return "unknown error: {}".format(error)


def _addDataFixed(result, data, full):
    """parse a fixed data header and add the data to the result"""
    if full:
        result['Id'] = _bcd_decode(data.id_bcd, 4)
        result['Medium'] = _dataFixedMedium(data)
        result['Status'] = data.status
        result['Function'] = _fixedFunction(data.status)

    record1 = {}
    if full:
        record1['Unit_int'] = data.cnt1_type
        record1['Unit'] = _fixedUnit(data.cnt1_type)
    if data.status & mbusLow.MBUS_DATA_FIXED_STATUS_FORMAT_MASK == mbusLow.MBUS_DATA_FIXED_STATUS_FORMAT_BCD:
        record1['Value'] = _bcd_decode(data.cnt1_val, 4)
    else:
        record1['Value'] = _int_decode(data.cnt1_val, 4)

    record2 = {}
    if full:
        record2['Unit_int'] = data.cnt2_type
        record1['Unit'] = _fixedUnit(data.cnt2_type)
    if data.status & mbusLow.MBUS_DATA_FIXED_STATUS_FORMAT_MASK == mbusLow.MBUS_DATA_FIXED_STATUS_FORMAT_BCD:
        record1['Value'] = _bcd_decode(data.cnt2_val, 4)
    else:
        record1['Value'] = _int_decode(data.cnt2_val, 4)

    result['DataRecord'] = [record1, record2]

def _bcd_decode(data, size):
    """decode a byte array into a number"""
    val = 0
    if data:
        for i in range(size, 0, -1):
            val = (val * 10) + ((data[i - 1] >> 4) & 0xF)
            val = (val * 10) + (data[i - 1] & 0xF)
        return val
    return -1

def _int_decode(data, size):
    """"decode data into int"""
    if not data or size < 1:
        return None
    result = 0
    neg = data[size -1] & 0x80
    for i in range(size, 0, -1):
        if neg:
            result = (result << 8) + (data[i-1] ^ 0xFF)
        else:
            result = (result << 8) + data[i - 1]
    if neg:
        result = result * -1 -1
    return result

def _dataFixedMedium(data):
    """convert the binary info about the medium into a string"""
    if data:
        val = (data.cnt1_type & 0xC0) >> 6 | (data.cnt2_type & 0xC0) >> 4
        if val == 0x00: return "Other"
        elif val == 0x01: return "Oil"
        elif val == 0x02: return "Electricity"
        elif val == 0x03: return "Gas"
        elif val == 0x04: return "Heat"
        elif val == 0x05: return "Steam"
        elif val == 0x06: return "Hot Water"
        elif val == 0x07: return "Water"
        elif val == 0x08: return "H.C.A."
        elif val == 0x09: return "Reserved"
        elif val == 0x0A: return "Gas Mode 2"
        elif val == 0x0B: return "Heat Mode 2"
        elif val == 0x0C: return "Hot Water Mode 2"
        elif val == 0x0D: return "Water Mode 2"
        elif val == 0x0E: return "H.C.A. Mode 2"
        elif val == 0x0F: return "Reserved"
        else: return "unknown"

def _fixedFunction(status):
    return "Stored function" if status & mbusLow.MBUS_DATA_FIXED_STATUS_DATE_MASK == mbusLow.MBUS_DATA_FIXED_STATUS_DATE_STORED else "Actual value"

def _fixedUnit(value):
    val = value & 0x3F
    if val == 0x00: return "h,m,s"
    elif val == 0x01: return "D,M,Y"
    elif val == 0x02: return "Wh"
    elif val == 0x03: return "10 Wh"
    elif val == 0x04: return "100 Wh"
    elif val == 0x05: return "kWh"
    elif val == 0x06: return "10 kWh"
    elif val == 0x07: return "100 kWh"
    elif val == 0x08: return "MWh"
    elif val == 0x09: return "10 MWh"
    elif val == 0x0A: return "100 MWh"
    elif val == 0x0B: return "kJ"
    elif val == 0x0C: return "10 kJ"
    elif val == 0x0D: return "100 kJ"
    elif val == 0x0E: return "MJ"
    elif val == 0x0F: return "10 MJ"
    elif val == 0x10: return "100 MJ"
    elif val == 0x11: return "GJ"
    elif val == 0x12: return "10 GJ"
    elif val == 0x13: return "100 GJ"
    elif val == 0x14: return "W"
    elif val == 0x15: return "10 W"
    elif val == 0x16: return "100 W"
    elif val == 0x17: return "kW"
    elif val == 0x18: return "10 kW"
    elif val == 0x19: return "100 kW"
    elif val == 0x1A: return "MW"
    elif val == 0x1B: return "10 MW"
    elif val == 0x1C: return "100 MW"
    elif val == 0x1D: return "kJ/h"
    elif val == 0x1E: return "10 kJ/h"
    elif val == 0x1F: return "100 kJ/h"
    elif val == 0x20: return "MJ/h"
    elif val == 0x21: return "10 MJ/h"
    elif val == 0x22: return "100 MJ/h"
    elif val == 0x23: return "GJ/h"
    elif val == 0x24: return "10 GJ/h"
    elif val == 0x25: return "100 GJ/h"
    elif val == 0x26: return "ml"
    elif val == 0x27: return "10 ml"
    elif val == 0x28: return "100 ml"
    elif val == 0x29: return "l"
    elif val == 0x2A: return "10 l"
    elif val == 0x2B: return "100 l"
    elif val == 0x2C: return "m^3"
    elif val == 0x2D: return "10 m^3"
    elif val == 0x2E: return "m^3"
    elif val == 0x2F: return "ml/h"
    elif val == 0x30: return "10 ml/h"
    elif val == 0x31: return "100 ml/h"
    elif val == 0x32: return "l/h"
    elif val == 0x33: return "10 l/h"
    elif val == 0x34: return "100 l/h"
    elif val == 0x35: return "m^3/h"
    elif val == 0x36: return "10 m^3/h"
    elif val == 0x37: return "100 m^3/h"
    elif val == 0x38: return "1e-3 degrees C"
    elif val == 0x39: return "units for HCA"
    elif val == 0x3A: return "reserved"
    elif val == 0x3B: return "reserved"
    elif val == 0x3C: return "reserved"
    elif val == 0x3D: return "reserved"
    elif val == 0x3E: return "reserved but historic"
    elif val == 0x3F: return "without units"
    else: return "unknown"

def _addDataVariable(result, data):
    """parse a variable data header and add the data to the result"""
    result['Id'] = _bcd_decode(data.id_bcd, 4)
    result['Manufacturer'] = _decodeManufacturer(data.manufacturer)
    result['Version'] = data.version
    result['Medium'] = _dataVarMedium(data.medium)
    result['Status'] = data.status

def _decodeManufacturer(value):
    """extract the name of the manufacturer"""
    intVal = _int_decode(value, 2)
    char1 = str( unichr(((intVal>>10) & 0x001F) + 64))
    char2 = str(unichr(((intVal >> 5) & 0x001F) + 64))
    char3 = str(unichr((intVal & 0x001F) + 64))
    return "{}{}{}".format(char1, char2, char3)

def _dataVarMedium(data):
    """convert medium info to string"""
    if data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_OTHER:
        return "Other"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_OIL:
        return "Oil"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_ELECTRICITY:
        return "Electricity"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_GAS:
        return "Gas"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_HEAT_OUT:
        return "Heat: Outlet"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_STEAM:
        return "Steam"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_HOT_WATER:
        return "Hot water"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_WATER:
        return "Water"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_HEAT_COST:
        return "Heat Cost Allocator"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_COMPR_AIR:
        return "Compressed Air"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_COOL_OUT:
        return "Cooling load meter: Outlet"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_COOL_IN:
        return "Cooling load meter: Inlet"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_HEAT_IN:
        return "Heat: Inlet"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_HEAT_COOL:
        return "Heat / Cooling load meter"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_BUS:
        return "Bus/System"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_UNKNOWN:
        return "Unknown Medium"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_COLD_WATER:
        return "Cold water"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_DUAL_WATER:
        return "Dual water"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_PRESSURE:
        return "Pressure"
    elif data == mbusLow.MBUS_VARIABLE_DATA_MEDIUM_ADC:
        return "A/D Converter"
    elif data >= 0x10 and data <= 0x20:
        return "Reserved"
    else:
        return "Unknown medium ({})".format(data)

def _decodeFunction(val):
    """decode the function part from a var record"""
    if val == mbusLow.MBUS_DIB_DIF_MANUFACTURER_SPECIFIC:
        return 'Manufacturer specific'
    else:
        functionId = val & mbusLow.MBUS_DATA_RECORD_DIF_MASK_FUNCTION
        if functionId == 0:
            return 'Instantaneous value'
        elif functionId == 0x10:
            return 'Maximum value'
        elif functionId == 0x20:
            return 'Minimum value'
        elif functionId == 0x30:
            return 'Value during error state'
        else:
            return 'unkown'

def _decodeUnitPrefix(exp):
    if exp == 0: return ""
    elif exp == -3: return "m"
    elif exp == -6: return "my"
    elif exp == 1: return "10 "
    elif exp == 2: return "100 "
    elif exp == 3: return "k"
    elif exp == 4: return "10 k"
    elif exp == 5: return "100 k"
    elif exp == 6: return "M"
    elif exp == 9: return "T"
    else:
        return "1e{}".format(exp)

def _decodeVifUnitLookup(vif):
    """helper function for decoding the unit info"""
    val = vif & mbusLow.MBUS_DIB_VIF_WITHOUT_EXTENSION
    if 0x0 <= val <= 0x00+7:
        n = (vif & 0x07) - 3
        return "Energy ({}Wh)".format(_decodeUnitPrefix(n))
    elif 0x08 <= val <= 0x08+7:
        n = (vif & 0x07)
        return "Energy ({}J)".format(_decodeUnitPrefix(n))
    elif 0x18 <= val <= 0x18 + 7:
        n = (vif & 0x07)
        return "Mass ({}kg)".format(_decodeUnitPrefix(n-3))
    elif 0x28 <= val <= 0x28 + 7:
        n = (vif & 0x07)
        return "Power ({} W)".format(_decodeUnitPrefix(n - 3))
    elif 0x30 <= val <= 0x30 + 7:
        n = (vif & 0x07)
        return "Power ({}J/h)".format(_decodeUnitPrefix(n))
    elif 0x10 <= val <= 0x10 + 7:
        n = (vif & 0x07)
        return "Volume ({} m^3)".format(_decodeUnitPrefix(n-6))
    elif 0x38 <= val <= 0x38 + 7:
        n = (vif & 0x07)
        return "Volume flow ({} m^3/h)".format(_decodeUnitPrefix(n - 6))
    elif 0x40 <= val <= 0x40 + 7:
        n = (vif & 0x07)
        return "Volume flow ({} m^3/min)".format(_decodeUnitPrefix(n - 7))
    elif 0x48 <= val <= 0x48 + 7:
        n = (vif & 0x07)
        return "Volume flow ({} m^3/s)".format(_decodeUnitPrefix(n - 9))
    elif 0x50 <= val <= 0x50 + 7:
        n = (vif & 0x07)
        return "Mass flow ({} kg/h)".format(_decodeUnitPrefix(n - 3))
    elif 0x58 <= val <= 0x58 + 7:
        n = (vif & 0x07)
        return "Flow temperature ({} deg C)".format(_decodeUnitPrefix(n - 3))
    elif 0x5C <= val <= 0x5C + 3:
        n = (vif & 0x07)
        return "Return temperature ({} deg C)".format(_decodeUnitPrefix(n - 3))
    elif 0x68 <= val <= 0x68 + 3:
        n = (vif & 0x07)
        return "Pressure ({} bar)".format(_decodeUnitPrefix(n - 3))
    elif (0x20 <= val <= 0x20+3) or (0x24 <= val <= 0x24+3) or (0x70 <= val <= 0x70+3) or (0x74 <= val <= 0x74+3):
        if vif & 0x7C == 0x20:
            res = "On time "
        elif vif & 0x7C == 0x24:
            res = "Operating time "
        elif vif & 0x7C == 0x70:
            res = "Averaging Duration "
        else:
            res = "Actuality Duration "

        temp = vif & 0x03
        if temp == 0:
            return res + "(seconds)"
        elif temp == 1:
            return res + "(minutes)"
        elif temp == 2:
            return res + "(hours)"
        else:
            return res + "(days)"
    elif 0x6C <= val <= 0x6C + 1:
        if vif & 0x1:
            return "Time Point (time & date)"
        else:
            return "Time Point (date)"
    elif 0x60 <= val <= 0x60 + 3:
        n = (vif & 0x03)
        return "Temperature Difference ({} deg C)".format(_decodeUnitPrefix(n - 3))
    elif 0x64 <= val <= 0x64 + 3:
        n = (vif & 0x03)
        return "External temperature ({} deg C)".format(_decodeUnitPrefix(n - 3))
    elif val == 0x6E:
        return "Units for H.C.A."
    elif val == 0x6F:
        return "Reserved"
    elif val == 0x7C:
        return "Custom VIF"
    elif val == 0x78:
        return "Fabrication number"
    elif val == 0x7A:
        return "Bus Address"
    elif val == 0x7F or val == 0xFF:
        return "Manufacturer specific"
    else:
        return "Unkknown (VIF = {})".format(vif)

def _decodeUnit(vib):
    """extract the unit from the record"""
    if vib.vif == 0xFD or vib.vif == 0xFB:
        if vib.nvife == 0:
            return "Missing VIF extension"
        elif vib.vife[0] == 0x08 or vib.vife[0] == 0x88:
            return "Access Number (transmission count)"
        elif vib.vife[0] == 0x09 or vib.vife[0] == 0x89:
            return "Medium (as in fixed header)"
        elif vib.vife[0] == 0x0A or vib.vife[0] == 0x8A:
            return "Manufacturer (as in fixed header)"
        elif vib.vife[0] == 0x0B or vib.vife[0] == 0x8B:
            return "Parameter set identification"
        elif vib.vife[0] == 0x0C or vib.vife[0] == 0x8C:
            return "Model / Version"
        elif vib.vife[0] == 0x0D or vib.vife[0] == 0x8D:
            return "Hardware version"
        elif vib.vife[0] == 0x0E or vib.vife[0] == 0x8E:
            return "Firmware version"
        elif vib.vife[0] == 0x0F or vib.vife[0] == 0x8F:
            return "Software version"
        elif vib.vife[0] == 0x16:
            return "Password"
        elif vib.vife[0] == 0x17 or vib.vife[0] == 0x97:
            return "Error flags"
        elif vib.vife[0] == 0x10:
            return "Customer location"
        elif vib.vife[0] == 0x11:
            return "Customer"
        elif vib.vife[0] == 0x1A:
            return "Digital output (binary)"
        elif vib.vife[0] == 0x1B:
            return "Digital input (binary)"
        elif vib.vife[0] & 0x70 == 0x40:
            n = (vib.vife[0] & 0x0F)
            return "{} V".format(_decodeUnitPrefix(n-9))
        elif vib.vife[0] & 0x70 == 0x50:
            n = (vib.vife[0] & 0x0F)
            return "{} A".format(_decodeUnitPrefix(n-12))
        elif vib.vife[0] & 0xF0 == 0x70:
            return "Reserved VIF extension"
        else:
            return "Unrecognized VIF extension: {}".format(vib.vife[0])
    elif vib.vif == 0x7C:
        return str(vib.custom_vif)
    elif vib.vif == 0xFC and (vib.vife[0] & 0x78) == 0x70:
        n = (vib.vife[0] & 0x07)
        return "{} {}".format(_decodeUnitPrefix(n-6), vib.custom_vif)
    else:
        return _decodeVifUnitLookup(vib.vif)

def _dateTime_decode(data, size):
    """convert to date time (string)"""
    if size == 2:
        year = ((data[0] & 0xE0) >> 5) | ((data[1] & 0xF0) >> 1)
        return str(datetime(day=data[0] & 0x1F, month=(data[1] & 0x0F) - 1, year=year))
    else:
        if (data[0] & 0x80) == 0:        # is time value
            min = data[0] & 0x3F
            hour = data[1] & 0x1F
            day = data[2] & 0x1F
            month = (data[3] & 0x0F) - 1
            year = ((data[2] & 0xE0) >> 5) | ((data[3] & 0xF0) >> 1)
            time = datetime(year=year, month=month, day=day, hour=hour, minute=min)
            tz = get_localzone()
            if (data[1] & 0x80) == 1:               # daylight saving time
                return str(tz.localize(time, is_dst=True))
            else:
                return str(tz.localize(time, is_dst=False))

def _float_decode(data):
    """convert to float value"""
    temp = 0

    # for _HAS_NON_IEEE754_FLOAT
    #for x in range(4, 0, -1):
    #    temp = (temp << 8) + data[x-1]
    #sign = -1 if (temp >> 31) == True else 1
    #exponent = ((temp & 0x7F800000) >> 23) - 127
    #fraction = temp & 0x007FFFFF
    #if (exponent != -127) and (exponent != 128):    # normalized value, add bit 24
    #    fraction |= 0x800000
    #return sign * fraction * pow(2.0, -23.0 + exponent)
    return struct.unpack('!f', data[0:4])[0]


def _decodeValue(result, record):
    """extract the nr of bytes and value from the record and store it int he result."""
    vif = record.drh.vib.vif & mbusLow.MBUS_DIB_VIF_WITHOUT_EXTENSION
    vife = record.drh.vib.vife[0] & mbusLow.MBUS_DIB_VIF_WITHOUT_EXTENSION

    switch = record.drh.dib.dif & mbusLow.MBUS_DATA_RECORD_DIF_MASK_DATA
    result["Encoding"] = ValueEncode(switch)
    if switch == 0: return
    elif switch == 0x01:    # 8 bit int
        result["Value"] = _int_decode(record.data, 1)
    elif switch == 0x02:  # 16 bit int
        if vif == 0x6C:
            result["Encoding"] = 0x6C
            result["Value"] = _dateTime_decode(record.data, 2)
        else:
            result["Value"] = _int_decode(record.data, 2)
    elif switch == 0x03:
        result["Value"] = _int_decode(record.data, 3)
    elif switch == 0x04:  # 16 bit int
        if vif == 0x6D or (record.drh.vib.vif == 0xFD and  vife == 0x30)  or  (record.drh.vib.vif == 0xFD and  vife == 0x70) :
            result["Encoding"] = 0x6D
            result["Value"] = _dateTime_decode(record.data, 4)
        else:
            result["Value"] = _int_decode(record.data, 4)
    elif switch == 0x05:
        result["Value"] = _float_decode(record.data)
    elif switch == 0x06:  # 6 byte int
        result["Value"] = _int_decode(record.data, 6)
    elif switch == 0x07:  # 8 byte int
        result["Value"] = _int_decode(record.data, 8)
    elif switch == 0x09:  # 2 digit bcd (8 bit)
        result["Value"] = _bcd_decode(record.data, 1)
    elif switch == 0x0A:  # 4 digit bcd (16 bit)
        result["Value"] = _bcd_decode(record.data, 2)
    elif switch == 0x0B:  # 6 digit bcd (24 bit)
        result["Value"] = _bcd_decode(record.data, 3)
    elif switch == 0x0C:  # 8 digit bcd (32 bit)
        result["Value"] = _bcd_decode(record.data, 4)
    elif switch == 0x0E:  # 12 digit bcd (48 bit)
        result["Value"] = _bcd_decode(record.data, 6)
    elif switch == 0x0F:  # hex
        result["Value"] = ' '.join('0x%02x' % b for b in record.data[0:record.data_len])
    elif switch == 0x0D:  # var length = string
        result["Value"] = ''.join([chr(x) for x in  record.data[0:record.data_len][::-1]])
    else:
        result["Value"] = None
        logger.error("Unknown DIF: {}".format(record.drh.dib.dif))

def __decodeRecord(record, full):
    """decode a single variable record"""
    result = {}
    if full:
        result['Function'] = _decodeFunction(record.drh.dib.dif)
        result['Unit'] = _decodeUnit(record.drh.vib)
    _decodeValue(result, record)
    return result

def _addVarRecords(data, full):
    """walk over every frame, convert every record in the frame"""
    frmCnt = 0
    records = []
    for frame in data:
        recCnt = 0
        if frame.data_var.record:
            record = frame.data_var.record
            while record:
                record = record.contents
                if record.drh.dib.dif != mbusLow.MBUS_DIB_DIF_MORE_RECORDS_FOLLOW:  # we skipt the 'more records follow' items
                    toAdd = None
                    try:
                        toAdd = __decodeRecord(record, full)
                        recCnt += 1
                    except:
                        logger.exception("failed to convert record nr {} in frame nr {}".format(recCnt, frmCnt))
                    records.append(toAdd)                           # if something went wrong, we add None, this way, the index nr is always correct.
                record = record.next
        frmCnt += 1
    return records
