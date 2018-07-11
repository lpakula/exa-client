#!/usr/bin/python
# -*- coding: utf-8 -*-
from fabric.api import local, hide, lcd
from fabric.colors import green


def initapp():
    """
    Init application (create spec file)
    :return:
    """

    local('docker run -v "$(pwd):/src/" cdrx/pyinstaller-linux "pyinstaller -w -F '
          '--add-data \"templates:templates\" --add-data \"static:static\" __init__.py"')


def buildapp(version):
    """
    Build applications

    """
    for client in ['linux', 'windows']:
        with lcd('src'):
            local('docker run -v "$(pwd):/src/" cdrx/pyinstaller-{}'.format(client))
        with lcd('src/dist/{}'.format(client)):
            local('zip ../../../app/exa-client_{client}_{version}.zip exa exa.exe'.format(
                client=client, version=version))


def checksum(version):
    """
    Generate checksum for apps
    
    """

    for client in ['linux', 'windows', 'macos']:
        output = local('sha1sum ../app/exa-client_{client}_{version}.zip'.format(
            client=client, version=version), capture=True)
        print(green(output))
