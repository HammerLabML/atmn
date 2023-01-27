import tempfile
import wntr
import plotly
import itertools
import os
import sys
import argparse
import lxml.etree


def plot_network(wn, leaks, sensorfaults, pressure_sensors, flow_sensors, demand_sensors, out_file, auto_open, plot_name):
    """
    Plot the given network including leaks, sensors and sensor faults.

    :param wn: Water network to plot
    :param leaks: List of leaks to plot
    :param sensorfaults: List of sensorfaults to plot
    :param pressure_sensors: List of pressure sensors to plot
    :param flow_sensors: List of flow sensors to plot
    :param demand_sensors: List of demand sensors to plot
    :param out_file: File to write the plot to
    :param auto_open: Boolean declaring if file should automatically be opened
    :param plot_name: Title of the plot
    """

    # Extract Graph from water network
    wn_graph = wn.get_graph()

    # Initialize edge information to plot
    edge_xs = []
    edge_ys = []
    edge_colors = []
    edge_label_xs = []
    edge_label_ys = []
    edge_label_labels = []
    edge_label_popups = []

    # Add all edges
    for edge_name, edge in itertools.chain(wn.pipes(), wn.pumps(), wn.valves()):

        # Extract coordinates
        x0, y0 = wn_graph.nodes[edge.start_node_name]['pos']
        x1, y1 = wn_graph.nodes[edge.end_node_name]['pos']

        # Create Label
        edge_color = '#BBB'
        popup_text = f'##### {wn.get_link(edge_name).link_type} #####<br>ID: {edge_name}<br>'

        # Add flow sensors to label
        if edge_name in flow_sensors:
            edge_color = '#0F0'
            popup_text += 'Flow Sensor<br>'

        # Add sensorfaults to label
        cur_sensorfaults = get_sensorfaults_for(edge_name, 'edge', sensorfaults)
        if len(cur_sensorfaults) > 0:
            edge_color = '#F00'
            popup_text += '### Sensorfaults ### <br>'
            for i, sensorfault in enumerate(cur_sensorfaults):
                fault_param = sensorfault['faultParam'] if 'faultParam' in sensorfault.keys() else '-'
                popup_text += f'''
    Fault {i}: <br>
        Type: {sensorfault["sensorType"]} <br>
        Start Time: {sensorfault["start"]} <br>
        End Time: {sensorfault["end"]} <br>
        Fault Type: {sensorfault["faultType"]} <br> 
        Fault Param: {fault_param} <br>'''

        # Add leaks to label
        cur_leaks = get_leaks_for(edge_name, 'edge', leaks)
        if len(cur_leaks) > 0:
            edge_color = '#00F'
            popup_text += '### Leaks ### <br>'
            for i, leak in enumerate(cur_leaks):
                peak_time = leak['peak'] if 'peak' in leak.keys() else '-'
                popup_text += f''' \
    Leak {i}: <br> \
        Start Time: {leak["start"]} <br>
        End Time: {leak["end"]} <br>
        Diameter: {leak["diameter"]} <br>
        Leak Type: {leak["type"]} <br>
        Peak Time: {peak_time} <br>'''

        # Append render information
        edge_xs += [x0, x1]
        edge_ys += [y0, y1]
        edge_label_xs.append((x0+x1)/2)
        edge_label_ys.append((y0+y1)/2)
        edge_label_labels.append(edge_name)
        edge_label_popups.append(popup_text)
        edge_colors.append(edge_color)

    # Define traces for each edge
    edge_traces = [ plotly.graph_objs.Scatter(
        x=edge_xs[i*2:i*2+2],
        y=edge_ys[i*2:i*2+2],
        mode='lines',
        line={
            'width': 1,
            'color': edge_colors[i]
        }) for i in range(len(edge_colors))]
    
    # Define a trace for the edge labels
    edge_label_trace = plotly.graph_objs.Scatter(
        x=edge_label_xs,
        y=edge_label_ys,
        text=edge_label_labels,
        hovertext=edge_label_popups,
        textposition="middle center",
        hoverinfo='text',
        mode='markers+text',
        marker={
            'color': edge_colors,
            'opacity': 0
        })

    # Initialize node information to plot
    node_xs = []
    node_ys = []
    node_labels = []
    node_popups = []
    node_colors = []

    # Add all nodes to the plot data
    for node in wn_graph.nodes():
        x, y = wn_graph.nodes[node]['pos']
        node_color = '#888'
        popup_text = f'##### {wn.get_node(node).node_type} #####<br>ID: {node}<br>'

        # Add pressure sensors
        if node in pressure_sensors:
            popup_text += 'Pressure Sensor<br>'
            node_color = '#0F0'

        # Add demand sensors
        if node in demand_sensors:
            popup_text += 'Demand Sensor<br>'
            node_color = '#0F0'

        # Add sensorfaults to label
        cur_sensorfaults = get_sensorfaults_for(node, 'node', sensorfaults)
        if len(cur_sensorfaults) > 0:
            node_color = '#F00'
            popup_text += '### Sensorfaults ### <br>'
            for i, sensorfault in enumerate(cur_sensorfaults):
                fault_param = sensorfault['faultParam'] if 'faultParam' in sensorfault.keys() else '-'
                popup_text += f'''
    Fault {i}: <br>
        Type: {sensorfault["sensorType"]} <br>
        Start Time: {sensorfault["start"]} <br>
        End Time: {sensorfault["end"]} <br>
        Fault Type: {sensorfault["faultType"]} <br> 
        Fault Param: {fault_param} <br>'''

        # Add leaks to label
        cur_leaks = get_leaks_for(node, 'node', leaks)
        if len(cur_leaks) > 0:
            node_color = '#F00'
            popup_text += '### Leaks ### <br>'
            for i, leak in enumerate(cur_leaks):
                peak_time = leak['peak'] if 'peak' in leak.keys() else '-'
                popup_text += f''' \
    Leak {i}: <br> \
        Start Time: {leak["start"]} <br>
        End Time: {leak["end"]} <br>
        Diameter: {leak["diameter"]} <br>
        Leak Type: {leak["type"]} <br>
        Peak Time: {peak_time} <br>'''

        # Append render information
        node_xs.append(x)
        node_ys.append(y)
        node_labels.append(node)
        node_popups.append(popup_text)
        node_colors.append(node_color)
    
    # Define a trace for the nodes
    node_trace = plotly.graph_objs.Scatter(
        x=node_xs,
        y=node_ys,
        text=node_labels,
        hovertext=node_popups,
        textposition="top center",
        hoverinfo='text',
        mode='markers+text',
        marker={
            'color': node_colors
        })

    # Create figure
    data = edge_traces + [edge_label_trace, node_trace]
    layout = plotly.graph_objs.Layout(
                    title=plot_name,
                    titlefont=dict(size=16),
                    showlegend=False,
                    width=1600,
                    height=800,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))

    # Plot figure
    fig = plotly.graph_objs.Figure(data=data,layout=layout)
    plotly.offline.plot(fig, filename=out_file, auto_open=auto_open)

