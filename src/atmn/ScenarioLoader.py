import os
import hashlib
import errno
import lxml.etree
import pandas as pd
import numpy as np

class ScenarioCollection:

    def __init__(self, path):
        """
        Scenario Collection Constructor.

        :param path: Path to the scenario collection
        """
        self.path = os.path.abspath(path)
        if not os.path.exists(self.path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self.path)

    def list_scenarios(self):
        """
        List the scenarios present in the collection.
        """
        return list(filter(lambda scenario: os.path.isdir(os.path.join(self.path, scenario)), os.listdir(self.path)))

    def get_scenario(self, scenario_name):
        """
        Retrieve a scenario from the collection.

        :param scenario_name: The name of the scenario
        :returns: A Scenario object, or None if the Scenario does not exist within the collection
        """
        if scenario_name in self.list_scenarios():
            return Scenario(os.path.join(self.path, scenario_name))
        else:
            return None

    def list_configs(self, scenario_name):
        """
        List configs for the given scenario.

        :param scenario_name: The name of the scenario
        :returns: A dictionary of config types, containing lists of the available configs
        """
        if scenario_name in self.list_scenarios():
            return Scenario(os.path.join(self.path, scenario_name)).list_configs()
        else:
            return None

    def get_leak_data(self, scenario_name, leak_config_name):
        """
        Retrieve the information about the leaks in a specific leak config in the given Scenario.

        :param scenario_name: The name of the scenario
        :param leak_config: The name of the leak config
        :returns: A list of dictionaries containing the leak information, None if no information was found
        """
        if scenario_name in self.list_scenarios():
            return Scenario(os.path.join(self.path, scenario_name)).get_leak_data(leak_config_name)
        else:
            return None

    def get_sensorfault_data(self, scenario_name, sensorfault_config_name):
        """
        Retrieve the information about the sensorfaults in a specific sensorfault config in the given Scenario.

        :param scenario_name: The name of the scenario
        :param sensorfault_config_name: The name of the sensorfault config
        :returns: A list of dictionaries containing the sensorfault information, None if no information was found
        """
        if scenario_name in self.list_scenarios():
            return Scenario(os.path.join(self.path, scenario_name)).get_sensorfault_data(sensorfault_config_name)
        else:
            return None
        
    def get(self, scenario_name, leak_config, sensor_config, sensorfault_config):
        """
        Retrieve specific measurements from the collection

        :param scenario_name: The name of the scenario
        :param leak_config: The name of the leak config
        :param sensor_config: The name of the sensor config
        :param sensorfault_config: The name of the sensorfault config
        :returns: A dictionary of measurement data frames, or None if the measurements do not exist within the collection
        """
        if scenario_name in self.list_scenarios():
            return Scenario(os.path.join(self.path, scenario_name)).get(leak_config, sensor_config, sensorfault_config)
        else:
            return None

