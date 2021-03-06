#!/usr/bin/python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ansible.module_utils.basic import *
from six.moves.urllib.parse import urlparse

import StringIO
from datetime import datetime

try:
    import requests
except ImportError:
    requests_found = False
else:
    requests_found = True

try:  # py27
    import ConfigParser as configparser
except ImportError:
    import configparser

DOCUMENTATION = '''
---
module: dci_format_puddle_component
short_description: An ansible module to format the puddle output
version_added: 2.2
options:
  state:
    required: false
    description: Desired state of the resource
  url:
    required: true
    description: URL to parse
'''

EXAMPLES = '''
- name: Format puddle component
  dci_format_puddle_component:
    url: 'https://url/mypuddle.repo'
'''

# TODO
RETURN = '''
'''


def get_canonical_project_name(type, name, repo_name):
    """Return canonical_project_name. """

    if 'puddle_osp' in type:
        canonical_project_name = repo_name
    elif type == 'snapshot_rdo':
        canonical_project_name = name

    return canonical_project_name


def get_name(type, name_label, repo_name, version, repo_date):
    """Return name. """

    if 'puddle_osp' in type:
        name = '%s %s' % (repo_name, version)
    elif type == 'snapshot_rdo':
        name = '%s %s %s' % (name_label, repo_date, version)

    return name


def get_data(type, name, repo_name, version, base_url):
    """Return data. """

    data = {
       'path': urlparse(base_url).path,
       'version': version,
    }
    if 'puddle_osp' in type:
        data['repo_name'] = repo_name
    elif type == 'snapshot_rdo':
        data['repo_name'] = name

    return data


def get_repo_information(url, type, name):
    repo_file_obj = requests.get(url)
    repo_file = repo_file_obj._content
    output = StringIO.StringIO(repo_file)
    config = configparser.ConfigParser()
    config.readfp(output)
    # we only use the first section
    section_name = config.sections()[0]
    raw_base_url = config.get(section_name, 'baseurl')
    base_url = raw_base_url.replace("$basearch", "x86_64")
    try:
        version = config.get(section_name, 'version')
    except configparser.NoOptionError:
        # extracting the version from the URL
        if 'puddle_osp' in type:
            version = base_url.split('/')[-4]
        elif type == 'snapshot_rdo':
            version = base_url.split('/')[-1]
    repo_name = config.get(section_name, 'name')

    repo_file_date = repo_file_obj.headers['Last-Modified']
    dt = datetime.strptime(repo_file_date,  '%a, %d %b %Y %H:%M:%S GMT')
    repo_date = '%s-%s-%s' % (dt.year, dt.month, dt.day)

    component_informations = {
        'canonical_project_name': get_canonical_project_name(type, name, repo_name),
        'name': get_name(type, name, repo_name, version, repo_date),
        'url': base_url,
        'data': get_data(type, name, repo_name, version, base_url),
    }

    return component_informations


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(default='present', choices=['present', 'absent'], type='str'),
            url=dict(required=True, type='str'),
            type=dict(required=True, type='str'),
            name=dict(required=True, type='str'),
        ),
    )

    if not requests_found:
        module.fail_json(msg='The python requests module is required')

    component_informations = get_repo_information(module.params['url'],
                                                  module.params['type'],
                                                  module.params['name'])
    puddle_component = {
        'canonical_project_name': component_informations['canonical_project_name'],
        'name': component_informations['name'],
        'url': component_informations['url'],
        'data': component_informations['data'],
        'changed': False
    }

    module.exit_json(**puddle_component)


if __name__ == '__main__':
    main()
