# dpbuild
A datapack bundling tool for combining multiple namespaces into a single datapack for easy distribution

## Usage
Clone or download this repository and execute the script by running either `./dpbuild <args>` or `python dpbuild <args>`. All datapacks must implement Lantern Load in order to bundle. See help text below for argument details.
```
usage: dpbuild [-h] [--zip] [--dest DEST] [--release] [--discover [DISCOVER ...]]
                   [--no-dep-tests]
                   datapack [dependencies ...]

A tool to bundle packs with different namespaces.

positional arguments:
  datapack              Datapack to bundle
  dependencies          Dependency datapacks or .zips to bundle into the main one

options:
  -h, --help            show this help message and exit
  --zip                 Compress the bundled datapack into a .zip file
  --dest DEST           Destination directory to copy bundled datapacks
  --release             Removes function/test paths and zips output
  --discover [DISCOVER ...]
                        Directories to discover Lantern Load datapack dependencies
  --no-dep-tests        Only applicable when not in release mode. Removes test functions from
                        bundled dependency packs.
```

## Example
Suppose you have a datapacks directory containing `your_dp` which is a datapack that relies on `dep1` and `dep2`.

```
datapacks
├── dep1
│   ├── data
│   │   └── dep1_ns
│   └── pack.mcmeta
├── dep2
│   ├── data
│   │   └── dep2_ns
│   └── pack.mcmeta
└── your_dp
    ├── data
    │   └── your_dp_ns
    │       └── functions
    └── pack.mcmeta
```
With `dpbuild` you can create a single directory or zip file with everything your datapack needs. The following command will bundle everything together and output in the test world datapacks folder.
```
./dpbuild your_dp --dest ~/.minecraft/saves/test-world/datapacks
```
The resulting bundled datapack at `~/.minecraft/saves/test-world/datapacks` will be structured as follows,
```
test-world/datapacks
└── your_dp
    ├── data
    │   └── dep1_ns
    │   └── dep2_ns
    │   └── your_dp_ns
    │       └── functions
    └── pack.mcmeta
```