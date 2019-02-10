#!/bin/env python
# -*- coding: utf-8 -*-

import argparse
import getpass
import json
import os
import re
import urllib.request
import shutil
import subprocess
import sys

PATH_WORK = 'opt'
PATH_DEPOT_TOOLS = 'opt/depot_tools'
GITHUB_PATH = 'https://api.github.com/repos/llamerada-jp/libwebrtc'
GITHUB_USER = 'llamerada-jp'

# Change directory by ROOT_PATH.
def util_cd(*path):
    abs_path = util_getpath(*path)
    if not os.path.exists(abs_path):
        os.mkdir(abs_path)
    os.chdir(abs_path)
    print('cd : ' + abs_path)

def util_cp(src, dst):
    shutil.copy(src, dst)
    print('cp : ' + src + ' ' + dst)

def util_emptydir(*path):
    abs_path = util_getpath(*path)
    if os.path.exists(abs_path):
        shutil.rmtree(abs_path)
    os.mkdir(abs_path)
    print('mkdir : ' + abs_path)

def util_exec(*cmds):
    print('exec : ' + ' '.join(cmds))
    subprocess.check_call(cmds)

def util_exec_stdin(data, *cmds):
    print('exec : ' + ' '.join(cmds))
    print(data)
    proc = subprocess.Popen(cmds, stdin=subprocess.PIPE)
    proc.communicate(data.encode('utf-8'))

def util_exists(*path):
    abs_path = util_getpath(*path)
    return os.path.exists(abs_path)

def util_getpath(*path):
    global PATH_ROOT
    return os.path.join(PATH_ROOT, *path)

def util_mv(src, dst):
    shutil.move(src, dst)
    print('mv : ' + src + ' ' + dst)

def util_rm(*path):
    abs_path = util_getpath(*path)
    if os.path.exists(abs_path):
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)

# Parser for arguments.
def parse_args():
    parser = argparse.ArgumentParser(description='This script is ...')
    parser.add_argument('-A', '--disable_archive', action='store_true',
                        help="Disable archive sequence.")
    parser.add_argument('-B', '--disable_build', action='store_true',
                        help="Disable build sequence.")
    parser.add_argument('-c', '--configure', action='store',
                        default='config.json', type=str,
                        help="Set configuration json file name. 'default: config.json'")
    parser.add_argument('-t', '--target_env', action='store',
                        type=str, required=True,
                        choices=['osx', 'ubuntu'],
                        help="Set target envrionment.")
    parser.add_argument('-a', '--arch', action='store', type=str,
                        choices=['x86', 'x64'],
                        help="Set arget archtecture")
    parser.add_argument('--chrome_ver', action='store',
                        type=int, help="Set build target Chrome version.")
    parser.add_argument('-d', '--debug', action='store_true',
                        help="Set build type to debug mode.")
    parser.add_argument('-u', '--upload', action='store_true',
                        help="Upload archive to github release.")

    return parser.parse_args()

#
def get_last_chrome_ver(os):
    csv = urllib.request.urlopen('https://omahaproxy.appspot.com/all').read()
    for line in csv.decode('utf-8').split('\n'):
        m = re.search(os + ',stable,([0-9]+)\.', line)
        if m:
            return int(m.group(1))

#
def get_work_path(conf, *path):
    target_path = conf['target_env']
    if 'arch' in conf:
        target_path = target_path + '_' + conf['arch']
    return util_getpath(PATH_WORK, target_path, *path)

#
def get_archive_name(conf):
    name = conf['archive_name']
    for key, val in conf.items():
        name = name.replace('{' + key + '}', str(val))
    return name

# Parser for configuration file.
def parse_conf(args):
    # Load configuration file as JSON.
    fd_js = open(args.configure, 'r')
    js_all = json.load(fd_js)
    fd_js.close()

    # Get configuration for target environment.
    target_env = args.target_env
    js_env = js_all[target_env]

    # Check chrome version
    if args.chrome_ver is None:
        chrome_ver = get_last_chrome_ver(js_all['chrome_os_map'][target_env])
    else:
        chrome_ver = int(args.chrome_ver)

    # Merge envrionment values.
    conf = {}
    for it_env in js_env:
        # Conditions of skip filter
        if it_env['chrome_version'] > chrome_ver:
            continue
        # Mearge
        conf.update(it_env)

    # Check architecture
    if 'arch' in conf and isinstance(conf['arch'], list):
        if args.arch is None:
            conf['arch'] = conf['arch'][0]
        elif args.arch in conf['arch']:
            conf['arch'] = args.arch
        else:
            print('invalid arch : ' + args.arch)
            sys.exit()

    conf['target_env'] = target_env
    conf['chrome_version'] = chrome_ver
    conf['enable_archive'] = not args.disable_archive
    conf['enable_build'] = not args.disable_build
    conf['enable_debug'] = args.debug
    conf['enable_upload'] = args.upload
    return conf

