# /src/constraints_test_generation.py

import re
import os
import json
import dotenv
import pandas as pd
import urllib.parse
import openai
import yaml
from utils.openapi_utils import (
    load_openapi,
    simplify_openapi,
    get_simplified_schema,
    get_response_body_name_and_type,
)
from utils.gptcall import GPTChatCompletion
from utils.dict_utils import filter_dict_by_key
from constant import (
    CONST_INSIDE_RESPONSEBODY_SCRIPT_GEN_PROMPT,
    CONST_RESPONSEBODY_PARAM_SCRIPT_GEN_PROMPT,
    TEST_EXECUTION_SCRIPT,
    TEST_INPUT_PARAM_EXECUTION_SCRIPT,
)

dotenv.load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY")


def extract_response_field(response, field):
    if response is None:
        return None

    if f"```{field}" in response:
        pattern = rf"```{field}\n(.*?)```"
        match = re.search(pattern, response, re.DOTALL)

        if match:
            answer = match.group(1)
            return answer.strip()
        else:
            return None
    else:
        return response.lower()


def unescape_string(escaped_str):
    try:
        return bytes(escaped_str, "utf-8").decode("unicode_escape")
    except:
        return escaped_str


def is_valid_url(url):
    parsed_url = urllib.parse.urlparse(url)
    return all([parsed_url.scheme, parsed_url.netloc])


def parse_request_info_from_query_parameters(query_parameters):
    request_info = {}
    # query_parameters is a string in the format of "key1=value1&key2=value2&..."
    if query_parameters:
        query_parameters = urllib.parse.parse_qs(query_parameters)
        for key, value in query_parameters.items():
            request_info[key] = value[0]
    return json.dumps(request_info)


def extract_python_code(response):
    if response is None:
        return None

    pattern = r"```python\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)

    if match:
        python_code = match.group(1)
        return python_code
    else:
        return None


def execute_response_constraint_verification_script(python_code, api_response):
    script_string = TEST_EXECUTION_SCRIPT.format(
        generated_verification_script=python_code, api_response=api_response
    )

    namespace = {}
    try:
        exec(script_string, namespace)
    except Exception as e:
        print(f"Error executing the script: {e}")
        return script_string, "code error"

    code = namespace["status"]
    status = ""
    if code == -1:
        status = "mismatched"
    elif code == 1:
        status = "satisfied"
    else:
        status = "unknown"

    return script_string, status


def execute_request_parameter_constraint_verification_script(
    python_code, api_response, request_info
):
    script_string = TEST_INPUT_PARAM_EXECUTION_SCRIPT.format(
        generated_verification_script=python_code,
        api_response=api_response,
        request_info=request_info,
    )

    namespace = {}
    try:
        exec(script_string, namespace)
    except Exception as e:
        print(f"Error executing the script: {e}")
        return script_string, "code error"

    code = namespace["status"]
    status = ""
    if code == -1:
        status = "mismatched"
    elif code == 1:
        status = "satisfied"
    else:
        status = "unknown"

    return script_string, status


def export_file(prompt, response, filename):
    with open(filename, "a") as file:
        file.write(f"Prompt:\n{prompt}\n\n")
        file.write(f"Response:\n{response}\n")


