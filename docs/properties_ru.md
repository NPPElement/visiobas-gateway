# Properties usage

## Contents

0. [Gateway](#Gateway)
    - [Gateway `propertyList`](#Gateway-propertyList)
1. [Device](#Device)
    - [Device `propertyList`](#Device-propertyList)
        - [ModbusRTU device `propertyList.rtu`](#ModbusRTU-device-propertyListrtu)
2. [Object](#Object)
    - [Modbus Object `propertyList.modbus`](#Modbus-object-propertyListmodbus)

## Gateway
|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`846 deviceId`|`int`|-|yes|-|Id шлюза
|`118 updatePeriod`|`int`|3600|-|-|Интервал обновления шлюза (пере-авторизация, обновление данных об опрашиваемых девайсах)
|`??`|TODO|-|TODO|-|Расписание

## Gateway `propertyList`
|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`device_ids`|`Json`|-|yes|-|Список id опрашиваемых девайсов

## Device

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`846 deviceId`|`int`|-|yes|-|Id девайса
|`371 propertyList`|`Json`|-|yes|-|См. таблицу ниже
|`11 apduTimeout`|`int`|TODO|-|-|TODO
|`73 numberOfApduRetries`|`int`|2|-|-|Количество повторов, при неудачной попытке
|`153 backupFailureTimeout`|`int`|TODO|-|-|(для сервера) Если шлюз не прислал данные на протяжении указанного периода — подсвечивается серым

- ~~116 timeSynchronizationRecipients~~ (Время синхронизации получателей)
    - Период отправки данные на сервер
    - По умолчанию `60` ?? (сейчас `10`)
- ~~118 updateInterval~~ ~~340 restoreCompletionTime~~ период отправки девайса на сервер (
  Отправка происходит в любом случае. Даже если значения не менялись).
  ~~- 118 updatePeriod есть не во всех датчиках. Возможно лучше оставить в 371~~

## Device `propertyList`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`protocol`|`str`|-|yes|'BACnet', 'ModbusTCP', 'ModbusRTU'|По какому протоколу опрашивается девайс
|`address`|`str`|-|for TCP|'10.20.30.40', ...|IP адрес девайса (для RTU не заполняется)
|`port`|`int`|depends on `protocol`|TODO|-|Порт
|`rtu`|`Json`|-|for RTU|-|Заполняется для `protocol`='ModbusRTU' (см. таблицу ниже)
|`internalPeriod`|`float`|TODO|-|-|Период 'внутреннего' опроса девайса в секундах (если значение не изменилось, то не будет отправлено)

## ModbusRTU device `propertyList.rtu`

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`unit`|`int`|-|yes|-|Номер девайса (юнит)
|`port`|`str`|-|yes|'/dev/ttyS0', '/dev/ttyUSB0', ...|Интерфейс девайса
|`baudrate`|`int`|19200|-|'600', '1200', '2400', '4800', '9600', '19200', '38400', '57600', '115200'|Скорость передачи
|`stopbits`|`int`|1|-|-|-
|`bytesize`|`int`|8|-|-|-
|`parity`|`str`|'N'|-| 'N', 'O', 'E'|-

- `371 propertyList` Все параметры из `address_cache` и `rtu.yaml` хранятся в свойствах
  девайса:
    - ~~rtu.retry_on_empty~~
        - ~~По умолчанию~~ `True`
    - ~~rtu.retry_on_invalid~~
        - ~~По умолчанию~~ `True`
    - ~~rtu.timeout~~ Используется 11-е свойство `apduTimeout`

 ---

## Object

|Property|Type|Default|Required|Possible|Description|
|--------|----|-------|--------|--------|-----------|
|`371 propertyList`|`Json`|-|for Modbus|-|См. таблицу ниже
|`106 resolution`|`float`|0.1|-|-|Значение округляется с указанным шагом
|`107 segmentationSupported`|`bool`|false|-|true, false|Поддерживается ли несколько сегментов в 1-м запросе.

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