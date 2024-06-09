# Steel_design_results_analysis

Steel_design_results_analysis is a Python script meant to create a database of results and perform a simple statistical analysis on the dataset. This script helps to interpret how many members in a structure are not safe and if the remaining elements are optimal for the design. As a result of this script an SQLite3 database is created.

## How to use?

It is required to run the included steel_design_results_analysis.py file.

```bash
python .\steel_design_results_analysis.py
```

Then it is recommended to use the attached directory filled with example files as datasets for analysis. They are located at:

```bash
.\steel_example_files\Stahlhalle\
```

## FAQ

- What does this do?

This program selects the directory with csv files exported from RFEM 6 program and then selects files containing info about results from Steel Design analysis and about Sections used in the model. Based on the data parsed from the csv files, custom tables inside SQLite3 database are created.

- Operations on Steel Design results table

During creation of Steel_Design table, this is a starting state of data:

During the execution of the program, this is the end state of data inside a created database:



In this process mainly renaming of column headers takes place and skipping of empty rows. After that the column representing numerical values of every Design Check performed is cleaned up from the intermittent Error or Warning messages from the program. This information is later included in a new defined column.

- Operation on Sections table

During creation of Sections table, this is a starting state of data:

During the execution of the program, this is the end state of data inside a created database:


In this process parsing the data also includes a process of renaming of column headers. Apart from that a type of notation is changed, from the comma/dash notation of a list Member Numbers assigned to a given section, is changed to a morelike database structure where every row of data


- Where did you obtain the data for example files?

The data was obtained as an export from an RFEM 6 program, based on a free model.

https://www.dlubal.com/en/downloads-and-information/examples-and-tutorials/models-to-download/004578


- I see that inside this file there are many #comments or #TODO notes, why?

This file is a result of a private work on a spare time, partly as a hobby, the TODO notes are my own notes for things that in my opinion should be implemeted/fixed at a later date.
In case of suggestions or comments, I invite you to please get in contact on github.