def get_leaks_for(name, type, leaks):
    """
    Extract Leaks for a specific part

    :param name: Name of the part
    :param type: Type of the part, either "node" or "edge"
    :param leaks: List of leaks to extract from
    :returns: Leaks that are occurring on the given part
    """
    if type == 'node':
        return list(filter(lambda leak: \
                'nodeId' in leak.keys() \
            and leak['nodeId'] == name \
            , leaks))
    else:
        return list(filter(lambda leak: \
                'pipeId' in leak.keys() \
            and leak['pipeId'] == name \
            , leaks))

def get_sensorfaults_for(name, type, sensorfaults):
    """
    Extract Sensorfaults for a specific part

    :param name: Name of the part
    :param type: Type of the part, either "node" or "edge"
    :param sensorfaults: List of sensorfaults to extract from
    :returns: Sensorfaults that are occurring on the given part
    """
    if type == 'node':
        return list(filter(lambda fault: \
                fault['partId'] == name \
            and fault['sensorType'] in ['pressure', 'demand']\
            , sensorfaults))
    else:
        return list(filter(lambda fault: \
                fault['partId'] == name \
            and fault['sensorType'] in ['flow']\
            , sensorfaults))

def read_config(config_path, scenario_name, leak_config_name, sensor_config_name, sensorfault_config_name):
    """
    Read a config from the path, and extract all information on a specified set of configurations relevant for visualization

    :param config_path: Path to the config to read
    :param scenario_name: Name of the Scenario
    :param leak_config_name: Name of the Leak Config
    :param sensor_config_name: Name of the Sensor Config
    :param sensorfault_config_name: Name of the Sensorfault Config
    :returns: Path to the network file, List of leaks, List of sensorfaults, List of pressure sensors, List of flow sensors, List of demand sensors
    """

    # Read in config and schema
    xml_doc = lxml.etree.parse(config_path)
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
    except Exception as e:
        print('[ERROR] Error parsing config:', e)
        sys.exit(1)

    # Extract info from XML
    # Network name
    network_file = next(iter(xml_doc.xpath(f'Scenario[@name="{scenario_name}"]/@network')), None)
    if network_file is None:
        print(f'[ERROR] The specified Scenario "{scenario_name}" does not exist in the specified config.')
        sys.exit(1)
    if not os.path.isabs(network_file):
        network_file = os.path.join(os.path.dirname(config_path), network_file)

    # Extract Leaks
    leaks_exist = len(xml_doc.xpath(f'Scenario[@name="{scenario_name}"]/LeakConfigs/LeakConfig[@name="{leak_config_name}"]')) > 0
    leaks_xml = xml_doc.xpath(f'Scenario[@name="{scenario_name}"]/LeakConfigs/LeakConfig[@name="{leak_config_name}"]/Leak')
    leaks = xml_to_dict_list(leaks_xml)

    # Check if Leak config exists
    if not leaks_exist:
        print(f'[ERROR] The specified Leak Config "{leak_config_name}" does not exist in the specified config.')
        sys.exit(1)

    
    # Extract Sensorfaults
    sensorfaults_exist = len(xml_doc.xpath(f'Scenario[@name="{scenario_name}"]/SensorfaultConfigs/SensorfaultConfig[@name="{sensorfault_config_name}"]')) > 0
    sensorfaults_xml = xml_doc.xpath(f'Scenario[@name="{scenario_name}"]/SensorfaultConfigs/SensorfaultConfig[@name="{sensorfault_config_name}"]/Sensorfault')
    sensorfaults = xml_to_dict_list(sensorfaults_xml)

    # Check if Sensorfault config exists
    if not sensorfaults_exist:
        print(f'[ERROR] The specified Sensorfault Config "{sensorfault_config_name}" does not exist in the specified config.')
        sys.exit(1)
    
    # Extract Sensors
    sensorfaults_exist = len(xml_doc.xpath(f'Scenario[@name="{scenario_name}"]/SensorConfigs/SensorConfig[@name="{sensor_config_name}"]')) > 0
    pressure_sensors = xml_doc.xpath(f'Scenario[@name="{scenario_name}"]/SensorConfigs/SensorConfig[@name="{sensor_config_name}"]/PressureSensors/Sensor/@id')
    flow_sensors = xml_doc.xpath(f'Scenario[@name="{scenario_name}"]/SensorConfigs/SensorConfig[@name="{sensor_config_name}"]/FlowSensors/Sensor/@id')
    demand_sensors = xml_doc.xpath(f'Scenario[@name="{scenario_name}"]/SensorConfigs/SensorConfig[@name="{sensor_config_name}"]/DemandSensors/Sensor/@id')

    # Check if Sensor config exits
    if not sensorfaults_exist:
        print(f'[ERROR] The specified Sensor Config "{sensor_config_name}" does not exist in the specified config.')
        sys.exit(1)

    # Return parsed data
    return network_file, leaks, sensorfaults, pressure_sensors, flow_sensors, demand_sensors

