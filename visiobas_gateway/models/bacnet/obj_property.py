from enum import Enum, unique


@unique
class ObjProperty(int, Enum):
    """Represent properties of BACnet object."""

    ACKED_TRANSITIONS = 0
    ACK_REQUIRED = 1
    ACTION = 2
    ACTION_TEXT = 3
    ACTIVE_TEXT = 4
    ACTIVE_VT_SESSIONS = 5
    ALARM_VALUE = 6
    ALARM_VALUES = 7
    ALL = 8
    ALL_WRITES_SUCCESSFUL = 9
    APDU_SEGMENT_TIMEOUT = 10
    APDU_TIMEOUT = 11
    APPLICATION_SOFTWARE_VERSION = 12
    ARCHIVE = 13
    BIAS = 14
    CHANGE_OF_STATE_COUNT = 15
    CHANGE_OF_STATE_TIME = 16
    NOTIFICATION_CLASS = 17
    # -- this property deleted(18),
    CONTROLLED_VARIABLE_REFERENCE = 19
    CONTROLLED_VARIABLE_UNITS = 20
    CONTROLLED_VARIABLE_VALUE = 21
    COV_INCREMENT = 22
    DATE_LIST = 23
    DAYLIGHT_SAVINGS_STATUS = 24
    DEADBAND = 25
    DERIVATIVE_CONSTANT = 26
    DERIVATIVE_CONSTANT_UNITS = 27
    DESCRIPTION = 28
    DESCRIPTION_OF_HALT = 29
    DEVICE_ADDRESS_BINDING = 30
    DEVICE_TYPE = 31
    EFFECTIVE_PERIOD = 32
    ELAPSED_ACTIVE_TIME = 33
    ERROR_LIMIT = 34
    EVENT_ENABLE = 35
    EVENT_STATE = 36
    EVENT_TYPE = 37
    EXCEPTION_SCHEDULE = 38
    FAULT_VALUES = 39
    FEEDBACK_VALUE = 40
    FILE_ACCESS_METHOD = 41
    FILE_SIZE = 42
    FILE_TYPE = 43
    FIRMWARE_REVISION = 44
    HIGH_LIMIT = 45
    INACTIVE_TEXT = 46
    IN_PROCESS = 47
    INSTANCE_OF = 48
    INTEGRAL_CONSTANT = 49
    INTEGRAL_CONSTANT_UNITS = 50
    # -- formerly: issue - confirmed - notifications(51), removed in version 1 revision 4.
    LIMIT_ENABLE = 52
    LIST_OF_GROUP_MEMBERS = 53
    LIST_OF_OBJECT_PROPERTY_REFERENCES = 54
    # -- enumeration value 55 is unassigned
    LOCAL_DATE = 56
    LOCAL_TIME = 57
    LOCATION = 58
    LOW_LIMIT = 59
    MANIPULATED_VARIABLE_REFERENCE = 60
    MAXIMUM_OUTPUT = 61
    MAX_APDU_LENGTH_ACCEPTED = 62
    MAX_INFO_FRAMES = 63
    MAX_MASTER = 64
    MAX_PRES_VALUE = 65
    MINIMUM_OFF_TIME = 66
    MINIMUM_ON_TIME = 67
    MINIMUM_OUTPUT = 68
    MIN_PRES_VALUE = 69
    MODEL_NAME = 70
    MODIFICATION_DATE = 71
    NOTIFY_TYPE = 72
    NUMBER_OF_APDU_RETRIES = 73
    NUMBER_OF_STATES = 74
    OBJECT_IDENTIFIER = 75
    OBJECT_LIST = 76
    OBJECT_NAME = 77
    OBJECT_PROPERTY_REFERENCE = 78
    OBJECT_TYPE = 79
    OPTIONAL = 80
    OUT_OF_SERVICE = 81
    OUTPUT_UNITS = 82
    EVENT_PARAMETERS = 83
    POLARITY = 84
    PRESENT_VALUE = 85
    PRIORITY = 86
    PRIORITY_ARRAY = 87
    PRIORITY_FOR_WRITING = 88
    PROCESS_IDENTIFIER = 89
    PROGRAM_CHANGE = 90
    PROGRAM_LOCATION = 91
    PROGRAM_STATE = 92
    PROPORTIONAL_CONSTANT = 93
    PROPORTIONAL_CONSTANT_UNITS = 94
    # -- formerly: protocol-conformance-class(95), removed in version 1 revision 2.
    PROTOCOL_OBJECT_TYPES_SUPPORTED = 96
    PROTOCOL_SERVICES_SUPPORTED = 97
    PROTOCOL_VERSION = 98
    READ_ONLY = 99
    REASON_FOR_HALT = 100
    # -- formerly: recipient(101), removed in version 1 revision 4.
    RECIPIENT_LIST = 102
    RELIABILITY = 103
    RELINQUISH_DEFAULT = 104
    REQUIRED = 105
    RESOLUTION = 106
    SEGMENTATION_SUPPORTED = 107
    SETPOINT = 108
    SETPOINT_REFERENCE = 109
    STATE_TEXT = 110
    STATUS_FLAGS = 111
    SYSTEM_STATUS = 112
    TIME_DELAY = 113
    TIME_OF_ACTIVE_TIME_RESET = 114
    TIME_OF_STATE_COUNT_RESET = 115
    TIME_SYNCHRONIZATION_RECIPIENTS = 116
    UNITS = 117
    UPDATE_INTERVAL = 118
    UTC_OFFSET = 119
    VENDOR_IDENTIFIER = 120
    VENDOR_NAME = 121
    VT_CLASSES_SUPPORTED = 122
    WEEKLY_SCHEDULE = 123
    ATTEMPTED_SAMPLES = 124
    AVERAGE_VALUE = 125
    BUFFER_SIZE = 126
    CLIENT_COV_INCREMENT = 127
    COV_RESUBSCRIPTION_INTERVAL = 128
    # -- formerly: current - notify - time(129), removed in version 1 revision 3.
    EVENT_TIME_STAMPS = 130
    LOG_BUFFER = 131
    LOG_DEVICE_OBJECT_PROPERTY = 132
    ENABLE = 133  # log - enable was renamed to enable in version 1 revision 5
    LOG_INTERVAL = 134
    MAXIMUM_VALUE = 135
    MINIMUM_VALUE = 136
    NOTIFICATION_THRESHOLD = 137
    # -- formerly: previous - notify - time(138), removed in version 1 revision 3.
    PROTOCOL_REVISION = 139
    RECORDS_SINCE_NOTIFICATION = 140
    RECORD_COUNT = 141
    START_TIME = 142
    STOP_TIME = 143
    STOP_WHEN_FULL = 144
    TOTAL_RECORD_COUNT = 145
    VALID_SAMPLES = 146
    WINDOW_INTERVAL = 147
    WINDOW_SAMPLES = 148
    MAXIMUM_VALUE_TIMESTAMP = 149
    MINIMUM_VALUE_TIMESTAMP = 150
    VARIANCE_VALUE = 151
    ACTIVE_COV_SUBSCRIPTIONS = 152
    BACKUP_FAILURE_TIMEOUT = 153
    CONFIGURATION_FILES = 154
    DATABASE_REVISION = 155
    DIRECT_READING = 156
    LAST_RESTORE_TIME = 157
    MAINTENANCE_REQUIRED = 158
    MEMBER_OF = 159
    MODE = 160
    OPERATION_EXPECTED = 161
    SETTING = 162
    SILENCED = 163
    TRACKING_VALUE = 164
    ZONE_MEMBERS = 165
    LIFE_SAFETY_ALARM_VALUES = 166
    MAX_SEGMENTS_ACCEPTED = 167
    PROFILE_NAME = 168
    AUTO_SLAVE_DISCOVERY = 169
    MANUAL_SLAVE_ADDRESS_BINDING = 170
    SLAVE_ADDRESS_BINDING = 171
    SLAVE_PROXY_ENABLE = 172
    LAST_NOTIFY_RECORD = 173
    SCHEDULE_DEFAULT = 174
    ACCEPTED_MODES = 175
    ADJUST_VALUE = 176
    COUNT = 177
    COUNT_BEFORE_CHANGE = 178
    COUNT_CHANGE_TIME = 179
    COV_PERIOD = 180
    INPUT_REFERENCE = 181
    LIMIT_MONITORING_INTERVAL = 182
    LOGGING_OBJECT = 183
    LOGGING_RECORD = 184
    PRESCALE = 185
    PULSE_RATE = 186
    SCALE = 187
    SCALE_FACTOR = 188
    UPDATE_TIME = 189
    VALUE_BEFORE_CHANGE = 190
    VALUE_SET = 191
    VALUE_CHANGE_TIME = 192
    ALIGN_INTERVALS = 193
    # -- enumeration value 194 is unassigned
    INTERVAL_OFFSET = 195
    LAST_RESTART_REASON = 196
    LOGGING_TYPE = 197
    # -- enumeration values 198 - 201 are unassigned
    RESTART_NOTIFICATION_RECIPIENTS = 202
    TIME_OF_DEVICE_RESTART = 203
    TIME_SYNCHRONIZATION_INTERVAL = 204
    TRIGGER = 205
    UTC_TIME_SYNCHRONIZATION_RECIPIENTS = 206
    NODE_SUBTYPE = 207
    NODE_TYPE = 208
    STRUCTURED_OBJECT_LIST = 209
    SUBORDINATE_ANNOTATIONS = 210
    SUBORDINATE_LIST = 211
    ACTUAL_SHED_LEVEL = 212
    DUTY_WINDOW = 213
    EXPECTED_SHED_LEVEL = 214
    FULL_DUTY_BASELINE = 215
    # -- enumeration values 216 - 217 are unassigned
    REQUESTED_SHED_LEVEL = 218
    SHED_DURATION = 219
    SHED_LEVEL_DESCRIPTIONS = 220
    SHED_LEVELS = 221
    STATE_DESCRIPTION = 222
    # -- enumeration values 223 - 225 are unassigned
    DOOR_ALARM_STATE = 226
    DOOR_EXTENDED_PULSE_TIME = 227
    DOOR_MEMBERS = 228
    DOOR_OPEN_TOO_LONG_TIME = 229
    DOOR_PULSE_TIME = 230
    DOOR_STATUS = 231
    DOOR_UNLOCK_DELAY_TIME = 232
    LOCK_STATUS = 233
    MASKED_ALARM_VALUES = 234
    SECURED_STATUS = 235
    # -- enumeration values 236 - 243 are unassigned
    ABSENTEE_LIMIT = 244
    ACCESS_ALARM_EVENTS = 245
    ACCESS_DOORS = 246
    ACCESS_EVENT = 247
    ACCESS_EVENT_AUTHENTICATION_FACTOR = 248
    ACCESS_EVENT_CREDENTIAL = 249
    ACCESS_EVENT_TIME = 250
    ACCESS_TRANSACTION_EVENTS = 251
    ACCOMPANIMENT = 252
    ACCOMPANIMENT_TIME = 253
    ACTIVATION_TIME = 254
    ACTIVE_AUTHENTICATION_POLICY = 255
    ASSIGNED_ACCESS_RIGHTS = 256
    AUTHENTICATION_FACTORS = 257
    AUTHENTICATION_POLICY_LIST = 258
    AUTHENTICATION_POLICY_NAMES = 259
    AUTHENTICATION_STATUS = 260
    AUTHORIZATION_MODE = 261
    BELONGS_TO = 262
    CREDENTIAL_DISABLE = 263
    CREDENTIAL_STATUS = 264
    CREDENTIALS = 265
    CREDENTIALS_IN_ZONE = 266
    DAYS_REMAINING = 267
    ENTRY_POINTS = 268
    EXIT_POINTS = 269
    EXPIRY_TIME = 270
    EXTENDED_TIME_ENABLE = 271
    FAILED_ATTEMPT_EVENTS = 272
    FAILED_ATTEMPTS = 273
    FAILED_ATTEMPTS_TIME = 274
    LAST_ACCESS_EVENT = 275
    LAST_ACCESS_POINT = 276
    LAST_CREDENTIAL_ADDED = 277
    LAST_CREDENTIAL_ADDED_TIME = 278
    LAST_CREDENTIAL_REMOVED = 279
    LAST_CREDENTIAL_REMOVED_TIME = 280
    LAST_USE_TIME = 281
    LOCKOUT = 282
    LOCKOUT_RELINQUISH_TIME = 283
    # -- formerly: master - exemption(284), removed in version 1 revision 13
    MAX_FAILED_ATTEMPTS = 285
    MEMBERS = 286
    MUSTER_POINT = 287
    NEGATIVE_ACCESS_RULES = 288
    NUMBER_OF_AUTHENTICATION_POLICIES = 289
    OCCUPANCY_COUNT = 290
    OCCUPANCY_COUNT_ADJUST = 291
    OCCUPANCY_COUNT_ENABLE = 292
    # -- formerly: occupancy - exemption(293), removed in version 1 revision 13
    OCCUPANCY_LOWER_LIMIT = 294
    OCCUPANCY_LOWER_LIMIT_ENFORCED = 295
    OCCUPANCY_STATE = 296
    OCCUPANCY_UPPER_LIMIT = 297
    OCCUPANCY_UPPER_LIMIT_ENFORCED = 298
    # -- formerly: passback - exemption(299), removed in version 1 revision 13
    PASSBACK_MODE = 300
    PASSBACK_TIMEOUT = 301
    POSITIVE_ACCESS_RULES = 302
    REASON_FOR_DISABLE = 303
    SUPPORTED_FORMATS = 304
    SUPPORTED_FORMAT_CLASSES = 305
    THREAT_AUTHORITY = 306
    THREAT_LEVEL = 307
    TRACE_FLAG = 308
    TRANSACTION_NOTIFICATION_CLASS = 309
    USER_EXTERNAL_IDENTIFIER = 310
    USER_INFORMATION_REFERENCE = 311
    # -- enumeration values 312 - 316 are unassigned
    USER_NAME = 317
    USER_TYPE = 318
    USES_REMAINING = 319
    ZONE_FROM = 320
    ZONE_TO = 321
    ACCESS_EVENT_TAG = 322
    GLOBAL_IDENTIFIER = 323
    # -- enumeration values 324 - 325 are unassigned
    VERIFICATION_TIME = 326
    BASE_DEVICE_SECURITY_POLICY = 327
    DISTRIBUTION_KEY_REVISION = 328
    DO_NOT_HIDE = 329
    KEY_SETS = 330
    LAST_KEY_SERVER = 331
    NETWORK_ACCESS_SECURITY_POLICIES = 332
    PACKET_REORDER_TIME = 333
    SECURITY_PDU_TIMEOUT = 334
    SECURITY_TIME_WINDOW = 335
    SUPPORTED_SECURITY_ALGORITHMS = 336
    UPDATE_KEY_SET_TIMEOUT = 337
    BACKUP_AND_RESTORE_STATE = 338
    BACKUP_PREPARATION_TIME = 339
    RESTORE_COMPLETION_TIME = 340
    RESTORE_PREPARATION_TIME = 341
    BIT_MASK = 342
    BIT_TEXT = 343
    IS_UTC = 344
    GROUP_MEMBERS = 345
    GROUP_MEMBER_NAMES = 346
    MEMBER_STATUS_FLAGS = 347
    REQUESTED_UPDATE_INTERVAL = 348
    COVU_PERIOD = 349
    COVU_RECIPIENTS = 350
    EVENT_MESSAGE_TEXTS = 351
    EVENT_MESSAGE_TEXTS_CONFIG = 352
    EVENT_DETECTION_ENABLE = 353
    EVENT_ALGORITHM_INHIBIT = 354
    EVENT_ALGORITHM_INHIBIT_REF = 355
    TIME_DELAY_NORMAL = 356
    RELIABILITY_EVALUATION_INHIBIT = 357
    FAULT_PARAMETERS = 358
    FAULT_TYPE = 359
    LOCAL_FORWARDING_ONLY = 360
    PROCESS_IDENTIFIER_FILTER = 361
    SUBSCRIBED_RECIPIENTS = 362
    PORT_FILTER = 363
    AUTHORIZATION_EXEMPTIONS = 364
    ALLOW_GROUP_DELAY_INHIBIT = 365
    CHANNEL_NUMBER = 366
    CONTROL_GROUPS = 367
    EXECUTION_DELAY = 368
    LAST_PRIORITY = 369
    WRITE_STATUS = 370
    PROPERTY_LIST = 371
    SERIAL_NUMBER = 372
    BLINK_WARN_ENABLE = 373
    DEFAULT_FADE_TIME = 374
    DEFAULT_RAMP_RATE = 375
    DEFAULT_STEP_INCREMENT = 376
    EGRESS_TIME = 377
    IN_PROGRESS = 378
    INSTANTANEOUS_POWER = 379
    LIGHTING_COMMAND = 380
    LIGHTING_COMMAND_DEFAULT_PRIORITY = 381
    MAX_ACTUAL_VALUE = 382
    MIN_ACTUAL_VALUE = 383
    POWER = 384
    TRANSITION = 385
    EGRESS_ACTIVE = 386
    DEVICE_ID = 846

    @property
    def id(self) -> int:
        return self.value
