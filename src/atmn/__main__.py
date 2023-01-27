#!/usr/bin/env python3

import argparse
from atmn.ScenarioGenerator import run as generate, configure_parser as configure_generate_parser
from atmn.ScenarioExporter import run as export, configure_parser as configure_export_parser
from atmn.ScenarioVisualizer import run as visualize, configure_parser as configure_visualize_parser

def main():
    # Create the command line parser
    parser = argparse.ArgumentParser(prog='atmn', description='Automation Toolbox for Machine learning in water Networks', epilog='For further documentation, see https://github.com/HammerLabML/atmn')

    # Add subparsers for each subcommand
    subparsers = parser.add_subparsers(dest='command', required=True)
    parser_generate = subparsers.add_parser("generate", help="Generate a dataset")
    parser_export = subparsers.add_parser("export", help="Export a dataset")
    parser_visualize = subparsers.add_parser("visualize", help="Visualize a network or configured Scenario")

    # Configure parsers
    configure_generate_parser(parser_generate)
    configure_export_parser(parser_export)
    configure_visualize_parser(parser_visualize)

    # Parse arguments
    args = parser.parse_args()

    # Execute corresponding command
    if args.command == 'generate':
        generate(args)
    elif args.command == 'export':
        export(args)
    elif args.command == 'visualize':
        visualize(args)

if __name__ == "__main__":
    main()