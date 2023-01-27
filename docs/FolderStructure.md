# Folder Structure
The generation tool generates a specific folder structure, which is expected by the loading API as well as the export tool. This documentation outlines this structure.

The base folder is called a *Collection* of Scenarios. It contains one folder per Scenario, named after the Scenario name.

Each *Scenario* folder in turn contains four folders and a file:
* `measurements`: This folder contains the actual simulation results. For each leak config, there is one folder named after that leak config. Within each folder there are the measurements in the separate files `demand.csv`, `flow.csv` and `pressure.csv`.
* `sensors`: This folder contains one xml file for each sensor config, named after the config name.
* `sensorfaults`: This folder contains one xml file for each sensorfault config, named after the config name.
* `leaks`: This folder contains one xml file for each leak config, named after the config name.
* `topology.xml`: The topology of the water network in `xml` format.