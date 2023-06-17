#!/usr/bin/env python3

from __future__ import annotations

import argparse
import filecmp
from itertools import chain
from pathlib import Path, PurePath
from dataclasses import dataclass, field
import json
import shutil
import tempfile
import re
import os
import sys
import zipfile
from enum import Enum
LOAD_TAG_PATH = Path('data/load/tags/functions/load.json')

@dataclass
class Datapack:
    path: Path
    dependencies: list = field(default_factory=list)

    def __str__(self):
        return Datapack.__recursive_str(self)

    @staticmethod
    def __recursive_str(pack, output='', indent=0):
        indent_str = '  ' * indent
        pack_str = f'Path: {pack.path}'
        if pack.dependencies:
            pack_str += '\nDependencies:'
            for dep in pack.dependencies:
                pack_str = Datapack.__recursive_str(dep, pack_str + '\n', indent + 2)
        indented = '\n'.join(indent_str + line for line in pack_str.split('\n'))
        output += indented
        return output


def get_datapacks_in_dir(datapack_parent_dir: Path) -> list[Path]:
    datapacks = []
    if datapack_parent_dir.is_dir():
        for subdir in (d for d in datapack_parent_dir.iterdir() if d.is_dir()):
            try:
                datapacks.append(valid_datapack_path(str(subdir)))
            except:
                continue
    return datapacks

def discover_from_dirs(discover_dirs: list[Path], tempdir) -> set[Path]:
    discovered_datapacks = set()
    for d in discover_dirs:
        for p in d.iterdir():
            if p.is_dir():
                try:
                    valid_datapack_path(p)
                    discovered_datapacks.add(p)
                except:
                    pass
            elif p.suffix == '.zip':
                unzipped_path = unzip_potential_datapack(p, tempdir)
                valid_datapack_path(unzipped_path)
                discovered_datapacks.add(unzipped_path)
    return discovered_datapacks

def get_lantern_load_tag_functions(datapack_path: str) -> list[str | dict]:
    with open(datapack_path / LOAD_TAG_PATH, 'r') as load_file:
        return json.load(load_file)['values']

def detect_datapack_path_from_funct(load_funct: str, datapack_paths: list[Path]) -> Path:
    is_tag = load_funct.startswith('#')
    function_or_tag_dir = 'tags/functions' if is_tag else 'functions'
    file_ext = '.json' if is_tag else '.mcfunction'
    
    if is_tag:
        load_funct = load_funct
    namespace = load_funct[1 if is_tag else 0:load_funct.find(':')]
    load_file = load_funct[load_funct.find(':') + 1:] + file_ext
    for datapack_path in datapack_paths:
        if load_funct == get_lantern_load_tag_functions(datapack_path)[-1]:
            load_file_path = datapack_path / 'data' / namespace / function_or_tag_dir / load_file
            if load_file_path.is_file():
                return datapack_path
    return None

def resolve_datapack(main_datapack_path: Path, required_dep_paths: list[Path], discovered_paths: set[Path] = None) -> Datapack:
    datapack = Datapack(main_datapack_path)
    datapack.dependencies = [Datapack(p) for p in required_dep_paths]
    # if there are discovered paths then --discover is enabled. Find the rest in those
    if discovered_paths:
        try:
            # Must be a lantern load datapack to discover deps
            valid_lantern_load_datapack_path(main_datapack_path)
            # TODO handle json type entry to values
            load_functions = get_lantern_load_tag_functions(main_datapack_path)
            if load_functions:
                # Pop last since its own load function
                # TODO only pop if last funct is in this datapack
                load_functions.pop()
                dep_datapacks = []
                for load_func in load_functions:
                    # first check if satisfied by required deps
                    dep_pack_path = detect_datapack_path_from_funct(load_func, required_dep_paths)
                    if not dep_pack_path:
                        dep_pack_path = detect_datapack_path_from_funct(load_func, discovered_paths)
                        if dep_pack_path:
                            dep_datapacks.append(resolve_datapack(dep_pack_path, [], discovered_paths=[*discovered_paths, *required_dep_paths])) 
                        else:
                            print(f'Warning: Failed to find datapack matching load function {load_func}')
                datapack.dependencies.extend(dep_datapacks)
        except argparse.ArgumentTypeError as e:
            raise e
    return datapack

