from enum import Enum, unique
from typing import NamedTuple, Sequence


class StatusFlags:
    __slots__ = ('in_alarm', 'fault', 'overriden', 'out_of_service')

    # FIXME: Implement singletons

    def __init__(self, status_flags: list = None):
        if status_flags is None:
            self.in_alarm: bool = False
            self.fault: bool = False
            self.overriden: bool = False
            self.out_of_service: bool = False

        elif isinstance(status_flags, Sequence) and len(status_flags) == 4:
            self.in_alarm, self.fault, self.overriden, self.out_of_service = [bool(flag) for
                                                                              flag in
                                                                              status_flags]
        elif isinstance(status_flags, StatusFlags):
            self.in_alarm = status_flags.in_alarm
            self.fault: bool = status_flags.fault
            self.overriden: bool = status_flags.overriden
            self.out_of_service: bool = status_flags.out_of_service

        else:
            raise ValueError('Please, provide <list> with 4 flags or'
                             f'Provided: {status_flags} {type(status_flags)}')

    def __eq__(self, other):
        if isinstance(self, StatusFlags) and isinstance(other, StatusFlags):
            return self.as_binary == other.as_binary
        return False

    def __repr__(self):
        """ Uses to convert into number by binary coding"""
        return str(self.as_binary)

    @property
    def as_binary(self):
        return int(''.join([str(int(self.out_of_service)),
                            str(int(self.overriden)),
                            str(int(self.fault)),
                            str(int(self.in_alarm))]), base=2)

    def set(self,
            *,
            in_alarm: bool = None,
            fault: bool = None,
            overriden: bool = None,
            out_of_service: bool = None
            ) -> None:
        if in_alarm is not None:
            if isinstance(in_alarm, bool):
                self.in_alarm = in_alarm
            else:
                raise ValueError(f'Please provide bool value. Provided: {in_alarm}')
        if fault is not None:
            if isinstance(fault, bool):
                self.fault = fault
            else:
                raise ValueError(f'Please provide bool value. Provided: {fault}')
        if overriden is not None:
            if isinstance(overriden, bool):
                self.overriden = overriden
            else:
                raise ValueError(f'Please provide bool value. Provided: {overriden}')
        if out_of_service is not None:
            if isinstance(out_of_service, bool):
                self.out_of_service = out_of_service
            else:
                raise ValueError(f'Please provide bool value. Provided: {out_of_service}')


class ObjType(Enum):
    ANALOG_INPUT = "analog-input", 0, 'analogInput'
    ANALOG_OUTPUT = "analog-output", 1, 'analogOutput'
    ANALOG_VALUE = "analog-value", 2, 'analogValue'
    BINARY_INPUT = "binary-input", 3, 'binaryInput'
    BINARY_OUTPUT = "binary-output", 4, 'binaryOutput'
    BINARY_VALUE = "binary-value", 5, 'binaryValue'
    CALENDAR = "calendar", 6, 'calendar'
    COMMAND = "command", 7, 'command'
    DEVICE = "device", 8, 'device'
    EVENT_ENROLLMENT = "event-enrollment", 9, 'eventEnrollment'
    FILE = "file", 10, 'file'
    GROUP = "group", 11, 'group'
    LOOP = "loop", 12, 'loop'
    MULTI_STATE_INPUT = "multi-state-input", 13, 'multiStateInput'
    MULTI_STATE_OUTPUT = "multi-state-output", 14, 'multiStateOutput'
    NOTIFICATION_CLASS = "notification-class", 15, 'notificationClass'
    PROGRAM = "program", 16, 'program'
    SCHEDULE = "schedule", 17, 'schedule'
    AVERAGING = "averaging", 18, 'averaging'
    MULTI_STATE_VALUE = "multi-state-value", 19, 'multiStateValue'
    TREND_LOG = "trend-log", 20, 'trendLog'
    LIFE_SAFETY_POINT = "life-safety-point", 21, 'lifeSafetyPoint'
    LIFE_SAFETY_ZONE = "life-safety-zone", 22, 'lifeSafetyZone'
    ACCUMULATOR = "accumulator", 23, 'accumulator'
    PULSE_CONVERTER = "pulse-converter", 24, 'pulseConverter'
    ACCESS_POINT = "access-point", 33, 'accessPoint'
    SITE = "site", -1
    FOLDER = "folder", -1
    TRUNK = "trunk", -1
    GRAPHIC = "graphic", -1

    def __repr__(self):
        return f'ObjType.{self.name}'

    @property
    def id(self):
        return self.value[1]

    @property
    def name(self):
        return self.value[2]

    @property
    def name_dashed(self):
        return self.value[0]

    @property
    def properties(self):
        if self in {ObjType.BINARY_INPUT,
                    ObjType.ANALOG_INPUT,
                    ObjType.MULTI_STATE_INPUT
                    }:
            return (ObjProperty.presentValue,
                    ObjProperty.statusFlags
                    )
        elif self in {ObjType.BINARY_OUTPUT, ObjType.BINARY_VALUE,
                      ObjType.ANALOG_OUTPUT, ObjType.ANALOG_VALUE,
                      ObjType.MULTI_STATE_VALUE, ObjType.MULTI_STATE_OUTPUT
                      }:
            return (ObjProperty.presentValue,
                    ObjProperty.statusFlags,
                    ObjProperty.priorityArray
                    )
        else:
            raise NotImplementedError(f'Properties for type {self} not yet defined')