#
def setup(conf):
    # Update or get depot tools.
    if os.path.exists(util_getpath(PATH_DEPOT_TOOLS)):
        util_cd(PATH_DEPOT_TOOLS)
        util_exec('git', 'pull')
    else:
        util_exec('git', 'clone',
                  'https://chromium.googlesource.com/chromium/tools/depot_tools.git',
                  util_getpath(PATH_DEPOT_TOOLS))

    # Add path of depot tools for environment value PATH.
    os.environ['PATH'] = util_getpath(PATH_DEPOT_TOOLS) + ':' + os.environ['PATH']

#
def build(conf):
    work_path = get_work_path(conf)
    util_cd(work_path)
    if not util_exists(work_path, '.gclient'):
        util_exec('fetch', '--nohooks', 'webrtc')
    util_exec('gclient', 'sync', '--nohooks', '--with_branch_heads', '-v', '-R')
    # TODO install-build-deps.sh
    util_exec('git', 'submodule', 'foreach',
              "'git config -f $toplevel/.git/config submodule.$name.ignore all'")
    util_exec('git', 'config', '--add', 'remote.origin.fetch', "'+refs/tags/*:refs/tags/*'")
    util_exec('git', 'config', 'diff.ignoreSubmodules', 'all')

    util_cd(work_path, 'src')
    util_exec('git', 'fetch', 'origin')
    util_exec('git', 'checkout', '-B', str(conf['chrome_version']),
              'refs/remotes/branch-heads/' + str(conf['chrome_version']))
    util_exec('gclient', 'sync', '--with_branch_heads', '-v', '-R')
    util_exec('gclient', 'runhooks', '-v')

    args = []
    if 'enable_debug' in conf and conf['enable_debug']:
        args.append('is_debug=true')
    else:
        args.append('is_debug=false')

    if 'arch' in conf:
        args.append("target_cpu=\"" + conf['arch'] + "\"")

    util_exec('gn', 'gen', 'out/Default', '--args=' + ' '.join(args))
    for build_target in conf['build_targets']:
        util_exec('ninja', '-C', 'out/Default', build_target)

def archive(conf):
    work_path = get_work_path(conf)
    # Make directory
    util_emptydir(work_path, 'lib')
    util_emptydir(work_path, 'include')
    util_cd(work_path, 'src/out/Default')

    # Build lib file for each environment.
    if conf['target_env'] == 'osx':
        archive_osx()
    else:
        archive_linux()
    
    # Rename if needed.
    for src, dst in conf['rename_objs'].items():
        util_mv(util_getpath(work_path, 'lib', src), util_getpath(work_path, 'lib', dst))

    # Listup lib filenames.
    util_cd(work_path, 'lib')
    fd = open(util_getpath(work_path, 'exports_libwebrtc.txt'), 'w')
    fd.write("\n".join([f.name for f in os.scandir() if f.name.startswith('lib')]))
    fd.close()

    # Copy header files.
    util_cd(work_path, conf['header_root_path'])
    if conf["target_env"] == "osx":
        util_exec('find', '.', '-name', '*.h', '-exec', 'rsync', '-R', '{}', util_getpath(work_path, 'include'), ';')
    else:
        util_exec('find', '.', '-name', '*.h', '-exec', 'cp', '--parents', '{}', util_getpath(work_path, 'include'), ';')
    for ex in conf['exclude_headers']:
        util_rm(work_path, 'include', ex)

    # Archive
    util_cd(work_path)
    archive_name = get_archive_name(conf)
    if re.search(r'\.zip$', archive_name):
        util_exec('zip', '-r', archive_name, 'lib', 'include', 'exports_libwebrtc.txt')
    elif re.search(r'\.tar\.gz$', archive_name):
        util_exec('tar', 'czvf', archive_name, 'lib', 'include', 'exports_libwebrtc.txt')

