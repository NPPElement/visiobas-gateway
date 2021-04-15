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
- `30 deviceAddressBinding` ip адрес девайса или юнит
    - Пример для BACnet: 11.22.33.44:5555
    - Пример для ModbusTCP: 11.22.33.44:5555
    - Пример для ModbusRTU: 1
- `73 numberOfApduRetries` количество повторов, при неудачной попытке
    - Значение по умолчанию: 1 ??
- `98 protocolVersion` По какому протоколу опрашивается девайс
    - Возможные значения: BACnet, ModbusRTU, ModbusTCP
- `116 timeSynchronizationRecipients` (Время синхронизации получателей)
    - Период отправки данные на сервер
    - Значение по умолчанию 60 ?? (сейчас 10)
- `118 updateInterval` ~~340 restoreCompletionTime~~ период отправки девайса на сервер (
  Отправка происходит в любом случае. Даже если значения не менялись).
  ~~- 118 updatePeriod есть не во всех датчиках. Возможно лучше оставить в 371~~
- `153 backupFailureTimeout` (для сервера) Если шлюз не прислал данные на протяжении
  указанного периода — подсвечивается серым.
- `371 propertyList` Все параметры из `address_cache` и `rtu.yaml` хранятся в свойствах
  девайса:
    - `internalPeriod` Период 'внутреннего' опроса девайса в секундах (если значение не
      изменилось, то не будет никуда отправлено) Пример: 0.2, 0.5
    - rtu
        - `rtu.port` Пример: /dev/ttyS0, /dev/ttyUSB0
        - `rtu.baudrate` 
          - Возможные значения: 600, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200
          - По умолчанию: 9600
        - `rtu.stopbits` По молчанию: 1
        - `rtu.bytesize` По умолчанию: 8
        - `rtu.timeout` По умолчанию: 1
        - `rtu.parity` По умолчанию: None

## Object

- `106 resolution` Значение округляется с указанным шагом
    - Пример 0.1, 0.5, 1

- `104 relinquishDefault` ~~не опрашивать (опросить единожды при инициализации)~~
    - **БУДЕТ ИЗМЕНЕНО!**: ~~Значение по умолчанию, используемое в качестве текущего
      значения, если все значения массива приоритетов (Priority_Array) равны NULL (нулю)~~
    - ~~ПРИЧИНА: The following example illustrates how a Lighting Output object may be used in a
      typical office scenario. Prior to 7:00 AM the lights are off as the Lighting Output
      object is being controlled at the relinquish default value (0.0%). At 7:00 AM a
      scheduler (e.g., a BACnet Schedule object or other automated process) turns the
      physical lights on by writing 100.0%~~
- `107 segmentationSupported` Поддерживается ли несколько сегментов в 1-м запросе

## Modbus Object

- `371 propertyList`:
    - modbus
        - `modbus.address` Адрес регистра
        - `modbus.quantity` Количество регистров
        - `modbus.functionRead` Функция для чтения
          - Пример: 0x03
        - `modbus.functionWrite` Функция для записи
          - По умолчанию: 0x06
        - `modbus.dataType` Тип значения
        - `modbus.dataLength` Используемое количество бит 
        - `modbus.scale` Для формулы `A*X+B`: Коэффициент A — умножать, а не делить.
        - `modbus.offset` Для формулы `A*X+B`: коэффициент B — прибавляется для коррекции.
        - `modbus.wordOrder` Порядок слов.
            - Возможные значения: `litte`, `big`
            - По умолчанию: `big` (старшим словом назад\обратный порядок)
                - Для FLOAT32: `little`
        - `modbus.byteOrder` Порядок байтов.
            - Возможные значения: `litte`, `big`
            - По умолчанию: `little` (старшим байтом вперед\прямой порядок)
                - Для FLOAT32: `big`

Предлагаю ввести тип BIT (COIL) когда требуется только один бит ??