class BACnetObject(NamedTuple):
    type: ObjType
    id: int

    name: str
    resolution: float = None  # todo
    update_interval: int = None  # TODO: implement skip by update_interval


@unique
class ObjProperty(Enum):
    ackedTransitions = 0
    ackRequired = 1
    action = 2
    actionText = 3
    activeText = 4
    activeVtSessions = 5
    alarmValue = 6
    alarmValues = 7
    all = 8
    allWritesSuccessful = 9
    apduSegmentTimeout = 10
    apduTimeout = 11
    applicationSoftwareVersion = 12
    archive = 13
    bias = 14
    changeOfStateCount = 15
    changeOfStateTime = 16
    notificationClass = 17
    controlledVariableReference = 19
    controlledVariableUnits = 20
    controlledVariableValue = 21
    covIncrement = 22
    dateList = 23
    daylightSavingsStatus = 24
    deadBand = 25
    derivativeConstant = 26
    derivativeConstantUnits = 27
    description = 28
    descriptionOfHalt = 29
    deviceAddressBinding = 30
    deviceType = 31
    effectivePeriod = 32
    elapsedActiveTime = 33
    errorLimit = 34
    eventEnable = 35
    eventState = 36
    eventType = 37
    exceptionSchedule = 38
    faultValues = 39
    feedbackValue = 40
    fileAccessMethod = 41
    fileSize = 42
    fileType = 43
    firmwareRevision = 44
    highLimit = 45
    inactiveText = 46
    inProcess = 47
    instanceOf = 48
    integralConstant = 49
    integralConstantUnits = 50
    limitEnable = 52
    listOfGroupMembers = 53
    listOfObjectPropertyReferences = 54
    localDate = 56
    localTime = 57
    location = 58
    lowLimit = 59
    manipulatedVariableReference = 60
    maximumOutput = 61
    maxApduLengthAccepted = 62
    maxInfoFrames = 63
    maxMaster = 64
    maxPresValue = 65
    minimumOffTime = 66
    minimumOnTime = 67
    minimumOutput = 68
    minPresValue = 69
    modelName = 70
    modificationDate = 71
    notifyType = 72
    numberOfApduRetries = 73
    numberOfStates = 74
    objectIdentifier = 75
    objectList = 76
    objectName = 77
    objectPropertyReference = 78
    objectType = 79
    optional = 80
    outOfService = 81
    outputUnits = 82
    eventParameters = 83
    polarity = 84
    presentValue = 85
    priority = 86
    priorityArray = 87
    priorityForWriting = 88
    processIdentifier = 89
    programChange = 90
    programLocation = 91
    programState = 92
    proportionalConstant = 93
    proportionalConstantUnits = 94
    protocolObjectTypesSupported = 96
    protocolServicesSupported = 97
    protocolVersion = 98
    readOnly = 99
    reasonForHalt = 100
    recipientList = 102
    reliability = 103
    relinquishDefault = 104
    required = 105
    resolution = 106
    segmentationSupported = 107
    setPoint = 108
    setPointReference = 109
    stateText = 110
    statusFlags = 111
    systemStatus = 112
    timeDelay = 113
    timeOfActiveTimeReset = 114
    timeOfStateCountReset = 115
    timeSynchronizationRecipients = 116
    units = 117
    updateInterval = 118
    utcOffset = 119
    vendorIdentifier = 120
    vendorName = 121
    vtClassesSupported = 122
    weeklySchedule = 123
    attemptedSamples = 124
    averageValue = 125
    bufferSize = 126
    clientCovIncrement = 127
    covResubscriptionInterval = 128
    eventTimeStamps = 130
    logBuffer = 131
    logDeviceObjectProperty = 132
    enable = 133
    logInterval = 134
    maximumValue = 135
    minimumValue = 136
    notificationThreshold = 137
    protocolRevision = 139
    recordsSinceNotification = 140
    recordCount = 141
    startTime = 142
    stopTime = 143
    stopWhenFull = 144
    totalRecordCount = 145
    validSamples = 146
    windowInterval = 147
    windowSamples = 148
    maximumValueTimestamp = 149
    minimumValueTimestamp = 150
    varianceValue = 151
    activeCovSubscriptions = 152
    backupFailureTimeout = 153
    configurationFiles = 154
    databaseRevision = 155
    directReading = 156
    lastRestoreTime = 157
    maintenanceRequired = 158
    memberOf = 159
    mode = 160
    operationExpected = 161
    setting = 162
    silenced = 163
    trackingValue = 164
    zoneMembers = 165
    lifeSafetyAlarmValues = 166
    maxSegmentsAccepted = 167
    profileName = 168
    autoSlaveDiscovery = 169
    manualSlaveAddressBinding = 170
    slaveAddressBinding = 171
    slaveProxyEnable = 172
    lastNotifyRecord = 173
    scheduleDefault = 174
    acceptedModes = 175
    adjustValue = 176
    count = 177
    countBeforeChange = 178
    countChangeTime = 179
    covPeriod = 180
    inputReference = 181
    limitMonitoringInterval = 182
    loggingObject = 183
    loggingRecord = 184
    prescale = 185
    pulseRate = 186
    scale = 187
    scaleFactor = 188
    updateTime = 189
    valueBeforeChange = 190
    valueSet = 191
    valueChangeTime = 192
    alignIntervals = 193
    intervalOffset = 195
    lastRestartReason = 196
    loggingType = 197
    restartNotificationRecipients = 202
    timeOfDeviceRestart = 203
    timeSynchronizationInterval = 204
    trigger = 205
    utcTimeSynchronizationRecipients = 206
    nodeSubtype = 207
    nodeType = 208
    structuredObjectList = 209
    subordinateAnnotations = 210
    subordinateList = 211
    actualShedLevel = 212
    dutyWindow = 213
    expectedShedLevel = 214
    fullDutyBaseline = 215
    requestedShedLevel = 218
    shedDuration = 219
    shedLevelDescriptions = 220
    shedLevels = 221
    stateDescription = 222
    doorAlarmState = 226
    doorExtendedPulseTime = 227
    doorMembers = 228
    doorOpenTooLongTime = 229
    doorPulseTime = 230
    doorStatus = 231
    doorUnlockDelayTime = 232
    lockStatus = 233
    maskedAlarmValues = 234
    securedStatus = 235
    absenteeLimit = 244
    accessAlarmEvents = 245
    accessDoors = 246
    accessEvent = 247
    accessEventAuthenticationFactor = 248
    accessEventCredential = 249
    accessEventTime = 250
    accessTransactionEvents = 251
    accompaniment = 252
    accompanimentTime = 253
    activationTime = 254
    activeAuthenticationPolicy = 255
    assignedAccessRights = 256
    authenticationFactors = 257
    authenticationPolicyList = 258
    authenticationPolicyNames = 259
    authenticationStatus = 260
    authorizationMode = 261
    belongsTo = 262
    credentialDisable = 263
    credentialStatus = 264
    credentials = 265
    credentialsInZone = 266
    daysRemaining = 267
    entryPoints = 268
    exitPoints = 269
    expiryTime = 270
    extendedTimeEnable = 271
    failedAttemptEvents = 272
    failedAttempts = 273
    failedAttemptsTime = 274
    lastAccessEvent = 275
    lastAccessPoint = 276
    lastCredentialAdded = 277
    lastCredentialAddedTime = 278
    lastCredentialRemoved = 279
    lastCredentialRemovedTime = 280
    lastUseTime = 281
    lockout = 282
    lockoutRelinquishTime = 283
    maxFailedAttempts = 285
    members = 286
    musterPoint = 287
    negativeAccessRules = 288
    numberOfAuthenticationPolicies = 289
    occupancyCount = 290
    occupancyCountAdjust = 291
    occupancyCountEnable = 292
    occupancyLowerLimit = 294
    occupancyLowerLimitEnforced = 295
    occupancyState = 296
    occupancyUpperLimit = 297
    occupancyUpperLimitEnforced = 298
    passbackMode = 300
    passbackTimeout = 301
    positiveAccessRules = 302
    reasonForDisable = 303
    supportedFormats = 304
    supportedFormatClasses = 305
    threatAuthority = 306
    threatLevel = 307
    traceFlag = 308
    transactionNotificationClass = 309
    userExternalIdentifier = 310
    userInformationReference = 311
    userName = 317
    userType = 318
    usesRemaining = 319
    zoneFrom = 320
    zoneTo = 321
    accessEventTag = 322
    globalIdentifier = 323
    verificationTime = 326
    baseDeviceSecurityPolicy = 327
    distributionKeyRevision = 328
    doNotHide = 329
    keySets = 330
    lastKeyServer = 331
    networkAccessSecurityPolicies = 332
    packetReorderTime = 333
    securityPduTimeout = 334
    securityTimeWindow = 335
    supportedSecurityAlgorithms = 336
    updateKeySetTimeout = 337
    backupAndRestoreState = 338
    backupPreparationTime = 339
    restoreCompletionTime = 340
    restorePreparationTime = 341
    bitMask = 342
    bitText = 343
    isUtc = 344
    groupMembers = 345
    groupMemberNames = 346
    memberStatusFlags = 347
    requestedUpdateInterval = 348
    covuPeriod = 349
    covuRecipients = 350
    eventMessageTexts = 351
    eventMessageTextsConfig = 352
    eventDetectionEnable = 353
    eventAlgorithmInhibit = 354
    eventAlgorithmInhibitRef = 355
    timeDelayNormal = 356
    reliabilityEvaluationInhibit = 357
    faultParameters = 358
    faultType = 359
    localForwardingOnly = 360
    processIdentifierFilter = 361
    subscribedRecipients = 362
    portFilter = 363
    authorizationExemptions = 364
    allowGroupDelayInhibit = 365
    channelNumber = 366
    controlGroups = 367
    executionDelay = 368
    lastPriority = 369
    writeStatus = 370
    propertyList = 371
    serialNumber = 372
    blinkWarnEnable = 373
    defaultFadeTime = 374
    defaultRampRate = 375
    defaultStepIncrement = 376
    egressTime = 377
    inProgress = 378
    instantaneousPower = 379
    lightingCommand = 380
    lightingCommandDefaultPriority = 381
    maxActualValue = 382
    minActualValue = 383
    power = 384
    transition = 385
    egressActive = 386
    deviceId = 846

    @property
    def id(self):
        return self.value


if __name__ == '__main__':
    # fixme
    sf1 = StatusFlags()
    sf2 = StatusFlags()
    print(sf1 is sf2)
