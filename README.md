# Automation Toolbox for Machine learning in water Networks
The Automation Toolbox for Machine learning in water Networks (`atmn`) offers a selection of easy to use tools for generating and working with synthetic water network data. It builds on the `wntr` python package to use the EPANET simulator for simulation of leaks and sensor faults in water networks.

If you want a hands-on tour of all features this toolbox has to offer, have a look in the `examples/Quickstart.ipynb` notebook. To get started you only need to install and run jupyter notebook:

- `$ pip install notebook`
- `$ jupyter notebook`
- Open the `Quickstart` notebook and it will explain everything you need to know.

## Documentation
There is separate documentation on different topics concerning the toolbox:

* If you want to learn more about your options for configuring a Scenario Collection, have a look at the [Scenario Configuration](docs/ScenarioConfig.md) page.
* If you seek documentation for loading Scenarios, refer to the [Scenario Loader Reference](docs/ScenarioLoader.md)
* If you are interested, how `atmn` organizes the generated data, have a look at the [Folder Structure](docs/FolderStructure.md) documentation.
* `atmn` currently offers three tools:
    * `atmn-generate` to generate a dataset from a Scenario Configuration.
    * `atmn-visualize` to visualize either a water network file `*.inp` or a specific Configuration from a Collection.
    * `atmn-export` to export a specific Configuration from a Collection to Excel.

    Use the `-h` flag to get more information on how to use these tools. For example usages, you can have a look in the `Quickstart` notebook. If your package manager did not create the `atmn` wrappers, you can also use `python -m atmn` to use the tools.


## Version History

### 1.1
- Added support for saving measurements with binary datatypes

### 1.0
- Initial public release