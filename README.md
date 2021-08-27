# dpbuild
A datapack bundling tool for combining multiple namespaces into a single datapack for easy distribution

## Usage
Clone or download this repository and execute the script by running either `./dpbuild <args>` or `python dpbuild <args>`. All datapacks must implement Lantern Load in order to bundle. See help text below for argument details.
```
usage: dpbuild [-h] [--zip] [--dest DEST] [--release] [--strict] datapacks [datapacks ...]

A tool to bundle packs with different namespaces. Requires each datapack to implement Lantern Load.

positional arguments:
  datapacks    Datapack(s) to bundle. Only need to provide the top level datapack unless --strict is used.

optional arguments:
  -h, --help   show this help message and exit
  --zip        Compress the bundled datapack into a .zip file
  --dest DEST  Destination directory to copy bundled datapacks
  --release    Removes function/test paths and zips output
  --strict     Only attempts to bundle using passed datapacks and not check parent folder for dependencies
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