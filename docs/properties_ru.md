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

## Gateway

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`846 deviceId`|`int`|-|yes|-|Id шлюза
|`371 propertyList`|`JSON-str`|-|yes|-|См. таблицу ниже
|`118 updatePeriod`|`int`|3600|-|-|Интервал обновления шлюза в секундах (пере-авторизация, обновление данных об опрашиваемых девайсах)
|`??`|TODO|-|TODO|-|Расписание

## Gateway `propertyList`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`device_ids`|`JSON`|-|yes|[13,666,777], ...|Список id опрашиваемых девайсов

---

## Device

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`846 deviceId`|`int`|-|yes|-|Id девайса
|`371 propertyList`|`JSON-str`|-|yes|-|См. таблицу ниже
|`11 apduTimeout`|`int`|TODO|-|-|Таймаут
|`118 updateInterval`|`int`|60|-|-|Интервал полной отправки девайса на сервер (в любом случае)
|`73 numberOfApduRetries`|`int`|2|-|-|Количество повторов, при неудачной попытке
|`153 backupFailureTimeout`|`int`|TODO|-|-|(для сервера) Если шлюз не прислал данные на протяжении указанного периода — подсвечивается серым

- ~~116 timeSynchronizationRecipients (Время синхронизации получателей)~~

## Device `propertyList`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`protocol`|`str`|-|yes|'BACnet', 'ModbusTCP', 'ModbusRTU', 'ModbusRTUoverTCP'|По какому протоколу опрашивается девайс
|`address`|`str`|-|for TCP|'10.20.30.40', ...|IP адрес девайса
|`port`|`int`|-|for TCP|-|Порт
|`rtu`|`JSON`|-|for RTU|-|Заполняется для `protocol`='ModbusRTU' (см. таблицу ниже)
|`pollInterval`|`float`|0.5|-|-|Интервал 'внутреннего' опроса девайса в секундах (если значение не изменилось, то не будет отправлено)

## ModbusRTU device `propertyList.rtu`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`unit`|`int`|-|yes|-|Номер девайса (юнит)
|`port`|`str`|-|yes|'/dev/ttyS0', '/dev/ttyUSB0', ...|Интерфейс девайса
|`baudrate`|`int`|9600|-|'600', '1200', '2400', '4800', '9600', '19200', '38400', '57600', '115200'|Скорость передачи
|`stopbits`|`int`|1|-|-|-
|`bytesize`|`int`|8|-|-|-
|`parity`|`str`|'N'|-| 'N', 'O', 'E'|-

- ~~rtu.timeout~~ Используется 11-е свойство `apduTimeout`

 ---

## Object

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`371 propertyList`|`JSON-str`|-|for Modbus|-|См. таблицу ниже
|`106 resolution`|`float`|0.1|-|-|Значение округляется с указанным шагом
|`107 segmentationSupported`|`bool`|false|-|true, false|Поддерживается ли несколько сегментов в 1-м запросе.

## Object `propertyList`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`updateInterval`|`int`|`device.updateInterval`|-|-|Интервал отправки значения на сервер в секундах
|`pollInterval`|`float`|`device.propertyList.pollInterval`|-|-|Интервал 'внутреннего' опроса объекта в секундах (если значение не изменилось, то не будет отправлено)
|`modbus`|`JSON`|-|for Modbus|-|Заполняется для Modbus объектов (См. таблицу ниже)

## Modbus object `propertyList.modbus`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`address`|`int`|-|yes|-|Адрес регистра
|`dataType`|`str`|-|yes|'int', 'uint', 'float', 'bool', 'bits', 'string'|Тип значения
|`quantity`|`int`|1|-|-|Количество регистров
|`functionRead`|`str`|'0x04'|-|'0x01', '0x02', '0x03', '0x04'|Функция для чтения
|`functionWrite`|`str`|'0x06'|-|'0x05', '0x06', '0x15', '0x16'|Функция для записи
|`dataLength`|`int`|`quantity` * 16|-|-|Используемое количество бит
|`scale`|`float`|1.0|-|-|Для `A*X+B`: Коэффициент `A` — умножается для коррекции
|`offset`|`float`|0.0|-|-|Для `A*X+B`: Коэффициент `B` — прибавляется для коррекции
|`wordOrder`|`str`|depends on `dataType`|-|'big', 'little'|Порядок слов (см. под таблицей)
|`byteOrder`|`str`|depends on `dataType`|-|'big', 'little'|Порядок байтов (см. под таблицей)
|`repack`TODO|`bool`|false

- `modbus.wordOrder` Порядок слов.
    - По умолчанию: `big` (старшим словом назад\обратный порядок)
    - Для FLOAT32: `little`
- `modbus.byteOrder` Порядок байтов.
    - По умолчанию: `little` (старшим байтом вперед\прямой порядок)
        - Для FLOAT32: `big`

Предлагаю ввести тип BIT (COIL) когда требуется только один бит ??