class Scenario:
    
    def __init__(self, path):
        """
        Scenario constructor.

        :param path: The path to the scenario
        """
        self.path = os.path.abspath(path)
        if not os.path.exists(self.path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self.path)

    def list_configs(self):
        """
        List configs of this scenario.

        :returns: A dictionary of config types, containing lists of the available configs
        """
        return {
            'LeakConfigs': os.listdir(os.path.join(self.path, 'measurements')),
            'SensorConfigs': list(map(lambda x: x[:-4], os.listdir(os.path.join(self.path, 'sensors')))),
            'SensorfaultConfigs': list(map(lambda x: x[:-4], os.listdir(os.path.join(self.path, 'sensorfaults'))))
        }

    def get_leak_data(self, leak_config_name):
        """
        Retrieve the information about the leaks in a specific leak config.

        :param leak_config: The name of the leak config
        :returns: A list of dictionaries containing the leak information, None if no information was found
        """

        # Create leak config path
        leak_config_path = os.path.join(self.path, 'leaks', f'{leak_config_name}.xml')

        # Return None if there is no information
        if not os.path.isfile(leak_config_path):
            return None

        # Read leak config and convert to list of dicts
        leak_config = lxml.etree.parse(leak_config_path).getroot()
        leaks = []
        for leak in leak_config:
            leaks.append({key: leak.attrib[key] for key in leak.attrib.iterkeys()})

        return leaks

    def get_sensorfault_data(self, sensorfault_config_name):
        """
        Retrieve the information about the sensorfaults in a specific sensorfault config.

        :param sensorfault_config_name: The name of the sensorfault config
        :returns: A list of dictionaries containing the sensorfault information, None if no information was found
        """

        # Create sensorfault config path
        sensorfault_config_path = os.path.join(self.path, 'sensorfaults', f'{sensorfault_config_name}.xml')

        # Return None if there is no information
        if not os.path.isfile(sensorfault_config_path):
            return None

        # Read sensorfault config and convert to list of dicts
        sensorfault_config = lxml.etree.parse(sensorfault_config_path).getroot()
        sensorfaults = []
        for sensorfault in sensorfault_config:
            sensorfaults.append({key: sensorfault.attrib[key] for key in sensorfault.attrib.iterkeys()})

        return sensorfaults

    def get(self, leak_config, sensor_config_name, sensorfault_config_name):
        """
        Retrieve specific measurements from this scenario.

        :param leak_config: The name of the leak config
        :param sensor_config: The name of the sensor config
        :param sensorfault_config: The name of the sensorfault config
        :returns: A dictionary of measurement data frames, or None if the measurements do not exist within the collection
        """

        # Check if all necessary configs are present
        configs = self.list_configs()
        if leak_config not in configs['LeakConfigs'] \
                or sensor_config_name not in configs['SensorConfigs'] \
                or sensorfault_config_name not in configs['SensorfaultConfigs']:
            return None

        # Read Sensor Config
        sensor_config = lxml.etree.parse(os.path.join(self.path, 'sensors', f'{sensor_config_name}.xml')).getroot()
        mask = {}
        for config in sensor_config:
            mask[config.tag] = []
            for sensor in config:
                mask[config.tag].append(sensor.attrib['id'])
        
        # Create path for measurements
        measurements_path = os.path.join(self.path, 'measurements', leak_config)

        # Check, if data is present as csv, alternatively assume pkl.
        if os.path.exists(os.path.join(measurements_path, 'demand.csv')):
            # Read measurements from csv
            data = {
                'demand': pd.read_csv(os.path.join(measurements_path, 'demand.csv'), index_col='time').loc[:,mask['DemandSensors']],
                'flow': pd.read_csv(os.path.join(measurements_path, 'flow.csv'), index_col='time').loc[:,mask['FlowSensors']],
                'pressure': pd.read_csv(os.path.join(measurements_path, 'pressure.csv'), index_col='time').loc[:,mask['PressureSensors']]
            }
        else:
            # Read measurements from pkl
            data = {
                'demand': pd.read_pickle(os.path.join(measurements_path, 'demand.pkl')).loc[:,mask['DemandSensors']],
                'flow': pd.read_pickle(os.path.join(measurements_path, 'flow.pkl')).loc[:,mask['FlowSensors']],
                'pressure': pd.read_pickle(os.path.join(measurements_path, 'pressure.pkl')).loc[:,mask['PressureSensors']]
            }

        # Read and apply Sensorfault config
        sensorfault_config = lxml.etree.parse(os.path.join(self.path, 'sensorfaults', f'{sensorfault_config_name}.xml')).getroot()

        # Create a numpy rng object to get repeatable 'normal' type faults.
        # Hash the sensor config file's contents as random seed
        with open(os.path.join(self.path, 'sensorfaults', f'{sensorfault_config_name}.xml')) as f:
            sensorfault_config_text = f.read()
        seed = int(hashlib.sha1(sensorfault_config_text.encode("utf-8")).hexdigest(), 16)
        rng = np.random.default_rng(seed)

        # Iterate through all sensorfaults
        for config in sensorfault_config:
            part_id = config.attrib['partId']
            sensor_type = config.attrib['sensorType']

            # Check if sensorfault is relevant for current sensor config
            if part_id not in data[sensor_type].columns:
                continue

            # Read sensorfault details
            start = int(config.attrib['start'])
            end = int(config.attrib['end'])
            fault_type = config.attrib['faultType']
            fault_param = float(config.attrib['faultParam']) if 'faultParam' in config.attrib.keys() else None

            # Make sure that the fault parameter is not None, except for stuckzero faults
            if fault_param is None and fault_type != 'stuckzero':
                print(f'ScenarioLoader: Missing fault parameter for {fault_type} fault on {part_id}! Skipping...')
                continue

            # Apply sensorfault to data
            data[sensor_type].loc[:,part_id] = _apply_sensorfault(data[sensor_type].loc[:,part_id], start, end, fault_type, fault_param, rng)

        return data


def _apply_sensorfault(df, start, end, fault_type, fault_param, rng):
    """
    Apply a sensorfault to the given measurements.
    This is a utility function designed to be used by the Scenario class.

    :param df: Dataframe of measurements to apply the fault to
    :param start: Start index of the fault
    :param end: End index of the fault
    :param fault_type: Type of the fault
    :param fault_param: Parameter of the fault
    :param rng: Numpy rng object, to ensure repeatable random faults
    :returns: The measurement dataframe with the sensorfaults applied
    """
    # Apply each fault according to its type
    if fault_type == 'constant':
        df.iloc[start:end] = fault_param
    elif fault_type == 'drift':
        step = np.arange(end-start) + 1
        df.iloc[start:end] += fault_param * step
    elif fault_type == 'normal':
        df.iloc[start:end] += rng.normal(1, fault_param, size=end-start)
    elif fault_type == 'percentage':
        df.iloc[start:end] *= fault_param
    elif fault_type == 'shift':
        df.iloc[start:end] += fault_param
    elif fault_type == 'stuckzero':
        df.iloc[start:end] = 0
    else:
        print(f'ScenarioLoader: Trying to apply invalid sensor fault type: {fault_type}')

    return df
