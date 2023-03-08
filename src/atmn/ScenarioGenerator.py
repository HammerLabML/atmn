#!/usr/bin/env python3

import os
import sys
import lxml.etree
import multiprocessing
import wntr
import numpy as np
import hashlib
import shutil
import psutil
import argparse
import alive_progress

verbose = 0

class ScenarioGenerator:

    def __init__(self, config_file, collection_path=None, force_regenerate=False, selection=None, n_threads=1, max_mem=None, dtype=None):
        """
        Scenario Generator Constructor.

        :param config_file: Path to the config file this generator uses
        :param collection_path: Directory for the generated scenario collection
        :param force_regenerate: Boolean flag, if true, present results are overwritten
        :param selection: Selection which scenarios to force, re-generate (Format: List of "SCENARIO.LEAK_CONFIG")
        :param n_threads: Number of threads to use, for single threaded use None
        :param max_mem: Maximum memory to use in parallel mode
        :param dtype: Datatype to save the measurement values with, either a numpy type or "csv"
        """

        # Check if config file exists
        self.config_path = os.path.abspath(config_file)
        if not os.path.isfile(self.config_path):
            print(f'[CRITICAL] Config file does not exist: "{self.config_path}".')
            sys.exit(1)

        # Retrieve command line parameters
        self.base_path = os.path.dirname(self.config_path)
        self.force_regenerate = force_regenerate
        self.selection = selection
        self.collection_path = os.path.abspath(collection_path) if collection_path else self.base_path
        self.n_threads = n_threads
        self.max_mem = max_mem
        self.dtype = dtype

        # Read and validate the config file
        self.read_config()

    def run(self):
        """
        Run the Scenario Generator. This writes all necessary configs and
        simulates all selected Scenarios.
        """

        if verbose > 1: print('Starting Scenario Generator...')

        # Get current memory usage as baseline, 5% safety margin
        process = psutil.Process(os.getpid())
        self.used_memory_baseline = (process.memory_info().rss * 1.05) // 1000

        # Calculate the available memory
        self.available_memory = self.max_mem - self.used_memory_baseline

        # Create sensor masks
        # They decide which measurements get saved to disk
        self.create_sensor_masks()

        # Write the actual configs and set up Simulation Jobs
        self.create_job_list_and_write_configs()
        self.n_jobs = len(self.job_list)

        # Simulate jobs
        print(f'Starting simulation for {self.n_jobs} jobs in {self.n_threads} threads...')

        # Set up process communication
        self.available_memory_shared = multiprocessing.Value('i', int(self.available_memory))
        self.memory_condition = multiprocessing.Condition()

        # Spawn a pool of workers and track using progress bar
        pool = multiprocessing.Pool(self.n_threads, Worker.init_worker, (self.available_memory_shared, self.memory_condition))
        with alive_progress.alive_bar(self.n_jobs) as progress:
            for _ in pool.imap_unordered(Worker.worker, self.job_list):
                progress()

        print(f'Done simulating {self.n_jobs} jobs.')

    def read_config(self):
        """
        Read and validate the config file.
        """

        if verbose: print('Reading Config...')

        # Read in config and schema
        xml_doc = lxml.etree.parse(self.config_path)
        xml_schema_doc = lxml.etree.parse(os.path.join(os.path.dirname(__file__), 'config_schema.xsd'))
        xml_schema = lxml.etree.XMLSchema(xml_schema_doc)

        # Remove comments from element tree
        comments = xml_doc.xpath('//comment()')
        for comment in comments:
            parent = comment.getparent()
            if parent is not None:
                parent.remove(comment)

        # Validate the config against the schema
        try:
            xml_schema.assertValid(xml_doc)
            self.scenarios = xml_doc.getroot()
        except Exception as e:
            print('[CRITICAL] Error parsing config:', e)
            sys.exit(1)

    def create_sensor_masks(self):
        """
        Create masks for each scenario and sensor type.
        These masks are used after simulation to determine, 
        which data is saved and which is not.
        """

        if verbose: print('Creating sensor masks...')

        # Initialize the empty sensor mask dict
        self.sensor_masks = {}
        for scenario in self.scenarios:
            # For each scenario, create an entry
            scenario_name = scenario.attrib['name']
            self.sensor_masks[scenario_name] = {
                'pressure': set(),
                'flow': set(),
                'demand': set()
            }
            # Read the Sensor config collection
            for config_collection in scenario:
                if config_collection.tag == 'SensorConfigs':
                    for sensor_config in config_collection:
                        # Within each collection, add all sensors from all sensor configs
                        for sensor_collection in sensor_config:
                            # Fill up the entry with the sensors from the corresponding type
                            sensor_type = sensor_collection.tag[:-7].lower()
                            for sensor in sensor_collection:
                                self.sensor_masks[scenario_name][sensor_type].add(sensor.attrib['id'])

    def create_job_list_and_write_configs(self):
        """
        Iterates through the entire config and (re)writes all necessary config
        files and creates simulation jobs.
        """

        if verbose: print('Adding simulation jobs...')

        # Initialize job list
        self.job_list = []

        # Keep track of lowest estimated memory size
        # We assume it is smaller than 1 PB :)
        lowest_estimated_memory = 10**12

        # Iterate through all scenarios
        for scenario in self.scenarios:
            scenario_name = scenario.attrib['name']
            network_path = scenario.attrib['network']
            network_path = network_path if os.path.isabs(network_path) \
                else os.path.join(self.base_path, network_path)
            scenario.attrib['network'] = network_path
            scenario_path = os.path.join(self.collection_path, scenario_name)

            # If whole scenario is force regenerated, remove it's whole folder structure
            if self.force_regenerate and self.is_selected(scenario_name, '*'):
                shutil.rmtree(scenario_path, ignore_errors=True)

            # If no leak config from this scenario is selected, continue with next one
            if not self.is_selected(scenario_name):
                continue

            # Initialize water network once to
            # * Validate
            # * Save topography
            # * Estimate memory consumption
            if verbose > 1: print(f'Validating {network_path}')
            wn = wntr.network.WaterNetworkModel(network_path)
            self.validate_wn(wn, network_path)
            self.write_topology(wn, scenario_path)
            estimated_memory = self.estimate_wn_memory(wn, scenario.attrib)
            lowest_estimated_memory = estimated_memory if estimated_memory < lowest_estimated_memory else lowest_estimated_memory
            if verbose > 1: print(f'Estimated memory: {estimated_memory}kB')
            wn = None

            # Skip this scenario, if its memory requirements would exceed the available memory
            if estimated_memory > self.available_memory:
                print(f'[ERROR] Estimated memory for scenario "{scenario_name}" exceeds the available memory. ({estimated_memory}kB > {self.available_memory}kB) Skipping...')
                continue

            ## Iterate through all configs within this scenario
            for config_collection in scenario:
                if config_collection.tag == 'SensorConfigs':
                    self.write_config_collection(config_collection, os.path.join(scenario_path, 'sensors'))
                elif config_collection.tag == 'SensorfaultConfigs':
                    self.write_config_collection(config_collection, os.path.join(scenario_path, 'sensorfaults'))
                elif config_collection.tag == 'LeakConfigs':                    
                    for leak_config in config_collection:

                        leak_config_name = leak_config.attrib['name']
                        measurements_path = os.path.join(scenario_path, 'measurements', leak_config_name)
                        leak_config_path = os.path.join(scenario_path, 'leaks')

                        # If leak config is force regenerated, remove its folder structure
                        if self.force_regenerate and self.is_selected(scenario_name, leak_config_name):
                            shutil.rmtree(measurements_path, ignore_errors=True)

                        # If this leak config is not selected, continue with next one
                        if not self.is_selected(scenario_name, leak_config_name):
                            continue
                        
                        # If measurements already exist, skip this simulation
                        # When forcing, this folder just got removed
                        if os.path.exists(measurements_path): 
                            continue
                        
                        # Convert leak config to list of leak dictionaries
                        leaks = []
                        for leak in leak_config:
                            leaks.append({key: leak.attrib[key] for key in leak.attrib.iterkeys()})

                        # Write config
                        self.write_config(leak_config, leak_config_path)

                        # Convert scenario_config to dict
                        scenario_dict = {key: scenario.attrib[key] for key in scenario.attrib.iterkeys()}

                        # Append simulation job to job list
                        if verbose: print(f'Adding: {scenario_name}.{leak_config_name}')
                        self.job_list.append(SimulationJob(scenario_dict, leaks, leak_config_name, self.sensor_masks[scenario_name], measurements_path, estimated_memory, self.dtype))
        
        # Clamp number of threads according to memory constraints
        practical_n_threads = int(self.available_memory // lowest_estimated_memory)
        if practical_n_threads < self.n_threads:
            self.n_threads = practical_n_threads
            print(f'Clamping threads to {self.n_threads} due to memory constraints...')


        if verbose: print('Done adding simulation jobs.')

    def validate_wn(self, wn, network_path):
        """
        Validate that the given water network does not contain illegal names.

        :param wn: The water network in question
        :param network_path: Path to the water network file
        """

        # Check for illegal link names
        illegal_names = [name for name in wn.links if name.startswith('leak_segment_')]
        if len(illegal_names) > 0:
            print(f'[WARNING] Some links in {network_path} are named like "leak_segment_*", this name might lead to unexpected behavior.')

        # Check for illegal node names
        illegal_names = [name for name in wn.nodes if name.startswith('leak_node_')]
        if len(illegal_names) > 0:
            print(f'[WARNING] Some nodes in {network_path} are named like "leak_node_*", this name might lead to unexpected behavior.')

    def estimate_wn_memory(self, wn, scenario):
        """
        Estimate the memory requirements for each job in this scenario in kB.

        :param wn: The water network in question
        :param scenario: Scenario this water network belongs to
        """

        # This formula is constructed from theory and validated empirically
        filesize = os.path.getsize(scenario['network']) // 1000
        n_nodes = len(wn.nodes)
        n_links = len(wn.links)
        iterations = int(scenario['iterations'])
        scenario_memory_kb = 0.15 * iterations * (n_nodes + n_links) + 40 * (n_nodes + n_links) + filesize
        return scenario_memory_kb

    def write_topology(self, wn, path):
        """
        Write the topology of the given water network to disk as XML.

        :param wn: The water network in question
        :param path: Path to write the topology XML
        """

        # Make sure the folder structure exists
        if not os.path.exists(path):
            os.makedirs(path)

        # Create XML Tree
        xml_root = lxml.etree.Element("Network")
        xml_nodes = lxml.etree.SubElement(xml_root, "Nodes")
        xml_links = lxml.etree.SubElement(xml_root, "Links")

        # Populate nodes
        for node_name in wn.nodes:
            node = wn.get_node(node_name)
            lxml.etree.SubElement(xml_nodes, "Node", id=node_name, type=node.node_type, x=str(node.coordinates[0]), y=str(node.coordinates[1]))

        # Populate links
        for link_name in wn.links:
            link = wn.get_link(link_name)
            lxml.etree.SubElement(xml_links, "Link", id=link_name, type=link.link_type, n1=link.start_node_name, n2=link.end_node_name)

        # Write XML
        xml = lxml.etree.ElementTree(xml_root)
        self.write_xml_warn_if_changed(xml, os.path.join(path, 'topology.xml'))

    def write_config(self, config, path):
        """
        Write a given XML config to disk.

        :param config: Config to write
        :param path: Path to write the config XML
        """

        config_name = config.attrib['name']
        config_path = os.path.join(path, f'{config_name}.xml')

        # Make sure the folder structure exists
        if not os.path.exists(path):
            os.makedirs(path)
        
        # Write new config
        xml = lxml.etree.ElementTree(config)
        self.write_xml_warn_if_changed(xml, config_path)

    def write_config_collection(self, config_collection, path):
        """
        Write all configs from a config collection to disk.

        :param config_collection: Config collection to write
        :param path: Path to write the config XMLs
        """

        # Write all configs
        for config in config_collection:
            self.write_config(config, path)
            
    def write_xml_warn_if_changed(self, xml, file_path):
        """
        Write an XML file to disk. If it already existed beforehand and the 
        new version differs, print a warning.

        :param xml: XML file to write
        :param path: Path to write the XML file to
        """

        if verbose > 1: print(f'Writing config: {file_path}')

        # Get hash of existing file
        old_file_hash = None
        if os.path.exists(file_path):
            with open(file_path) as f:
                old_file_hash = hashlib.md5(f.read().encode('utf-8')).digest()

        # Write new file
        xml.write(file_path, xml_declaration=True)

        # Check for equivalence with previous file
        if old_file_hash is not None:
            with open(file_path) as f:
                new_file_hash = hashlib.md5(f.read().encode('utf-8')).digest()
            # If hashes differ, print a warning
            if new_file_hash != old_file_hash:
                print(f'[WARNING] File {file_path} has changed. The corresponding scenario has not been regenerated in its entirety. This might mean that this file now is inconsistent with previously simulated leak configs.')

    def is_selected(self, scenario_name, leak_config_name=None):
        """
        Helper to check, whether a config is selected using the "--selection" 
        command line argument. If no "--selection" is given, always return True.

        :param scenario_name: The name of the scenario
        :param leak_config_name: The name of the leak configuration; use "*" to
                check if whole scenario is selected; leave empty to check if 
                any leak config of the scenario is selected
        :returns: Whether the given scenario and leak config are selected
        """

        # Empty selection means everything is selected implicitly
        if self.selection is None:
            return True

        # Check if any leak config is selected if only scenario name is given
        if leak_config_name is None:
            return any([sel.startswith(f'{scenario_name}.') for sel in self.selection])

        # Check if specific config is selected
        if f'{scenario_name}.{leak_config_name}' in self.selection \
            or f'{scenario_name}.*' in self.selection:
            return True

        # The current configuration is not selected
        return False


class SimulationJob:

    def __init__(self, scenario_config, leaks, leak_config_name, sensor_mask, results_path, memory_estimate, dtype):
        """
        Simulation Job constructor.

        :param scenario_config: A dictionary containing the scenario config
        :param leaks: A list of dictionaries describing the leaks
        :param leak_config_name: The name of the leak config
        :param sensor_mask: A mask to determine, which sensors to save an which not
        :param results_path: Path where to save the simulation results
        :param memory_estimate: Estimation of this jobs maximum memory requirements
        :param dtype: Datatype to save the measurement values with, either a numpy type or "csv"
        """

        # Save attributes
        self.scenario_config = scenario_config
        self.leaks = leaks
        self.leak_config_name = leak_config_name
        self.sensor_mask = sensor_mask
        self.results_path = results_path
        self.memory_estimate = memory_estimate
        self.dtype = dtype

    def init(self):
        '''
        Initialize this job.
        This entails initializing the water network and inserting leaks.

        :returns: True if init was successful, False otherwise
        '''

        # Extract params
        network_path = self.scenario_config['network']
        self.iterations = int(self.scenario_config['iterations'])
        self.time_step = int(self.scenario_config['timeStep'])

        # Initialize water network
        if verbose > 1: print(f'Initializing {self.scenario_config["name"]}.{self.leak_config_name}', flush=True)
        self.wn = wntr.network.WaterNetworkModel(network_path)
        self.wn.options.hydraulic.demand_model = 'PDD'
        self.wn.options.time.duration = self.iterations * self.time_step

        self.wn.options.time.hydraulic_timestep = self.time_step
        self.wn.options.time.report_timestep = self.time_step

        # Add leaks
        for leak in self.leaks:
            if not self.insert_leak(leak):
                return False

        return True

    def insert_leak(self, leak_info):
        """
        Insert a leak into the water network.

        :param leak_info: dictionary containing the leak information
        :returns: True if leak was successfully added, False otherwise
        """

        leak_type = leak_info['type']
        diameter = float(leak_info['diameter'])
        i_start = int(leak_info['start'])
        i_end = int(leak_info['end'])
        i_peak = int(leak_info['peak']) if 'peak' in leak_info.keys() else None

        # Check if peak time is given for incipient leaks
        if leak_type == 'incipient' and i_peak == None:
            print('[ERROR] Incipient leak lacking "peak" parameter.', flush=True)
            return False

        #Get leaky node
        if 'nodeId' in leak_info.keys():
            leak_node_name = leak_info['nodeId']

            # Incipient leaks are modeled using pressure dependent demand
            # To not mess up the pressure independent demand of the node, 
            # create a new node at distance 0 for the leak demand
            if leak_type == 'incipient':
                original_leak_node_name = leak_node_name
                leak_node_name = f'leak_node_{original_leak_node_name}'
                if leak_node_name not in self.wn.node_name_list:
                    # Create new, if not exists already
                    self.wn.add_junction(leak_node_name, elevation=self.wn.get_node(original_leak_node_name).elevation)
                    self.wn.add_pipe(f'leak_segment_{leak_node_name}', start_node_name=original_leak_node_name, end_node_name=leak_node_name, length=0, diameter=100, roughness=1, minor_loss=0)
        elif 'pipeId' in leak_info.keys():
            leak_pipe_name = leak_info['pipeId']
            # If part is a pipe, split the pipe and insert leaky node in the middle
            leak_node_name = f'leak_node_{leak_pipe_name}'
            if leak_node_name not in self.wn.node_name_list:
                # Create new, if not exists already
                pipe_new = f'leak_segment_{leak_pipe_name}'
                wntr.morph.split_pipe(self.wn, leak_pipe_name, pipe_new, leak_node_name, return_copy=False)
        else:
            print('[ERROR] Leak missing required parameter: "nodeId" or "pipeId".', flush=True)
            return False
        
        # Assign leak node to variable
        leak_node = self.wn.get_node(leak_node_name)

        # handle different leak types
        if leak_type == 'incipient':

            # Demand formula as also used in wntr:
            # discharge coeff * sqrt(2/1000) * water density * area
            # Below required and minimum pressure are used together with
            # this formula for pressure dependent demand

            # Pressure at which the leak is saturated
            leak_node.required_pressure = 100
            # Pressure at which the leak starts loosing water
            leak_node.minimum_pressure = 0

            # Ramp-up
            # When computing the radii, we go from step to diameter/2 + step * 0.5
            # The final step is multiplied by 0.5 for numerical stability (otherwise one too many samples may be generated)
            if i_peak == i_start:
                leak_ramp_up = np.array([])
            else:
                leak_radius_step = diameter / (i_peak - i_start) / 2
                leak_radii = np.arange(leak_radius_step, diameter/2 + leak_radius_step * 0.5 , leak_radius_step)
                leak_ramp_up = 0.75 * np.sqrt(2 / 1000) * 990.27 * np.pi * leak_radii ** 2

            # Constant demand
            leak_area = np.pi * (diameter / 2) ** 2
            leak_demand_constant = 0.75 * np.sqrt(2 / 1000) * 990.27 * leak_area

            # Create array of demands
            pattern = np.zeros(self.iterations)
            pattern[i_start:i_peak] = leak_ramp_up
            pattern[i_peak:i_end] = leak_demand_constant

            # Resample if pattern timestep mismatches simulation time step
            if self.wn.options.time.pattern_timestep != self.time_step:
                scaling_factor = self.wn.options.time.pattern_timestep / self.time_step
                stretched_max = self.iterations * self.wn.options.time.pattern_timestep
                pattern = np.interp(np.arange(0, stretched_max, scaling_factor), np.arange(0, pattern.shape[0]), pattern)

            # Create unique pattern name
            pattern_name = f'leak_pattern_{leak_node_name}'
            pattern_id = 1
            while pattern_name in self.wn.pattern_name_list:
                pattern_name = f'leak_pattern_{leak_node_name}_{pattern_id}'
                pattern_id += 1

            # Add pattern
            self.wn.add_pattern(pattern_name, pattern)
            leak_node.add_demand(1, pattern_name)

        elif leak_type == 'abrupt':
            # Inserting an abrupt leak using the add_leak method
            # Note: Currently only one leak is possible.
            leak_area = np.pi * (diameter / 2) ** 2
            leak_node.add_leak(self.wn, discharge_coeff=0.75, area=leak_area, start_time=i_start * self.time_step, end_time=i_end * self.time_step)
        else:
            print(f'[ERROR] Encountered invalid leak type: "{leak_type}".', flush=True)
            return False

        return True

    def simulate(self):
        """
        Simulate this job using the WNTRSimulator.
        """

        # Run simulation
        if verbose > 1: print(f'Start simulation of {self.scenario_config["name"]}.{self.leak_config_name}', flush=True)
        sim = wntr.sim.WNTRSimulator(self.wn)
        self.results = sim.run_sim()
        if verbose > 1: print(f'Done simulation of {self.scenario_config["name"]}.{self.leak_config_name}', flush=True)
    
    def save(self):      
        """
        Save the results of the simulation to disk.
        """

        if verbose > 1: print(f'Saving results for {self.scenario_config["name"]}.{self.leak_config_name}', flush=True)
        # Extract relevant results and apply save mask
        pressure = self.results.node['pressure'].loc[:,list(self.sensor_mask['pressure'])]
        pressure.index.name = 'time'
        demand = self.results.node['demand'].loc[:,list(self.sensor_mask['demand'])]
        demand.index.name = 'time'
        flow = self.results.link['flowrate'].loc[:,list(self.sensor_mask['flow'])]
        flow.index.name = 'time'

        # Create folder structure
        if not os.path.exists(self.results_path):
            os.makedirs(self.results_path)

        # Save dataframes
        if self.dtype == 'csv':
            pressure.to_csv(os.path.join(self.results_path, 'pressure.csv'))
            flow.to_csv(os.path.join(self.results_path, 'flow.csv'))
            demand.to_csv(os.path.join(self.results_path, 'demand.csv'))
        else:
            pressure.astype(self.dtype).to_pickle(os.path.join(self.results_path, 'pressure.pkl'))
            flow.astype(self.dtype).to_pickle(os.path.join(self.results_path, 'flow.pkl'))
            demand.astype(self.dtype).to_pickle(os.path.join(self.results_path, 'demand.pkl'))
            
        if verbose > 1: print(f'Done saving results for {self.scenario_config["name"]}.{self.leak_config_name}', flush=True)


class Worker:

    def __init__(self):
        """
        Worker only contains static methods, do not initialize.
        """

        assert False, 'Worker only contains static methods, do not initialize.'

    def _reserve_memory(available_memory, memory):
        """
        Higher order function to be used as a predicate. It tries to reserve 
        memory from the multiprocessing.Value "available_memory", returns True
        if successful, otherwise false.

        :param available_memory: multiprocessing.Value that contains the available memory
        :param memory: Memory to reserve
        """

        # Define predicate
        def __reserve_memory():
            reserved = False
            with available_memory.get_lock():
                new_available_memory = available_memory.value - int(memory)
                if new_available_memory >= 0:
                    available_memory.value = new_available_memory
                    reserved = True
                    if verbose > 1: print(f'Some process reserved memory. Left: {available_memory.value}')

            return reserved

        # Return predicate
        return __reserve_memory

    def _unreserve_memory(available_memory, memory):
        """
        Unreserve memory, by adding "memory" to the shared variable "available_memory"

        :param available_memory: multiprocessing.Value memory to unreserve from
        :param memory: amount of memory to unreserve
        """

        with available_memory.get_lock():
            available_memory.value += int(memory)
            if verbose > 1: print(f'Some process unreserved memory. Left: {available_memory.value}')

    def init_worker(available_memory_param, condition_param):
        """
        Initialize the worker process by making shared variables available

        :param available_memory_param: multiprocessing.Value memory available for simulation jobs
        :param condition_param: wait condition for sufficient memory
        """

        global available_memory
        global condition

        available_memory = available_memory_param
        condition = condition_param

    def worker(job):
        """
        Worker to process a single SimulationJob

        :param job: multiprocessing.Queue containing the jobs
        """

        # Reserve memory for this job
        with condition:
            condition.wait_for(Worker._reserve_memory(available_memory, job.memory_estimate))
                
        # Initialize and simulate the jobs and save the results
        if not job.init():
            print(f'[ERROR] Could not initialize Scenario {job.scenario_config["name"]}.{job.leak_config_name}; Skipping...', flush=True)
            #self.tick_bar()
            return
        job.simulate()
        job.save()
                
        # After processing, unreserve memory and notify the other threads
        Worker._unreserve_memory(available_memory, job.memory_estimate)
        with condition:
            condition.notify_all()


def run(args):
    """
    Run the scenario generation script with the given command line args

    :param args: command line arguments
    """

    # Read args
    verbose = args.verbose
    config = args.config
    collection_path = args.collection_path
    force = args.force_regenerate
    selection = args.selection
    dtype = args.dtype

    # If thread number is given, us it. Otherwise use 1 if not parallel and os.cpu_count() if parallel
    n_threads = args.threads if args.threads is not None \
        else os.cpu_count() if args.parallel else 1
    
    # If max memory is given, use it. Otherwise, use 99% of available memory
    # Make sure to convert from MB to kB
    memory = args.max_memory * 1000 if args.max_memory is not None else psutil.virtual_memory().available * 0.99 // 1000

    # Check datatype validity and convert to datatype string
    if dtype not in ['8', '16', '32', '64', 'csv']:
        print(f'[WARNING] Unknown datatype "{dtype}", reverting to float16.')
    elif dtype != 'csv':
        dtype = f'float{dtype}'

    # Create Generator and run generations
    generator = ScenarioGenerator(config, collection_path=collection_path, force_regenerate=force, selection=selection, n_threads=n_threads, max_mem=memory, dtype=dtype)
    generator.run()

def configure_parser(parser):
    """
    Set up the parser for the command line arguments.

    :param parser: parser to set up
    """

    # Set up command line arguments
    parser.add_argument('config', help='Path to the Scenario Collection configuration file')
    parser.add_argument('collection_path', nargs='?', default=None, help='Path where simulation results are saved to (Default: Scenario Collection path)')
    parser.add_argument('-f', '--force-regenerate', action='store_true', help='Force existing simulations results to be re-generated')
    parser.add_argument('-s', '--selection', action='extend', nargs='*', help='Selection, which Scenarios and Leak Configurations should be generated in format "[SCENARIO].[LEAK_CONFIG]" where [LEAK_CONFIG] can use "*" as wildcard')
    parser.add_argument('-p', '--parallel', action='store_true', help='Enable parallelized simulation on all available cores')
    parser.add_argument('-t', '--threads', action='store', type=int, help='Specify a number of threads for parallelized simulation (Overwrites "-p")')
    parser.add_argument('-m', '--max-memory', action='store', type=int, help='Maximum memory this generator should consume in MB')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Enable verbose output, -vv for extra verbose')
    parser.add_argument('-d', '--dtype', action='store', type=str, default='16', help='Choose datatype to store measurements as. Either 16, 32 or 64 for the corresponding floating point precision or "csv" to save in csv format. Default: 16')

def main():
    """
    Execute the generator script.
    """
    
    # Create argument parser
    parser = argparse.ArgumentParser(prog='atmn-generate', description='Automation Toolbox for Machine learning in water Networks: Generator Tool', epilog='For further documentation, see https://github.com/HammerLabML/atmn')

    # Configure the parser
    configure_parser(parser)

    # Parse arguments
    args = parser.parse_args()

    # Run Generator
    run(args)


if __name__ == '__main__':
    main()