def archive_osx(conf):
    work_path = get_work_path(conf)

    target_objs = conf['extra_objs']
    for line in  open(conf['ninja_file'], 'r'):
        if line.find(conf['ninja_target']) >= 0:
            target_objs.extend(line.split(' '))
            break

    objs = []
    for obj in target_objs:
        is_exclude = False
        for ex in conf['exclude_objs']:
            # Exclude files.
            if obj.find(ex) >= 0:
                is_exclude = True
                break
        if is_exclude:
            continue
        elif re.search(r'\.o$', obj):
            # Collect *.o files.
            objs.append(obj)
        elif re.search(r'\.a$', obj):
            # Copy *.a files.
            if util_exists(util_getpath(work_path, 'lib', os.path.basename(obj))):
                i = 1
                while util_exists(util_getpath(work_path, 'lib', os.path.splitext(os.path.basename(obj))[0] + '_' + str(i) + '.a')):
                    i += 1
                util_cp(util_getpath(work_path, 'src/out/Default', obj), util_getpath(work_path, 'lib', os.path.splitext(os.path.basename(obj))[0] + '_' + str(i) + '.a'))
            else:
                util_cp(util_getpath(work_path, 'src/out/Default', obj), util_getpath(work_path, 'lib'))
    # Generate libwebrtc.a from *.o files.
    util_exec('ar', 'cr', util_getpath(work_path, 'lib/libmywebrtc.a'), *objs)

def archive_linux():
    work_path = get_work_path(conf)

    target_objs = conf['extra_objs']
    for line in  open(conf['ninja_file'], 'r'):
        if line.find(conf['ninja_target']) >= 0:
            target_objs.extend(line.split(' '))
            break
    objs = []
    script = 'create ' + util_getpath(work_path, 'lib/libwebrtc.a\n')
    for obj in target_objs:
        is_exclude = False
        for ex in conf['exclude_objs']:
            # Exclude files.
            if obj.find(ex) >= 0:
                is_exclude = True
                break
        if is_exclude:
            continue
        elif re.search(r'\.o$', obj):
            # Collect *.o files.
            objs.append(obj)
        elif re.search(r'\.a$', obj):
            # Build script
            script = script + "addlib " + obj + "\n"

    # Generate libwebrtc.a from *.o files.
    tmplib_name = util_getpath(work_path, 'lib/libmywebrtc.a')
    util_exec('ar', 'cr', tmplib_name, *objs)
    script = script + "addlib " + tmplib_name + "\nsave\nend"
    util_exec_stdin(script, "ar", "-M")
    util_rm(tmplib_name)
    
def upload(conf):
    GITHUB_PSWD = getpass.getpass('Password for github: ')

    releases = urllib.request.urlopen(GITHUB_PATH + '/releases').read()
    releases = json.loads(releases.decode('utf-8'))
    upload_url = False
    for entry in releases:
        if 'body' in entry and str(entry['body']) == str(conf['chrome_version']):
            upload_url = entry['upload_url']
            break

    if not upload_url:
        data = {
            'tag_name' : 'v' + str(conf['chrome_version']),
            'target_commitish' : 'master',
            'name' : 'v' + str(conf['chrome_version']),
            'body' : str(conf['chrome_version']),
            'draft' : False,
            'prerelease' : False
        }
        headers = {
            'Content-Type': 'application/json',
        }
        req = urllib.request.Request(GITHUB_PATH + '/releases',
                                     json.dumps(data).encode(), headers)
        with urllib.request.urlopen(req, auth=(GITHUB_USER, GITHUB_PSWD)) as res:
            body = res.read()
            body = json.loads(body)
            upload_url = body['upload_url']
    file_name = get_archive_name(conf)
    upload_url = re.sub(r'assets.*', '', upload_url)
    upload_url = upload_url + 'assets?name=' + os.path.basename(file_name)
    util_exec('curl', '-v',
              '-u', GITHUB_USER + ':' + GITHUB_PSWD,
              '-H', 'Content-Type: ' + conf['mime_type'],
              '--data-binary', '@' + get_work_path(conf, file_name),
              upload_url)

if __name__ == '__main__':
    global PATH_ROOT
    PATH_ROOT = os.path.dirname(os.path.abspath(__file__))

    args = parse_args()
    conf = parse_conf(args)
    if 'enable_build' in conf and conf['enable_build']:
        setup(conf)
        build(conf)
    if 'enable_archive' in conf and conf['enable_archive']:
        archive(conf)
    if 'enable_upload' in conf and conf['enable_upload']:
        upload(conf)