class VerificationScriptGenerator:
    def __init__(
        self,
        service_name,
        experiment_dir,
        request_response_constraints_file=None,
        response_property_constraints_file=None,
    ):
        self.openapi_spec = load_openapi(f"RBCTest_dataset/{service_name}/openapi.json")
        self.simplified_openapi = simplify_openapi(self.openapi_spec)
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)
        self.experiment_dir = experiment_dir
        with open("simplified_openapi.json", "w") as file:
            json.dump(self.simplified_openapi, file, indent=2)
        self.service_name = service_name
        service_name = self.openapi_spec["info"]["title"]
        self.experiment_dir = f"{experiment_dir}/{service_name}"

        self.generated_verification_scripts = []

        if request_response_constraints_file:
            self.request_response_constraints_file = request_response_constraints_file
            self.request_response_constraints_df = pd.read_excel(
                request_response_constraints_file, sheet_name="Sheet1"
            )
            self.request_response_constraints_df = (
                self.request_response_constraints_df.fillna("")
            )
            self.verify_request_parameter_constraints()

        if response_property_constraints_file:
            self.response_property_constraints_file = response_property_constraints_file
            self.response_property_constraints_df = pd.read_excel(
                response_property_constraints_file, sheet_name="Sheet1"
            )
            self.response_property_constraints_df = (
                self.response_property_constraints_df.fillna("")
            )
            self.verify_inside_response_body_constraints()

    def track_generated_script(self, generating_script):
        for generated_script in self.generated_verification_scripts:
            if (
                generated_script["response_resource"]
                == generating_script["response_resource"]
                and generated_script["attribute"] == generating_script["attribute"]
                and generated_script["description"] == generating_script["description"]
                and generated_script["operation"] == generating_script["operation"]
            ):
                return generated_script
        return None

    def verify_inside_response_body_constraints(self):
        verification_scripts = [""] * len(self.response_property_constraints_df)
        executable_scripts = [""] * len(self.response_property_constraints_df)
        statuses = [""] * len(self.response_property_constraints_df)

        confirmations = [""] * len(self.response_property_constraints_df)
        revised_scripts = [""] * len(self.response_property_constraints_df)
        revised_executable_scripts = [""] * len(self.response_property_constraints_df)
        revised_script_statuses = [""] * len(self.response_property_constraints_df)

        for index, row in self.response_property_constraints_df.iterrows():
            response_resource = row["response resource"]
            attribute = row["attribute"]
            description = row["description"]
            operation = row["operation"]

            print(
                f"Generating verification script for {response_resource} - {attribute} - {description}"
            )

            generating_script = {
                "operation": operation,
                "response_resource": response_resource,
                "attribute": attribute,
                "description": description,
                "verification_script": "",
                "executable_script": "",
                "status": "",
                "confirmation": "",
                "revised_script": "",
                "revised_executable_script": "",
                "revised_status": "",
            }

            generated_script = self.track_generated_script(generating_script)
            if generated_script:
                verification_scripts[index] = generated_script["verification_script"]
                executable_scripts[index] = generated_script["executable_script"]
                statuses[index] = generated_script["status"]
                confirmations[index] = generated_script["confirmation"]
                revised_scripts[index] = generated_script["revised_script"]
                revised_executable_scripts[index] = generated_script[
                    "revised_executable_script"
                ]
                revised_script_statuses[index] = generated_script["revised_status"]
                continue

            response_specification = self.simplified_openapi[operation].get(
                "responseBody", {}
            )
            response_specification = filter_dict_by_key(
                response_specification, attribute
            )

            response_schema_structure = ""
            main_response_schema_name, response_type = get_response_body_name_and_type(
                self.openapi_spec, operation
            )
            print(f"Main response schema name: {main_response_schema_name}")
            print(f"Response type: {response_type}")
            if not main_response_schema_name:
                response_schema_structure = response_type
            else:
                if response_type == "object":
                    response_schema_structure = f"{main_response_schema_name} object"
                else:
                    response_schema_structure = (
                        f"array of {main_response_schema_name} objects"
                    )

            response_schema_specification = ""
            if main_response_schema_name:
                response_schema_specification = f"- Data structure of the response body: {response_schema_structure}\n- Specification of {main_response_schema_name} object: {json.dumps(response_specification)}"
            else:
                response_schema_specification = f"- Data structure of the response body: {response_schema_structure}\n- Specification: {json.dumps(response_specification)}"

            attribute_spec = self.simplified_schemas.get(response_resource, {}).get(
                attribute, ""
            )
            other_description = ""

            attribute_spec = (
                self.openapi_spec.get("components", {})
                .get("schemas", {})
                .get(response_resource, {})
                .get("properties", {})
                .get(attribute, "")
            )
            if not attribute_spec:
                attribute_spec = (
                    self.openapi_spec.get("definitions", {})
                    .get(response_resource, {})
                    .get("properties", {})
                    .get(attribute, "")
                )

            if attribute_spec:
                other_description = json.dumps(attribute_spec)

            python_verification_script_generation_prompt = (
                CONST_INSIDE_RESPONSEBODY_SCRIPT_GEN_PROMPT.format(
                    attribute=attribute,
                    description=other_description if other_description else description,
                    response_schema_specification=response_schema_specification,
                )
            )
            print(python_verification_script_generation_prompt)

            with open(f"{self.experiment_dir}/prompts.txt", "a") as file:
                file.write(
                    f"Prompt for constraint {index}:\n{python_verification_script_generation_prompt}\n"
                )

            python_verification_script_response = GPTChatCompletion(
                python_verification_script_generation_prompt, model="gpt-4-turbo"
            )

            # export_file(python_verification_script_generation_prompt, python_verification_script_response, f"constraint_{index}.txt")

            print(f"Generated script: {python_verification_script_response}")

            python_verification_script = extract_python_code(
                python_verification_script_response
            )

            # script_string, status = execute_response_constraint_verification_script(python_verification_script, row['API response'])
            script_string = verification_scripts
            status = "unknown"

            verification_scripts[index] = python_verification_script
            executable_scripts[index] = script_string
            statuses[index] = status

            generating_script["verification_script"] = python_verification_script
            generating_script["executable_script"] = script_string
            generating_script["status"] = status

            self.generated_verification_scripts.append(generating_script)

            # Confirm the generated script
            # python_verification_script_confirm_prompt = CONST_INSIDE_RESPONSEBODY_SCRIPT_CONFIRM_PROMPT.format(
            #     attribute = attribute,
            #     description = description,
            #     response_schema_specification = response_schema_specification,
            #     generated_verification_script = python_verification_script
            # )

            # confirmation_response = GPTChatCompletion(python_verification_script_confirm_prompt, model="gpt-4-turbo")

            # export_file(python_verification_script_confirm_prompt, confirmation_response, f"constraint_{index}.txt")

            # firstline = confirmation_response.split("\n")[0]

            # if "yes" in firstline:
            #     confirmations[index] = "yes"
            # else:
            #     confirmation_answer = "no"

            #     print(f"Confirmation answer: {confirmation_answer}")
            #     revised_script = extract_python_code(confirmation_response)
            #     revised_script = unescape_string(revised_script)

            #     confirmations[index] = confirmation_answer
            #     revised_scripts[index] = revised_script

            #     print(f"Revised script: {revised_script}")

            #     revised_script_string, revised_status = execute_response_constraint_verification_script(revised_script, row['API response'])

            #     revised_script_statuses[index] = revised_status
            #     revised_executable_scripts[index] = revised_script_string

            #     generating_script["confirmation"] = confirmation_answer
            #     generating_script["revised_script"] = revised_script
            #     generating_script["revised_executable_script"] = revised_script_string
            #     generating_script["revised_status"] = revised_status

            self.response_property_constraints_df["verification script"] = pd.array(
                verification_scripts
            )
            # self.response_property_constraints_df['executable script'] = pd.array(executable_scripts)
            self.response_property_constraints_df["status"] = pd.array(statuses)

            self.response_property_constraints_df["script confirmation"] = pd.array(
                confirmations
            )

            self.response_property_constraints_df["revised script"] = pd.array(
                revised_scripts
            )
            self.response_property_constraints_df["revised executable script"] = (
                pd.array(revised_executable_scripts)
            )
            self.response_property_constraints_df["revised status"] = pd.array(
                revised_script_statuses
            )

            self.response_property_constraints_df.to_excel(
                self.response_property_constraints_file,
                sheet_name="Sheet1",
                index=False,
            )

    def track_generated_request_parameter_script(self, generating_script):
        for generated_script in self.generated_verification_scripts:
            require_keys = [
                "response_resource",
                "attribute",
                "description",
                "corresponding_operation",
                "corresponding_attribute",
                "corresponding_description",
                "operation",
            ]
            for key in require_keys:
                if generated_script[key] != generating_script[key]:
                    return None
            return generated_script
        return None

    def verify_request_parameter_constraints(self):
        verification_scripts = [""] * len(self.request_response_constraints_df)
        executable_scripts = [""] * len(self.request_response_constraints_df)

        statuses = [""] * len(self.request_response_constraints_df)
        confirmations = [""] * len(self.request_response_constraints_df)
        revised_scripts = [""] * len(self.request_response_constraints_df)
        revised_executable_scripts = [""] * len(self.request_response_constraints_df)
        revised_script_statuses = [""] * len(self.request_response_constraints_df)

        self.generated_verification_scripts_responsebody_input_parameter = []
        for index, row in self.request_response_constraints_df.iterrows():
            response_resource = row["response resource"]
            attribute = row["attribute"]
            description = str(row["description"])
            corresponding_operation = (row["attribute inferred from operation"],)
            corresponding_part = row["part"]
            corresponding_attribute = row["corresponding attribute"]
            corresponding_description = row["corresponding attribute description"]
            # *******
            constraint_correctness = row["constraint_correctness"]
            tp = row["tp"]
            if not (constraint_correctness == "TP" and tp == 0):
                print(
                    f"Skipping {response_resource} - {attribute} - {description} As it has been processed before"
                )
                continue

            verification_script = (
                row["verification script"] if "verification script" in row else None
            )
            executable_script = (
                row["executable script"] if "executable script" in row else None
            )
            status = row["status"] if "status" in row else None
            confirmation = (
                row["script confirmation"] if "script confirmation" in row else None
            )
            revised_script = row["revised script"] if "revised script" in row else None
            revised_executable_script = (
                row["revised executable script"]
                if "revised executable script" in row
                else None
            )
            revised_status = row["revised status"] if "revised status" in row else None

            print(f"Previous verification script: {verification_script}")
            print(f"Previous executable script: {executable_script}")
            print(f"Previous status: {status}")

            # if verification_script and executable_script and status:
            #     verification_scripts[index] = verification_script
            #     executable_scripts[index] = executable_script
            #     statuses[index] = status
            #     confirmations[index] = confirmation
            #     revised_scripts[index] = revised_script
            #     revised_executable_scripts[index] = revised_executable_script
            #     revised_script_statuses[index] = revised_status
            #     print(f"Skipping {response_resource} - {attribute} - {description} As it has been processed before")
            #     continue

            operation = corresponding_operation[0]
            generating_script = {
                "operation": operation,
                "response_resource": response_resource,
                "attribute": attribute,
                "description": description,
                "corresponding_operation": corresponding_operation,
                "corresponding_attribute": corresponding_attribute,
                "corresponding_description": corresponding_description,
                "verification_script": "",
                "executable_script": "",
                "status": "",
                "confirmation": "",
                "revised_script": "",
                "revised_executable_script": "",
                "revised_status": "",
            }

            generated_script = self.track_generated_request_parameter_script(
                generating_script
            )
            if generated_script:
                verification_scripts[index] = generated_script["verification_script"]
                executable_scripts[index] = generated_script["executable_script"]
                statuses[index] = generated_script["status"]
                confirmations[index] = generated_script["confirmation"]
                revised_scripts[index] = generated_script["revised_script"]
                revised_executable_scripts[index] = generated_script[
                    "revised_executable_script"
                ]
                revised_script_statuses[index] = generated_script["revised_status"]
                continue

            response_specification = self.simplified_openapi[operation].get(
                "responseBody", {}
            )
            response_specification = filter_dict_by_key(
                response_specification, attribute
            )
            response_schema_structure = ""
            main_response_schema_name, response_type = get_response_body_name_and_type(
                self.openapi_spec, operation
            )
            print(f"Main response schema name: {main_response_schema_name}")
            print(f"Response type: {response_type}")
            if not main_response_schema_name:
                response_schema_structure = response_type
            else:
                if response_type == "object":
                    response_schema_structure = f"{main_response_schema_name} object"
                else:
                    response_schema_structure = (
                        f"array of {main_response_schema_name} objects"
                    )

            response_schema_specification = ""
            if main_response_schema_name:
                response_schema_specification = f"- Data structure of the response body: {response_schema_structure}\n- Specification of {main_response_schema_name} object: {json.dumps(response_specification)}"
            else:
                response_schema_specification = f"- Data structure of the response body: {response_schema_structure}\n- Specification: {json.dumps(response_specification)}"

            print(f"Response schema specification: {response_schema_specification}")

            attribute_spec = self.simplified_schemas.get(response_resource, {}).get(
                attribute, ""
            )
            other_description = ""

            attribute_spec = (
                self.openapi_spec.get("components", {})
                .get("schemas", {})
                .get(response_resource, {})
                .get("properties", {})
                .get(attribute, "")
            )
            if not attribute_spec:
                attribute_spec = (
                    self.openapi_spec.get("definitions", {})
                    .get(response_resource, {})
                    .get("properties", {})
                    .get(attribute, "")
                )

            if attribute_spec:
                other_description = yaml.dump(attribute_spec)

            corresponding_operation = corresponding_operation[0]
            cor_operation, path = corresponding_operation.split("-", 1)
            print(
                f"Finding parameter constraints for {corresponding_attribute} in {cor_operation} in corresponding part {corresponding_part} - {path}"
            )
            parameters = (
                self.openapi_spec.get("paths", {})
                .get(path, {})
                .get(cor_operation, {})
                .get(corresponding_part, {})
            )
            if corresponding_part == "parameters":
                parameter_spec = {}
                for parameter in parameters:
                    if parameter["name"] == corresponding_attribute:
                        parameter_spec = yaml.dump(parameter)
                        break

            elif corresponding_part == "requestBody":
                parameter_spec = (
                    parameters.get("content", {})
                    .get("application/x-www-form-urlencoded", {})
                    .get("schema", {})
                    .get("properties", {})
                    .get(corresponding_attribute, {})
                )
                if not parameter_spec:
                    parameter_spec = (
                        parameters.get("content", {})
                        .get("application/json", {})
                        .get("schema", {})
                        .get("properties", {})
                        .get(corresponding_attribute, {})
                    )
                parameter_spec = yaml.dump(parameter_spec)

            attribute_information = ""
            if other_description:
                attribute_information = f"-Corresponding attribute {attribute}\n- Description: {other_description}"
            else:
                attribute_information = f"- Corresponding attribute: {attribute}"

            python_verification_script_generation_prompt = (
                CONST_RESPONSEBODY_PARAM_SCRIPT_GEN_PROMPT.format(
                    parameter=corresponding_attribute,
                    parameter_description=parameter_spec,
                    response_schema_specification=response_schema_specification,
                    attribute_information=attribute_information,
                    attribute=attribute,
                )
            )

            export_file(
                python_verification_script_generation_prompt,
                "python_verification_script_response",
                f"constraint_{index}.txt",
            )
            print(python_verification_script_generation_prompt)
            # input(f"{index} - Press Enter to continue...")

            python_verification_script_response = GPTChatCompletion(
                python_verification_script_generation_prompt, model="gpt-4-turbo"
            )
            python_verification_script = extract_python_code(
                python_verification_script_response
            )
            # script_string, status = execute_request_parameter_constraint_verification_script(python_verification_script, row['API response'], row['request information'])
            verification_scripts[index] = python_verification_script
            # executable_scripts[index] = script_string
            statuses[index] = "unknown"

            # generating_script["verification_script"] = python_verification_script
            # generating_script["executable_script"] = script_string
            # generating_script["status"] = status

            # self.generated_verification_scripts_responsebody_input_parameter.append(generating_script)

            # # Confirm the generated script
            # python_verification_script_confirm_prompt = CONST_RESPONSEBODY_PARAM_SCRIPT_CONFIRM_PROMPT.format(
            #     parameter = corresponding_attribute,
            #     parameter_description = corresponding_description,
            #     response_schema_specification = response_schema_specification,
            #     attribute_information = attribute_information,
            #     attribute = attribute,
            #     generated_verification_script = python_verification_script
            # )

            # confirmation_response = GPTChatCompletion(python_verification_script_confirm_prompt, model="gpt-4-turbo")
            # export_file(python_verification_script_confirm_prompt, confirmation_response, f"constraint_{index}.txt")
            # # input("Press Enter to continue...")

            # firstline = confirmation_response.split("\n")[0]

            # if "yes" in firstline:
            #     confirmations[index] = "yes"
            # else:
            #     confirmation_answer = "no"

            #     revised_script = extract_python_code(confirmation_response)
            #     revised_script = unescape_string(revised_script)

            #     confirmations[index] = confirmation_answer
            #     revised_scripts[index] = revised_script

            #     revised_script_string, revised_status = execute_request_parameter_constraint_verification_script(revised_script, row['API response'], row['request information'])

            #     revised_script_statuses[index] = revised_status
            #     revised_executable_scripts[index] = revised_script_string

            #     generating_script["confirmation"] = confirmation_answer
            #     generating_script["revised_script"] = revised_script
            #     generating_script["revised_executable_script"] = revised_script_string
            #     generating_script["revised_status"] = revised_status

            self.request_response_constraints_df["verification script"] = pd.array(
                verification_scripts
            )
            self.request_response_constraints_df["executable script"] = pd.array(
                executable_scripts
            )
            self.request_response_constraints_df["status"] = pd.array(statuses)

            self.request_response_constraints_df["script confirmation"] = pd.array(
                confirmations
            )
            self.request_response_constraints_df["revised script"] = pd.array(
                revised_scripts
            )
            self.request_response_constraints_df["revised executable script"] = (
                pd.array(revised_executable_scripts)
            )
            self.request_response_constraints_df["revised status"] = pd.array(
                revised_script_statuses
            )

            self.request_response_constraints_df.to_excel(
                self.request_response_constraints_file, sheet_name="Sheet1", index=False
            )


