# dpbuild
A datapack bundling tool for combining multiple namespaces into a single datapack for easy distribution

## Example
Creating a complex datapack often involves calling functions in library datapacks. This forces the user to install dependency datapacks or requires the developer to bundle dependencies.

The following block shows an example of a datapacks directory containing `your_dp` which is a datapack that relies on `dep1` and `dep2`.

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

After running `dpbuild <world/datapacks> your_dp dep1 dep2` the resulting bundled datapack will be structured as follows,
```
output_dir
└── your_dp
    ├── data
    │   └── dep1_ns
    │   └── dep2_ns
    │   └── your_dp_ns
    │       └── functions
    └── pack.mcmeta
```