class DepType(Enum):
    DATAPACK = 1
    ZIP = 2

def valid_dep_path(path_str: str) -> tuple[DepType,Path]:
    try:
        if path_str.endswith('.zip'):
            return DepType.ZIP,Path(path_str)
        else:
            p = valid_datapack_path(path_str)
            return DepType.DATAPACK,p
    except Exception as e:
        raise e
def dp_or_zips_at_path(path_str: str) -> list[Path]:
    datapacks = []
    msg = ""
    try:
        # allow zip archive
        if path_str.endswith('.zip'):
            datapacks.append(Path(path_str))
        else:
            datapacks.append(valid_datapack_path(path_str))
    except Exception as e:
        msg = str(e)
        temp_path = Path(path_str)
        datapacks = get_datapacks_in_dir(temp_path)
    
    if not datapacks:
        raise argparse.ArgumentTypeError(f'Path is not a datapack or directory containing datapacks. {msg}')
    
    return datapacks


def valid_datapack_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f'Path to datapack does not exist: {path}')
    
    mc_meta_file = path / 'pack.mcmeta'
    if not mc_meta_file.is_file():
        raise argparse.ArgumentTypeError(f'Datapack does not have a pack.mcmeta file: {mc_meta_file}')
    
    return path

def valid_lantern_load_datapack_path(path_str: str | Path) -> Path:
    path = valid_datapack_path(path_str)
    lantern_load_tag = path / LOAD_TAG_PATH
    if not lantern_load_tag.is_file():
        raise argparse.ArgumentTypeError(f'Datapack does not have Lantern Load tag: {lantern_load_tag}')
    return path

def valid_dir(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f'Invalid directory: {path}')
    return path


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

def copy_datapack_files(datapack: Datapack, dest_data_dir: Path, file_ignore_patterns: list):
    src_data_dir = datapack.path / 'data'
    shutil.copytree(src_data_dir, dest_data_dir, ignore=ignore_patterns(file_ignore_patterns), dirs_exist_ok=True)
    for dep in datapack.dependencies:
        copy_datapack_files(dep, dest_data_dir, file_ignore_patterns)

def bundle_in_dest(datapack: Datapack, destination: Path, zip_up, release, no_dep_tests):
    main_pack_ignores = []
    ignore_tests = r'.+/functions/test(/.*)?'
    ignore_lantern_load = r'.+/data/load(/.*)?'
    ignore_minecraft_tags = r'.+/data/minecraft/tags(/.*)?'
    dependency_ignores = []
    if release:
        main_pack_ignores = [ignore_tests]
        dependency_ignores += [ignore_tests]
    
    if no_dep_tests:
        dependency_ignores += [ignore_tests]

    with tempfile.TemporaryDirectory() as tmpdir:
        src_datapack_path = datapack.path.resolve()
        datapack_name = src_datapack_path.name
        destination = destination.resolve()
        dest_datapack_path = destination / datapack_name
        tmp_datapack_path = Path(tmpdir) / datapack_name
        
        # Create base datapack dir
        (tmp_datapack_path / 'data').mkdir(parents=True, exist_ok=True)
        # copy dependencies
        for dep in datapack.dependencies:
            copy_datapack_files(dep, tmp_datapack_path / 'data', dependency_ignores)        
        
        # copy base datapack after deps to prioritize main datapack files
        shutil.copytree(src_datapack_path, tmp_datapack_path,ignore=ignore_patterns(main_pack_ignores), dirs_exist_ok=True)
        print(f'Building datapack at {dest_datapack_path}')
        if zip_up or release:
            zip_path = shutil.make_archive(datapack_name, 'zip', tmp_datapack_path)
            tmp_datapack_path = zip_path
            dest_datapack_path = destination / Path(zip_path).name
        
        if dest_datapack_path.exists():
            print(f'Removing existing pack..')
            if dest_datapack_path.is_dir():
                shutil.rmtree(dest_datapack_path)
            elif dest_datapack_path.is_file():
                os.remove(dest_datapack_path)
        shutil.move(tmp_datapack_path, dest_datapack_path)

        print('Done')

