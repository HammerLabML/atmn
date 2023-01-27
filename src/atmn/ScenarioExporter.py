#!/usr/bin/env python3

from atmn.ScenarioLoader import ScenarioCollection
import os
import sys
import pandas as pd
import argparse

def run(args):
    """
    Run the scenario export script with the given command line args

    :param args: command line arguments
    """

    # Retrieve command line arguments
    collection_path = args.collection_path
    scenario_name = args.scenario_name
    leak_config_name = args.leak_config_name
    sensorconfig_name = args.sensorconfig_name
    sensorfault_config_name = args.sensorfault_config_name
    output = args.output if args.output.endswith('.xlsx') else f'{args.output}.xlsx'

    # Initialize scenario collection
    if not os.path.exists(collection_path):
        print(f'[ERROR] No collection found at "{collection_path}".')
        sys.exit(1)
    collection = ScenarioCollection(collection_path)

    # Check if scenario and configs exist within selection
    if scenario_name not in collection.list_scenarios():
        print(f'[ERROR] The specified collection does not include Scenario "{scenario_name}".')
        sys.exit(1)

    if leak_config_name not in collection.list_configs(scenario_name)['LeakConfigs']:
        print(f'[ERROR] Scenario "{scenario_name}" does not contain Leak Config "{leak_config_name}".')
        sys.exit(1)

    if sensorconfig_name not in collection.list_configs(scenario_name)['SensorConfigs']:
        print(f'[ERROR] Scenario "{scenario_name}" does not contain Sensor Config "{sensorconfig_name}".')
        sys.exit(1)

    if sensorfault_config_name not in collection.list_configs(scenario_name)['SensorfaultConfigs']:
        print(f'[ERROR] Scenario "{scenario_name}" does not contain Sensorfault Config "{sensorfault_config_name}".')
        sys.exit(1)

    # Retrieve Data
    data = collection.get(scenario_name, leak_config_name, sensorconfig_name, sensorfault_config_name)

    # Write measurements to excel file
    with pd.ExcelWriter(output) as writer:
        for sheet in data.keys():
            data[sheet].to_excel(writer, sheet_name=sheet)

    print(f'Successfully wrote {output}')

def configure_parser(parser):
    """
    Set up the parser for the command line arguments.

    :param parser: parser to set up
    """

    parser.add_argument('collection_path', help='Path to the Scenario Collection')
    parser.add_argument('scenario_name', help='Name of the Scenario')
    parser.add_argument('leak_config_name', help='Name of the Leak Config')
    parser.add_argument('sensorconfig_name', help='Name of the Sensor Config')
    parser.add_argument('sensorfault_config_name', help='Name of the Sensorfault Config')
    parser.add_argument('output', help='Path to the output xlsx file')

def main():
    """
    Execute the export script.
    """

    # Create argument parser
    parser = argparse.ArgumentParser(prog='atmn-export', description='Automation Toolbox for Machine learning in water Networks: Export Tool', epilog='For further documentation, see https://github.com/HammerLabML/atmn')

    # Configure the parser
    configure_parser(parser)

    # Parse arguments
    args = parser.parse_args()

    # Run exporter
    run(args)


if __name__ == '__main__':
    main()