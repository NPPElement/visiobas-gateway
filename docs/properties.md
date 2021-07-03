# Properties usage

## Contents

0. [Gateway](#Gateway)
    - [Gateway `propertyList`](#Gateway-propertyList)
1. [Device](#Device)
    - [Device `propertyList`](#Device-propertyList)
        - [ModbusRTU device `propertyList.rtu`](#ModbusRTU-device-propertyListrtu)
2. [Object](#Object)
    - [Object `propertyList`](#Object-propertyList)
        - [Modbus Object `propertyList.modbus`](#Modbus-object-propertyListmodbus)

## Properties usage may change. If you found that one, please, lookup properties limits and description in `gateway.models` package. Also you can pm me or make PR.

## Gateway

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`846 deviceId`|`int`|-|yes|-|Gateway identifier
|`371 propertyList`|`JSON-str`|-|yes|-|See table below
|`118 updatePeriod`|`int`|3600|-|-|Update interval in seconds (re-auth + update objects)
|`??`|TODO|-|TODO|-|Schedule

## Gateway `propertyList`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`device_ids`|`JSON`|-|yes|[13,666,777], ...|List of identifiers polling devices

---

## Device

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`846 deviceId`|`int`|-|yes|-|Device identifier
|`371 propertyList`|`JSON-str`|-|yes|-|See table below

|`153 backupFailureTimeout`|`int`|TODO|-|-|(для сервера) Если шлюз не прислал данные на
протяжении указанного периода — подсвечивается серым

## Device `propertyList`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`apduTimeout`|`int`|6000|-|-|Timeout in milliseconds. Serial devices requires timeout around 500ms.
|`numberOfApduRetries`|`int`|3|-|-|Retry number if requests failed.
|`protocol`|`str`|-|yes|'BACnet', 'ModbusTCP', 'ModbusRTU', 'ModbusRTUoverTCP', 'SUNAPI'|Used protocol.
|`address`|`str`|-|for TCP|'10.20.30.40', ...|IP address.
|`port`|`int`|-|for TCP|-|Port.
|`rtu`|`JSON`|-|for RTU|-|Required for `protocol`='ModbusRTU'. See table below.
|`pollPeriod`|`float`|90|-|-|Period in which the object will poll by gateway. If the object has changed, it sends to the server, otherwise it does not. Using by objects as default `pollPeriod` for them.
|`sendPeriod`|`int`|300|-|-|Period in which the object will be sent to the server, whether it has been changed. Using by objects as default `sendPeriod` for them.

## ModbusRTU device `propertyList.rtu`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`unit`|`int`|-|yes|-|Device unit number.
|`port`|`str`|-|yes|'/dev/ttyS0', '/dev/ttyUSB0', ...|Device interface (ex: serial).
|`baudrate`|`int`|9600|-|'600', '1200', '2400', '4800', '9600', '19200', '38400', '57600', '115200'|Speed of communication.
|`stopbits`|`int`|1|-|-|-
|`bytesize`|`int`|8|-|-|-
|`parity`|`str`|'N'|-| 'N', 'O', 'E'|-

 ---

## Object

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`371 propertyList`|`JSON-str`|-|for Modbus|-|See table below.
|`106 resolution`|`float`|0.1|-|-|`presentValue` rounds by this step.
|`107 segmentationSupported`|`bool`|false|-|true, false|Is object support several segments on one request..

## Object `propertyList`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`sendPeriod`|`int`|`device.propertyList.sendPeriod`|-|-|Period in which the object will be sent to the server, whether it has been changed.
|`pollPeriod`|`float`|`device.propertyList.pollPeriod`|-|-|Period in which the object will poll by gateway. If the object has changed, it sends to the server, otherwise it does not.
|`modbus`|`JSON`|-|for Modbus|-|Required for Modbus objects. See table below.

## Modbus object `propertyList.modbus`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`address`|`int`|-|yes|-|Register address.
|`dataType`|`str`|-|yes|'int', 'uint', 'float', 'bool', 'bits', 'string'|Type of `presentValue`.
|`quantity`|`int`|1|-|-|Number of registers.
|`functionRead`|`str`|'0x04'|-|'0x01', '0x02', '0x03', '0x04'|Function for read `presentValue`.
|`functionWrite`|`str`|'0x06'|-|'0x05', '0x06', '0x15', '0x16'|Function for write `presentValue`.
|`dataLength`|`int`|`quantity` * 16|-|-|Number of using bits.
|`scale`|`float`|1.0|-|-|For `A*X+B`: coefficient `A` — multiply for correction.
|`offset`|`float`|0.0|-|-|For `A*X+B`: coefficient `B` — add for correction.
|`wordOrder`|`str`|depends on `dataType`|-|'big', 'little'|Word order. See below
|`byteOrder`|`str`|depends on `dataType`|-|'big', 'little'|Byte order. See below.

- `modbus.wordOrder` Word order.
    - Default: `big` (Big endian\reverse order).
    - For FLOAT32: `big`
- `modbus.byteOrder` Byte order.
    - Default: `little` (Little endian\straight order).
    - For FLOAT32: `big`

TODO: add COIL type for one-bit values.