if __name__ == "__main__":
    # service_names = ["GitLab Groups", "GitLab Issues", "GitLab Project", "GitLab Repository",]
    service_names = [
        "GitLab Groups",
        "GitLab Issues",
        "GitLab Project",
        "GitLab Repository",
        "GitLab Branch",
        "GitLab Commit",
    ]
    experiment_dir = "approaches/new_method_our_data copy 2"
    excel_file_name = [
        "request_response_constraints.xlsx",
        "response_property_constraints.xlsx",
    ]

    for service_name in service_names:
        # try:
        response_property_constraints_file = (
            f"{experiment_dir}/{service_name} API/{excel_file_name[1]}"
        )
        request_response_constraints_file = (
            f"{experiment_dir}/{service_name} API/{excel_file_name[0]}"
        )

        # if os.path.exists(response_property_constraints_file):
        #     VerificationScriptGenerator(service_name, experiment_dir, response_property_constraints_file=response_property_constraints_file)

        if os.path.exists(request_response_constraints_file):
            VerificationScriptGenerator(
                service_name,
                experiment_dir,
                request_response_constraints_file=request_response_constraints_file,
            )
        else:
            print(f"File {request_response_constraints_file} does not exist")

        with open(f"LOG.txt", "a") as file:
            file.write(f"Successfully processed {service_name}\n")

    # except Exception as e:
    #     print(f"Error processing {service_name}: {e}")
    #     with open(f"LOG.txt", "a") as file:
    #         file.write(f"Error processing {service_name}: {e}\n")
