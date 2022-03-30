import os
import argparse
import yaml
from yaml.constructor import SafeConstructor
from yaml.reader import *
from yaml.scanner import *
from yaml.parser import *
from yaml.composer import *
from yaml.resolver import *
from string import Template
from typing import Tuple
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--path", "-p", help="path to workflows", required=True)

# https://stackoverflow.com/a/58593978
# Create custom safe constructor class that inherits from SafeConstructor
class MySafeConstructor(SafeConstructor):
    # Create new method handle boolean logic
    def add_bool(self, node):
        return self.construct_scalar(node)

class MySafeLoader(Reader, Scanner, Parser, Composer, MySafeConstructor, Resolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        MySafeConstructor.__init__(self)
        Resolver.__init__(self)

# Inject the above boolean logic into the custom constuctor
MySafeConstructor.add_constructor('tag:yaml.org,2002:bool',
                                      MySafeConstructor.add_bool)

def get_value(value: str,default: str) -> str :
    if value != None:
        return value
    return default

def generate_data(file_path: str) -> Tuple[str, str]:
    file = open(file_path, 'r')
    description = ""
    while True:
        # Get next line from file
        line = file.readline()
        # if line doesnt start with #
        # break out
        if not line.startswith("#"):
            break
        description += "{}".format(line.strip().strip("#"))

    file.close()

    with open(file_path) as f:
        data = yaml.load(f,MySafeLoader)

    template = Template(
        """
## $name
---
$description
### Inputs
$inputs
### Secrets
$secrets
        """
    )

    name = get_value(data.get("name"),Path(file_path).name)

    # if workflow_call is not set then it is not a reusable workflow
    # and should be skipped
    if data.get("on").get("workflow_call") == None:
        return None,None

    inputs = data.get("on").get("workflow_call").get("inputs")
    input_str = ""
    if inputs != None:
        for input in inputs:
            input_data = inputs.get(input)
            input_str += """
* **{0}**
    * **Description:** {1}
    * **Type:** *{2}*
    * **Required:** *{3}*
    * **Default:** *{4}*
            """.format(
                get_value(input,file_path),
                get_value(input_data.get("description"),"N/A"),
                get_value(input_data.get("type"),"N/A"),
                get_value(input_data.get("required"),"N/A"),
                get_value(input_data.get("default"),"N/A"),
            )

    secrets = data.get("on").get("workflow_call").get("secrets")
    secret_str = ""
    if secrets != None:
        for secret in secrets:
            secret_data = secrets.get(secret)
            secret_str += """
* **{0}**
    * **Description:** {1}
    * **Required:** *{2}*
            """.format(
                get_value(secret,"N/A"),
                get_value(secret_data.get("description"),"N/A"),
                get_value(secret_data.get("required"),"N/A"),
            )

    return name , template.substitute(
        {
            'name': name,
            'description': description,
            'inputs': input_str,
            'secrets': secret_str,
        }
    )

args = parser.parse_args()
path = args.path
files = os.listdir(path)
files.sort()

list_of_workflows = "# Available Reusable Workflows \n"
workflow_str = ""


for file in files:
    result = generate_data(path+file)
    if result[0] == None:
        continue
    list_of_workflows += "* [{}](#{}) \n".format(result[0],result[0].replace(" ","-"))
    workflow_str += result[1]

print(list_of_workflows , workflow_str)