# Scenario Configuration
All scenario generation is based on a configuration xml file. Each file contains a Collection of multiple Scenarios, each of which supports multiple configurations for leaks, sensors and sensorfaults. An example configuration can be found in `examples/config.xml`.

## Scenarios
Each config file needs to have a single `<ScenarioCollection>` tag at the top level. Within this collection, multiple scenarios can be defined using `<Scenario>` elements. It requires these attributes:

|Attribute      |Function                               |
|---------------|---------------------------------------|
|`name`         |Name of the scenario                   |
|`network`      |Path to the network inp file           |
|`iterations`   |Number of iterations to simulate       |
|`timeStep`     |Length of each iteration in seconds    |

*Note: When using realistic demands, the `timeStep` should equal the pattern time step defined in the network file. Otherwise the simulation results may contain sampling artifacts.*

*Note: If `timeStep` and the network file's pattern time step for realistic demands mismatch, incipient leaks are resampled using linear interpolation.*

Additionally, each `<Scenario>` requires exactly one child element of types `<LeakConfigs>`, `<SensorConfigs>` and `<SensorfaultConfigs>` each. These config collections can contain multiple configurations of the corresponding types.

An example scenario configuration may look like this:
```
<ScenarioCollection>
    <Scenario 
        name="MyScenario"
        network="MyNetwork.inp" 
        iterations="100"
        timeStep="300">
        <SensorConfigs> ... </SensorConfigs>
        <SensorfaultConfigs> ... </SensorfaultConfigs>
        <LeakConfigs> ... </LeakConfigs>
    </Scenario>
</ScenarioCollection>
```


## Leaks
Leaks can be defined on pipes or nodes. It is assumed, that a leak is a circular hole with a given diameter. For each leak, a start and an end time is given. There are two types of leaks:
* `abrupt` leaks are present in the same size for the whole duration of the leak. 
* `incipient` leaks feature a linear increase of the hole diameter from the start time to the peak time, and then remain constant in size

*Note:* Currently, only one `abrupt` leak is possible per part! As a workaround `incipient` leaks can be added where `start` = `peak`.

### Definition

Leaks are defined in the `<LeakConfigs>` collection of a scenario by including a `<LeakConfig>` element with a unique `name` attribute.

Within a leak config, multiple leaks can be defined by including `<Leak>` elements. They require the following attributes:

|Attribute          |Function                                                                           |
|-------------------|-----------------------------------------------------------------------------------|
|`pipeId`/`nodeId`  |Id of the leaky part                                                               |
|`type`             |Type of the leak, either `abrupt` or `incipient`                                   |
|`diameter`         |Diameter of the leak in m                                                          |
|`start`            |Index, at which the leak starts                                                    |
|`end`              |Index, at which the leak ends                                                      |
|`peak`             |Index, at which the leak reaches peak size (only required for `incipient` type)    |

An example leak config might look like this:
```
<LeakConfigs>
    <LeakConfig name="Baseline">
    </LeakConfig>
    <LeakConfig name="MyLeakConfig">
        <Leak
            pipeId="l1"
            type="incipient"
            diameter="0.1"
            start="5"
            end="15"
            peak="10"/>
        ...
    </LeakConfig>
    ...
</LeakConfigs>
```
Note, that a non-leaky baseline scenario can be simply defined by providing an empty leak config.


## Sensors
Sensors are defined on the corresponding parts, there are 3 kinds of sensors
* `pressure`: Measure pressure at a node
* `flow`: Measure flow through a link
* `demand`: Measure demand at a node

### Definition
Sensors are defined in the `<SensorConfigs>` collection of a scenario by including a `<SensorConfig>` element with a unique `name` attribute.

Within a sensor config, there is a collection of sensors of each type: `<PressureSensors>`, `<FlowSensors>` and `<DemandSensors>`. All of these tags must be present. If you do not want to define any sensor of a specific type, leave the corresponding tag empty.

Within each of these sensor collections, sensors are defined using a `<Sensor>` element. Each of them has an `id` attribute identifying the sensor this sensor is on.

An example sensor config might look like this:
```
<SensorConfigs>
    <SensorConfig name="MySensorConfig">
        <PressureSensors>
            <Sensor id="n1"/>
            ...
        </PressureSensors>
        <FlowSensors>
            <Sensor id="l1"/>
            ...
        </FlowSensors>
        <DemandSensors>
            <Sensor id="n1"/>
            ...
        </DemandSensors>
    </SensorConfig>
    ...
</SensorConfigs>
```


## Sensorfaults
Sensorfaults can be defined on any sensor. Each sensorfault is located by providing the component id and sensor type. It features a start and end time as well as the fault type and a fault parameter. There are 6 fault types:

|Fault Type     |Function                                                                   |
|---------------|---------------------------------------------------------------------------|
|`constant`     |The sensor is permanently stuck on `faultParam`                            |
|`drift`        |The sensor drifts away from its actual value by `faultParam` per iteration |
|`normal`       |The sensor experiences normal noise with std deviation `faultParam`        |
|`percentage`   |The sensor value is multiplied by `faultParam`                             |
|`shift`        |`faultParam` is added to the sensor value                                  |
|`stuckzero`    |The sensor is stuck at 0                                                   |

### Definition
Sensorfaults are defined in the `<SensorfaultConfigs>` collection of a scenario by including a `<SensorfaultConfig>` element with a unique `name` attribute.

Within a sensorfault config, multiple sensorfaults can be defined by including `<Sensorfault>` elements. They require the following attributes:

|Attribute      |Function                                                           |
|---------------|-------------------------------------------------------------------|
|`partId`       |Id of the part with the faulty sensor                              |
|`sensorType`   |Type of the faulty sensor                                          |
|`start`        |Index, at which the sensorfault starts                             |
|`end`          |Index, at which the sensorfault ends                               |
|`faultType`    |Type of the sensorfault, as described above                        |
|`faultParam`   |Parameter for the sensorfault (not required for `stuckzero` type)  |

An example sensorfault config might look like this:
```
<SensorfaultConfigs>
    <SensorfaultConfig name="GT">
    </SensorfaultConfig>
    <SensorfaultConfig name="MySensorfaultConfig">
        <Sensorfault
            partId="l1"
            sensorType="flow"
            start="5"
            end="10"
            faultType="constant"
            faultParam="1"/>
        ...
    </SensorfaultConfig>
    ...
</SensorfaultConfigs>
```
Note, that a ground truth scenario can be simply defined by providing an empty sensorfault config. If you do not want any sensorfaults, you still need to provide this ground truth config.

## Additional Notes
* All `name` attributes should be unique, even if they are for different categories
* `name` attributes shall not contain spaces or dots.