def move_changed_files(source_path: Path, dest_path: Path):
    
    # if the dest does not exist or is a different type than the source, copy over
    if not dest_path.exists() or (source_path.is_file() and dest_path.is_dir()) or (source_path.is_dir() and dest_path.is_file()):
        print(f'copy {source_path.name} to {dest_path}')
        if dest_path.is_dir():
            shutil.rmtree(dest_path)
        elif dest_path.is_file():
            os.remove(dest_path)
        shutil.move(source_path, dest_path)

    elif source_path.is_dir():
        for f in source_path.iterdir():
            dest_file = dest_path / f.name
            move_changed_files(f, dest_file)
        # TODO handle dir
    elif source_path.is_file():
        is_match = filecmp.cmp(source_path, dest_path, shallow=False)
        print(f'{source_path}, {dest_path}: {"NO CHANGES" if is_match else "CHANGED"}')
        if not is_match:
            shutil.copy2(source_path, dest_path)
    elif not source_path.exists():
        raise ValueError(f'Source path {source_path} does not exist!')

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='A tool to bundle packs with different namespaces.')
    parser.add_argument('datapack', type=valid_datapack_path, default='.', help='Datapack to bundle')
    parser.add_argument('dependencies', nargs='*', type=valid_dep_path, help='Dependency datapacks or .zips to bundle into the main one')
    parser.add_argument('--zip', action='store_true', help='Compress the bundled datapack into a .zip file')
    parser.add_argument('--dest', type=Path, default='bundles', help='Destination directory to copy bundled datapacks')
    parser.add_argument('--release', action='store_true', help='Removes function/test paths and zips output')
    parser.add_argument('--discover', nargs='*', help='Directories to discover Lantern Load datapack dependencies')
    parser.add_argument('--no-dep-tests', action='store_true', help='Only applicable when not in release mode. Removes test functions from bundled dependency packs.')
    return parser.parse_args()


def unzip_potential_datapack(zip_path: Path, tempdir: Path) -> Path:
    unzipped_p = tempdir / zip_path.stem
    unzipped_p.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(unzipped_p)
    return unzipped_p
    

def convert_zips(dep_or_zip_paths: list[Path], tempdir) -> list[Path]:
    dep_paths = []
    for p in dep_or_zip_paths:
        if p.is_file() and p.suffix == '.zip':
            p = unzip_potential_datapack(p, tempdir)
        try:
            dep_paths.append(valid_datapack_path(p))
        except argparse.ArgumentTypeError as e:
            continue
    return dep_paths

def run(main_datapack_path: Path, dep_or_zip_paths: list[Path], destination_path:Path, zip_up: bool=False, release: bool=False, no_dep_tests: bool=False, discover_dirs: list[Path] = None):
    with tempfile.TemporaryDirectory() as tempdir_name:
        tempdir = Path(tempdir_name)
        dep_paths = convert_zips(dep_or_zip_paths, tempdir)
        potential_deps = discover_from_dirs(discover_dirs, tempdir) if discover_dirs else None
        
        datapack = resolve_datapack(main_datapack_path, dep_paths, discovered_paths = potential_deps)
        destination_path.mkdir(parents=True, exist_ok=True)
        bundle_in_dest(datapack,destination_path, zip_up, release, no_dep_tests)

def main():
    try:
        args = get_args()
        datapacks_or_zip_paths = [path for dep_type,path in args.dependencies]
        discover_dirs = args.discover
        run(args.datapack, datapacks_or_zip_paths, args.dest, zip_up=args.zip, release=args.release, no_dep_tests=args.no_dep_tests, discover_dirs=discover_dirs)
        return 0
    except argparse.ArgumentTypeError as e:
        print(f'Argument error: {e}')
    return 1

if __name__ == "__main__":
    main()