def xml_to_dict_list(xml_list):
    """
    Helper function to convert a list of xml elements into a list of dicts

    :param xml_list: A list of xml nodes
    :returns: A list of dictionaries containing the nodes' attributes
    """

    lst = []
    for xml in xml_list:
        lst.append({key: xml.attrib[key] for key in xml.attrib.iterkeys()})
    return lst

def run(args):
    """
    Run the scenario visualizer script with the given command line args

    :param args: command line arguments
    """

    # Retrieve command line arguments
    config_or_network = args.config_or_network
    scenario_name = args.scenario_name
    leak_config_name = args.leak_config_name
    sensor_config_name = args.sensor_config_name
    sensorfault_config_name = args.sensorfault_config_name
    output = args.output

    # Check if given config or network file exists
    if not os.path.exists(config_or_network):
        print(f'[ERROR] The specified config or network file does not exist: "{config_or_network}"')
        sys.exit(1)

    # According to given file type, generate data to plot
    file_type = config_or_network.split('.')[-1].lower()
    if file_type == 'inp':

        # For network files, there are no leaks, faults, or sensors
        network_file = config_or_network
        leaks, sensorfaults, pressure_sensors, flow_sensors, demand_sensors = [], [], [], [], []
        plot_name = config_or_network

    elif file_type == 'xml':

        # For config files, first make sure all necessary configs are specified
        if any([name is None for name in [scenario_name, leak_config_name, sensor_config_name, sensorfault_config_name]]):
            print(f'[ERROR] If providing a config file, a configuration of each type must also be specified.')
            sys.exit(1)

        # Next, read all necessary config from the config file
        network_file, leaks, sensorfaults, pressure_sensors, flow_sensors, demand_sensors = \
            read_config(config_or_network, scenario_name, leak_config_name, sensor_config_name, sensorfault_config_name)
        plot_name = f'{scenario_name} - Leaks: "{leak_config_name}"; Sensors: "{sensor_config_name}"; Sensorfaults: "{sensorfault_config_name}"'
    else:
        print(f'[ERROR] Unknown file type "{file_type}", provide either "inp" or "xml".')
        sys.exit(1)

    # Make sure the output file is html, if none is specified create a temporary one.
    if output is None:
        output = tempfile.NamedTemporaryFile(suffix='.html').name
        auto_open = True
    else:
        auto_open = False
        output = output if output.endswith('.html') else f'{output}.html'
    
    # Create a water network model
    wn = wntr.network.WaterNetworkModel(network_file)

    # Graph the network
    plot_network(wn, leaks=leaks, sensorfaults=sensorfaults, \
        pressure_sensors=pressure_sensors, flow_sensors=flow_sensors, demand_sensors=demand_sensors, \
        out_file=output, auto_open=auto_open, plot_name=plot_name)

def configure_parser(parser):
    """
    Set up the parser for the command line arguments.

    :param parser: parser to set up
    """

    parser.add_argument('config_or_network', help='Config or Network file')
    parser.add_argument('scenario_name', nargs='?', help='Name of the Scenario, ignored if Network file is given')
    parser.add_argument('leak_config_name', nargs='?', help='Name of the Leak Config, ignored if Network file is given')
    parser.add_argument('sensor_config_name', nargs='?', help='Name of the Sensor Config, ignored if Network file is given')
    parser.add_argument('sensorfault_config_name', nargs='?', help='Name of the Sensorfault Config, ignored if Network file is given')
    parser.add_argument('-o', '--output', action='store', nargs='?', help='Html file to write visualization, leave empty to display only')

def main():
    """
    Execute the visualize script.
    """

    # Create argument parser
    parser = argparse.ArgumentParser(prog='atmn-visualize', description='Automation Toolbox for Machine learning in water Networks: Visualization Tool', epilog='For further documentation, see https://github.com/HammerLabML/atmn')

    # Configure the parser
    configure_parser(parser)

    # Parse arguments
    args = parser.parse_args()

    # Run visualizer
    run(args)


if __name__ == '__main__':
    main()
