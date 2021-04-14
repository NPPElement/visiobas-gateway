# BACnet properties and objects

## Gateway (device)

Создается девайс для шлюза. В нем определяются:

- `??` расписание
- `??` список id девайсов для опроса
- `??` время обновления шлюза (пере-авторизация, обновление данных об опрашиваемых девайсах)

При запуске шлюза, он посылает запрос на сервер для получения собственного объекта (по id).
Из этого объекта берется список id девайсов, которые опрашиваются этим шлюзом.

## Device

- `11 apduTimeout` таймаут для девайса ??
- `30 deviceAddressBinding` ip-адрес девайса или юнит (для ModbusRTU)
- `73 numberOfApduRetries` количество повторов, при неудачной попытке
    - Значение по умолчанию: 1 ??
- `98 protocolVersion` По какому протоколу опрашивается девайс
    - Пример: BACnet, ModbusRTU, ModbusTCP
- `116 timeSynchronizationRecipients` (Время синхронизации получателей)
    - Период отправки данные на сервер
    - Значение по умолчанию 60 ?? (сейчас 10)
- `371 propertyList` `internal_period` Период 'внутреннего' опроса девайса (если значение не
  изменилось, то не будет никуда отправлено)
    ~~- 118 updatePeriod есть не во всех датчиках. Возможно лучше оставить в 371~~
    - Пример 0.2 0.5 (в секундах).
- `153 backupFailureTimeout` (используется сервером) если шлюз не прислал данные на
  протяжении указанного периода — подсвечивается серым.
- `118 updateInterval` ~~340 restoreCompletionTime~~ период отправки девайса на сервер (
  Отправка происходит в любом случае. Даже если значения не менялись).
- `371 propertyList` Все параметры из `address_cache` и `rtu.yaml` хранятся в свойствах
  девайса.

## Object

- `104 relinquishDefault` ~~не опрашивать (опросить единожды при инициализации)~~
    - **БУДЕТ ИЗМЕНЕНО!**: ~~Значение по умолчанию, используемое в качестве текущего
      значения, если все значения массива приоритетов (Priority_Array) равны NULL (нулю)~~
    - The following example illustrates how a Lighting Output object may be used in a
      typical office scenario. Prior to 7:00 AM the lights are off as the Lighting Output
      object is being controlled at the relinquish default value (0.0%). At 7:00 AM a
      scheduler (e.g., a BACnet Schedule object or other automated process) turns the
      physical lights on by writing 100.0%
- `107 segmentationSupported` поддерживается ли несколько сегментов в 1-м запросе

## Modbus Object

- `371 propertyList`:
    - Для формулы (A*X) + B: Изменить `scale` (A) — умножать, а не делить. Также будет
      дополнительный параметр `offset` (B), который может прибавляться для коррекции.
    - Параметры `byteOrder` и `wordOrder`. По умолчанию они будут равны:
      старшим байтом вперед, старшим словом назад. Для обозначения используются символы
      `big` и `little`.
        - little endian — прямой порядок
        - big endian — обратный порядок
    - Для типа В float32 сейчас используются: `byteOrder`=`big`, `wordOrder`=`little`.
    - Для других типов: `byteOrder`=`little`, `wordOrder`=`big`

- `106 resolution` значение округляется с указанным шагом (Не количество знаков после
  запятой!).
    - Пример 0.1, 0.5, 1

Предлагаю ввести тип BIT (COIL) когда требуется только один бит ??
