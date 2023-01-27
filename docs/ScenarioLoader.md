# Contents

  * [ScenarioCollection](#atmn.ScenarioLoader.ScenarioCollection)
    * [\_\_init\_\_](#atmn.ScenarioLoader.ScenarioCollection.__init__)
    * [list\_scenarios](#atmn.ScenarioLoader.ScenarioCollection.list_scenarios)
    * [get\_scenario](#atmn.ScenarioLoader.ScenarioCollection.get_scenario)
    * [list\_configs](#atmn.ScenarioLoader.ScenarioCollection.list_configs)
    * [get\_leak\_data](#atmn.ScenarioLoader.ScenarioCollection.get_leak_data)
    * [get\_sensorfault\_data](#atmn.ScenarioLoader.ScenarioCollection.get_sensorfault_data)
    * [get](#atmn.ScenarioLoader.ScenarioCollection.get)
  * [Scenario](#atmn.ScenarioLoader.Scenario)
    * [\_\_init\_\_](#atmn.ScenarioLoader.Scenario.__init__)
    * [list\_configs](#atmn.ScenarioLoader.Scenario.list_configs)
    * [get\_leak\_data](#atmn.ScenarioLoader.Scenario.get_leak_data)
    * [get\_sensorfault\_data](#atmn.ScenarioLoader.Scenario.get_sensorfault_data)
    * [get](#atmn.ScenarioLoader.Scenario.get)

<a id="atmn.ScenarioLoader.ScenarioCollection"></a>

# ScenarioCollection

```python
class ScenarioCollection()
```

<a id="atmn.ScenarioLoader.ScenarioCollection.__init__"></a>

## \_\_init\_\_

```python
def __init__(path)
```

Scenario Collection Constructor.

**Arguments**:

- `path`: Path to the scenario collection

<a id="atmn.ScenarioLoader.ScenarioCollection.list_scenarios"></a>

## list\_scenarios

```python
def list_scenarios()
```

List the scenarios present in the collection.

<a id="atmn.ScenarioLoader.ScenarioCollection.get_scenario"></a>

## get\_scenario

```python
def get_scenario(scenario_name)
```

Retrieve a scenario from the collection.

**Arguments**:

- `scenario_name`: The name of the scenario

**Returns**:

A Scenario object, or None if the Scenario does not exist within the collection

<a id="atmn.ScenarioLoader.ScenarioCollection.list_configs"></a>

## list\_configs

```python
def list_configs(scenario_name)
```

List configs for the given scenario.

**Arguments**:

- `scenario_name`: The name of the scenario

**Returns**:

A dictionary of config types, containing lists of the available configs

<a id="atmn.ScenarioLoader.ScenarioCollection.get_leak_data"></a>

## get\_leak\_data

```python
def get_leak_data(scenario_name, leak_config_name)
```

Retrieve the information about the leaks in a specific leak config in the given Scenario.

**Arguments**:

- `scenario_name`: The name of the scenario
- `leak_config`: The name of the leak config

**Returns**:

A list of dictionaries containing the leak information, None if no information was found

<a id="atmn.ScenarioLoader.ScenarioCollection.get_sensorfault_data"></a>

## get\_sensorfault\_data

```python
def get_sensorfault_data(scenario_name, sensorfault_config_name)
```

Retrieve the information about the sensorfaults in a specific sensorfault config in the given Scenario.

**Arguments**:

- `scenario_name`: The name of the scenario
- `sensorfault_config_name`: The name of the sensorfault config

**Returns**:

A list of dictionaries containing the sensorfault information, None if no information was found

<a id="atmn.ScenarioLoader.ScenarioCollection.get"></a>

## get

```python
def get(scenario_name, leak_config, sensor_config, sensorfault_config)
```

Retrieve specific measurements from the collection

**Arguments**:

- `scenario_name`: The name of the scenario
- `leak_config`: The name of the leak config
- `sensor_config`: The name of the sensor config
- `sensorfault_config`: The name of the sensorfault config

**Returns**:

A dictionary of measurement data frames, or None if the measurements do not exist within the collection

<a id="atmn.ScenarioLoader.Scenario"></a>

# Scenario

```python
class Scenario()
```

<a id="atmn.ScenarioLoader.Scenario.__init__"></a>

## \_\_init\_\_

```python
def __init__(path)
```

Scenario constructor.

**Arguments**:

- `path`: The path to the scenario

<a id="atmn.ScenarioLoader.Scenario.list_configs"></a>

## list\_configs

```python
def list_configs()
```

List configs of this scenario.

**Returns**:

A dictionary of config types, containing lists of the available configs

<a id="atmn.ScenarioLoader.Scenario.get_leak_data"></a>

## get\_leak\_data

```python
def get_leak_data(leak_config_name)
```

Retrieve the information about the leaks in a specific leak config.

**Arguments**:

- `leak_config`: The name of the leak config

**Returns**:

A list of dictionaries containing the leak information, None if no information was found

<a id="atmn.ScenarioLoader.Scenario.get_sensorfault_data"></a>

## get\_sensorfault\_data

```python
def get_sensorfault_data(sensorfault_config_name)
```

Retrieve the information about the sensorfaults in a specific sensorfault config.

**Arguments**:

- `sensorfault_config_name`: The name of the sensorfault config

**Returns**:

A list of dictionaries containing the sensorfault information, None if no information was found

<a id="atmn.ScenarioLoader.Scenario.get"></a>

## get

```python
def get(leak_config, sensor_config_name, sensorfault_config_name)
```

Retrieve specific measurements from this scenario.

**Arguments**:

- `leak_config`: The name of the leak config
- `sensor_config`: The name of the sensor config
- `sensorfault_config`: The name of the sensorfault config

**Returns**:

A dictionary of measurement data frames, or None if the measurements do not exist within the collection

