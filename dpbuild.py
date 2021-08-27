#!/usr/bin/env python3

import argparse
import glob
from pathlib import Path, PurePath
from dataclasses import dataclass, field
import json
import shutil
import tempfile
import re
import os

LOAD_TAG_PATH = Path('data/load/tags/functions/load.json')

@dataclass
class Datapack:
    path: Path
    dependencies: list = field(default_factory=list)

    def __str__(self):
        return Datapack.__recusive_str(self)

    @staticmethod
    def __recusive_str(pack, output='', indent=0):
        indent_str = '  ' * indent
        pack_str = f'Path: {pack.path}'
        if pack.dependencies:
            pack_str += '\nDependencies:'
            for dep in pack.dependencies:
                pack_str = Datapack.__recusive_str(dep, pack_str + '\n', indent + 2)
        indented = '\n'.join(indent_str + line for line in pack_str.split('\n'))
        output += indented
        return output
    
def get_sibling_datapack_paths(datapack_paths: list[Path]):
    parents = set()
    for path in datapack_paths:
        parent = path.parent
        if parent not in parents:
            for sibling in [p for p in parent.iterdir() if p.is_dir()]:
                try:
                    yield valid_datapack_path(sibling)
                except:
                    pass # TODO do better

def get_lantern_load_tag_functions(datapack_path: str):
    with open(datapack_path / LOAD_TAG_PATH, 'r') as load_file:
        return json.load(load_file)['values']

def detect_datapack_path_from_funct(load_funct: str, datapack_paths: list[Path]) -> Path:
    namespace = load_funct[:load_funct.find(':')]
    mcfunction = load_funct[load_funct.find(':') + 1:] + '.mcfunction'
    for datapack_path in datapack_paths:
        if load_funct == get_lantern_load_tag_functions(datapack_path)[-1]:
            mcfunction_path = datapack_path / 'data' / namespace / 'functions' / mcfunction
            if mcfunction_path.is_file():
                return datapack_path
    print(f'Warning: Failed to find datapack matching load function {load_funct}')
    return None

def resolve_datapack(datapack_path: Path, all_datapack_paths: list[Path]) -> Datapack:
    datapack = Datapack(path=datapack_path)
    load_functions = get_lantern_load_tag_functions(datapack_path)
    if load_functions:
        # Pop last since its own load function
        load_functions.pop()
        dep_datapacks = []
        for load_func in load_functions:
            dep_pack_path = detect_datapack_path_from_funct(load_func, all_datapack_paths)
            if dep_pack_path:
                dep_datapacks.append(resolve_datapack(dep_pack_path, all_datapacks)) 
        datapack.dependencies = dep_datapacks
    return datapack

def valid_datapack_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f'Path to datapack does not exist: {path}')
    
    mc_meta_file = path / 'pack.mcmeta'
    if not mc_meta_file.is_file():
        raise argparse.ArgumentTypeError(f'Datapack does not have a pack.mcmeta file: {mc_meta_file}')
    
    lantern_load_tag = path / LOAD_TAG_PATH
    if not lantern_load_tag.is_file():
        raise argparse.ArgumentTypeError(f'Datapack does not have Lantern Load tag: {lantern_load_tag}')
    return path

def valid_dir(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f'Invalid directory: {path}')
    return path

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='A tool to bundle packs with different namespaces')
    parser.add_argument('datapacks', nargs='+', type=valid_datapack_path, help='Datapacks to bundle. All datapacks will be bundled into the first listed')
    parser.add_argument('--zip', action='store_true', help='Compress the bundled datapack into a .zip file')
    parser.add_argument('--dest', type=Path, default='bundles', help='Destination directory to copy bundled datapacks')
    parser.add_argument('--release', action='store_true', help='Removes function/test paths and zips output')
    return parser.parse_args()



def ignore_patterns(patterns: list[str]):
    def get_ignored(dir, filenames):
        dir_path = Path(dir)
        results = []
        for patt in patterns:
            for f in filenames:
                path = str(dir_path / f)
                if re.match(patt, path):
                    results.append(f)
        return results
    return get_ignored

def bundle_in_dest(datapack: Datapack, destination: Path, zip=False, release=False):
    main_ignores = []
    dep_ignores = [r'.+/data/load(/.*)?',r'.+/data/minecraft/tags(/.*)?' ]
    if release:
        main_ignores = [r'.+/functions/test(/.*)?']
        dep_ignores += main_ignores
    
    with tempfile.TemporaryDirectory() as tmpdir:
        src_datapack_path = datapack.path
        datapack_name = src_datapack_path.name
        dest_datapack_path = destination / datapack_name
        tmp_datapack_path = Path(tmpdir) / datapack_name
        
        # copy base datapack
        shutil.copytree(src_datapack_path, tmp_datapack_path,ignore=ignore_patterns(main_ignores), dirs_exist_ok=True)
        # copy dependencies
        for dep in datapack.dependencies:
            src_data_dir = dep.path / 'data'
            dest_data_dir = tmp_datapack_path / 'data'
            shutil.copytree(src_data_dir, dest_data_dir, ignore=ignore_patterns(dep_ignores), dirs_exist_ok=True)
        
        if zip or release:
            zip_path = shutil.make_archive(datapack_name, 'zip', tmp_datapack_path)
            tmp_datapack_path = zip_path
            dest_datapack_path = destination / Path(zip_path).name
        
        if dest_datapack_path.exists():
            print(f'Removing existing pack at {dest_datapack_path}')
            if dest_datapack_path.is_dir():
                shutil.rmtree(dest_datapack_path)
            elif dest_datapack_path.is_file():
                os.remove(dest_datapack_path)
        shutil.move(tmp_datapack_path, dest_datapack_path)



if __name__ == "__main__":
    args = get_args()

    all_datapacks = list(get_sibling_datapack_paths(args.datapacks))
    datapack = resolve_datapack(args.datapacks[0], all_datapacks)

    args.dest.mkdir(parents=True, exist_ok=True)
    bundle_in_dest(datapack,args.dest, zip=args.zip, release=args.release)

    