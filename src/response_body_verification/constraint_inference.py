# /src/response_body_verification/constraint_inference.py

from utils.openapi_utils import *
from utils.gptcall import GPTChatCompletion
import re
import json
from constant import (
    DESCRIPTION_OBSERVATION_PROMPT,
    NAIVE_CONSTRAINT_DETECTION_PROMPT,
    CONSTRAINT_CONFIRMATION,
)


def extract_variables(statement):
    variable_pattern = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"
    matches = re.findall(variable_pattern, statement)

    keywords = {
        "IF",
        "THEN",
        "Or",
        "OnlyOne",
        "AllOrNone",
        "ZeroOrOne",
        "AND",
        "OR",
        "NOT",
        "==",
        "!=",
        "<=",
        "<",
        ">=",
        ">",
        "+",
        "-",
        "*",
        "/",
        "True",
        "False",
        "true",
        "false",
    }

    variables = []
    for match in matches:
        if match not in keywords:
            preceding_text = statement[: statement.find(match)]
            if not (
                preceding_text.count('"') % 2 != 0 or preceding_text.count("'") % 2 != 0
            ):
                variables.append(match)

    return list(set(variables))


def extract_values(statement):
    pattern = r"\'(.*?)\'|\"(.*?)\"|(\d+\.?\d*)"
    matches = re.findall(pattern, statement)

    values = [match[0] or match[1] or match[2] for match in matches]
    return values


# This is used to extract attributes specified in OpenAPI spec (except OpenAPI keywords)
def extract_dict_attributes(input_dict, keys_list=None):
    if keys_list is None:
        keys_list = []

    for key, value in input_dict.items():
        if not key.startswith("array of") and not key.startswith("schema of"):
            keys_list.append(key)
        if isinstance(value, dict):
            extract_dict_attributes(value, keys_list)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    extract_dict_attributes(item, keys_list)
    return keys_list


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


def extract_answer(response):
    if response is None:
        return None

    if "```answer" in response:
        pattern = r"```answer\n(.*?)```"
        match = re.search(pattern, response, re.DOTALL)

        if match:
            answer = match.group(1)
            return answer.strip()
        else:
            return None
    else:
        return response.lower()


def extract_summary_constraint(response):
    if response is None:
        return None

    pattern = r"```constraint\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)

    if match:
        constraint = match.group(1)
        return constraint.strip()
    else:
        return None


def extract_idl(response):
    if response is None:
        return None

    pattern = r"```IDL\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)

    if match:
        constraint = match.group(1)
        return constraint.strip()
    else:
        return None


def is_construct_json_object(text):
    try:
        json.loads(text)
        return True
    except:
        return False


def standardize_returned_idl(idl_sentence):
    if idl_sentence is None:
        return None

    idl_lines = idl_sentence.split("\n")
    for i, line in enumerate(idl_lines):
        if ":" in line:
            idl_lines[i] = line.split(":", 1)[1].lstrip()

    result = "\n".join(idl_lines).strip("`\"'")

    return result


# Method of test_data.TestDataGenerator class
class ConstraintExtractor:
    def __init__(
        self,
        openapi_path,
        save_and_load=False,
        list_of_operations=None,
        experiment_folder="experiment",
    ) -> None:
        self.openapi_path = openapi_path
        self.save_and_load = save_and_load
        self.list_of_operations = list_of_operations
        self.experiment_folder = experiment_folder
        self.initialize()
        self.filter_params_w_descr()

    def initialize(self):
        self.openapi_spec = load_openapi(self.openapi_path)
        self.service_name = self.openapi_spec["info"]["title"]

        self.simplified_openapi = simplify_openapi(self.openapi_spec)

        self.mappings_checked = []
        self.input_parameters_checked = []
        if self.save_and_load:
            self.mappings_checked_save_path = (
                f"{self.experiment_folder}/{self.service_name}/mappings_checked.txt"
            )
            if os.path.exists(self.mappings_checked_save_path):
                self.mappings_checked = json.load(
                    open(self.mappings_checked_save_path, "r")
                )

            self.input_parameters_checked_save_path = f"{self.experiment_folder}/{self.service_name}/input_parameters_checked.txt"
            if os.path.exists(self.input_parameters_checked_save_path):
                self.input_parameters_checked = json.load(
                    open(self.input_parameters_checked_save_path, "r")
                )

        if self.list_of_operations is None:
            self.list_of_operations = list(self.simplified_openapi.keys())

    def filter_params_w_descr(self):
        """
        Create a new dict from `self.openapi_spec`, which contains only operations that have parameters/request body fields with description.
        Save the new dict to `self.operations_containing_param_w_description`

        Returns:
            dict: the value of `self.operations_containing_param_w_description`
        """
        self.operations_containing_param_w_description = {}
        # Get simplified openapi Spec with params, that each param has a description
        self.operation_param_w_descr = simplify_openapi(self.openapi_spec)

        self.total_inference = json.dumps(self.operation_param_w_descr).count(
            "(description:"
        )

        for operation in self.operation_param_w_descr:
            self.operations_containing_param_w_description[operation] = {}
            if "summary" in self.operation_param_w_descr[operation]:
                self.operations_containing_param_w_description[operation]["summary"] = (
                    self.operation_param_w_descr[operation]["summary"]
                )

            parts = ["parameters", "requestBody"]
            for part in parts:
                if (
                    self.operation_param_w_descr.get(operation, {}).get(part, None)
                    is not None
                ):
                    self.operations_containing_param_w_description[operation][part] = {}
                    if isinstance(self.operation_param_w_descr[operation][part], dict):
                        for param, value in self.operation_param_w_descr[operation][
                            part
                        ].items():
                            if "description" in value:
                                self.operations_containing_param_w_description[
                                    operation
                                ][part][param] = value

    def checkedMapping(self, mapping):
        for check_mapping in self.mappings_checked:
            if check_mapping[0] == mapping:
                return check_mapping
        return None

    def get_response_body_input_parameter_mappings_with_constraint(self):
        print("Filterring response body constraints through input parameters...")
        self.input_parameter_responsebody_mapping = json.load(
            open(
                f"{self.experiment_folder}/{self.service_name}/request_response_mappings.json",
                "r",
            )
        )
        self.response_body_input_parameter_mappings_with_constraint = copy.deepcopy(
            self.input_parameter_responsebody_mapping
        )

        for schema in self.input_parameter_responsebody_mapping:
            for attribute in self.input_parameter_responsebody_mapping[schema]:
                for mapping in self.input_parameter_responsebody_mapping[schema][
                    attribute
                ]:
                    operation, part, corresponding_attribute = mapping

                    # If the attribute does not have a description, just skip it
                    if (
                        "(description:"
                        not in self.operations_containing_param_w_description[
                            operation
                        ][part][corresponding_attribute]
                    ):
                        self.response_body_input_parameter_mappings_with_constraint[
                            schema
                        ][attribute].remove(mapping)
                        continue

                    data_type = (
                        self.operations_containing_param_w_description[operation][part][
                            corresponding_attribute
                        ]
                        .split("(description: ")[0]
                        .strip()
                    )
                    description = (
                        self.operations_containing_param_w_description[operation][part][
                            corresponding_attribute
                        ]
                        .split("(description: ")[-1][:-1]
                        .strip()
                    )

                    check_mapping = self.checkedMapping(mapping)
                    if check_mapping:
                        confirmation_status = check_mapping[1]
                        if confirmation_status != "yes":
                            if (
                                mapping
                                in self.response_body_input_parameter_mappings_with_constraint[
                                    schema
                                ][
                                    attribute
                                ]
                            ):
                                self.response_body_input_parameter_mappings_with_constraint[
                                    schema
                                ][
                                    attribute
                                ].remove(
                                    mapping
                                )
                        continue

                    # generate an observation for the current description
                    description_observation_prompt = (
                        DESCRIPTION_OBSERVATION_PROMPT.format(
                            attribute=corresponding_attribute,
                            data_type=data_type,
                            description=description,
                        )
                    )
                    description_observation_response = GPTChatCompletion(
                        description_observation_prompt, model="gpt-4-turbo"
                    )

                    # assert that the description implies constraints
                    constraint_confirmation_prompt = CONSTRAINT_CONFIRMATION.format(
                        attribute=corresponding_attribute,
                        data_type=data_type,
                        description=description,
                        description_observation=description_observation_response,
                    )
                    constraint_confirmation_response = GPTChatCompletion(
                        constraint_confirmation_prompt, model="gpt-4-turbo"
                    )
                    confirmation = extract_answer(
                        constraint_confirmation_response
                    )  # 'yes' or 'no'

                    if confirmation != "yes":
                        if (
                            mapping
                            in self.response_body_input_parameter_mappings_with_constraint[
                                schema
                            ][
                                attribute
                            ]
                        ):
                            self.response_body_input_parameter_mappings_with_constraint[
                                schema
                            ][attribute].remove(mapping)

                    self.mappings_checked.append(
                        [mapping, confirmation]
                    )  # 'yes' if this is a valid constraint, otherwise 'no'

                    # update checked mappings to file
                    if self.save_and_load:
                        with open(self.mappings_checked_save_path, "w") as file:
                            json.dump(self.mappings_checked, file)

    def foundConstraintResponseBody(self, checking_attribute):
        for checked_attribute in self.found_responsebody_constraints:
            if checking_attribute == checked_attribute[0]:
                return checked_attribute
        return None

    def foundConstraintInputParameter(self, checking_parameter):
        for checked_parameter in self.input_parameters_checked:
            if checking_parameter == checked_parameter[0]:
                return checked_parameter
        return None

    def get_input_parameter_constraints(self, outfile=None):
        print("Inferring constaints inside input parameters...")
        self.input_parameter_constraints = {}

        progress_size = len(self.list_of_operations) * 2
        completed = 0

        for operation in self.list_of_operations:
            self.input_parameter_constraints[operation] = {
                "parameters": {},
                "requestBody": {},
            }
            parts = ["parameters", "requestBody"]
            for part in parts:
                print(
                    f"[{self.service_name}] progess: {round(completed/progress_size*100, 2)}"
                )
                completed += 1

                specification = self.simplified_openapi.get(operation, {}).get(part, {})
                operation_path = operation.split("-")[1]
                operation_name = operation.split("-")[0]
                full_specifications = (
                    self.openapi_spec.get("paths", {})
                    .get(operation_path, {})
                    .get(operation_name, {})
                    .get(part, {})
                )
                if not specification:
                    continue
                for parameter in specification:
                    parameter_name = parameter

                    # if "(description:" not in specification[parameter]:
                    #     continue

                    data_type = (
                        specification[parameter_name].split("(description: ")[0].strip()
                    )

                    description = (
                        specification[parameter_name]
                        .split("(description: ")[-1][:-1]
                        .strip()
                    )
                    # if not description:
                    #     continue

                    param_spec = {}
                    for spec in full_specifications:
                        if isinstance(spec, str):
                            continue
                        if spec.get("name", "") == parameter_name:
                            param_spec = spec
                            break

                    param_schema = param_spec.get("schema", {})
                    if param_schema:
                        param_schema = json.dumps(param_schema)

                    checking_parameter = [parameter_name, specification[parameter_name]]

                    checked_parameter = self.foundConstraintInputParameter(
                        checking_parameter
                    )
                    if checked_parameter:
                        confirmation_status = checked_parameter[1]
                        if confirmation_status == "yes":
                            if (
                                parameter_name
                                not in self.input_parameter_constraints[operation][part]
                            ):
                                self.input_parameter_constraints[operation][part][
                                    parameter
                                ] = specification[parameter_name]
                        continue

                    description_observation_prompt = (
                        DESCRIPTION_OBSERVATION_PROMPT.format(
                            attribute=parameter_name,
                            data_type=data_type,
                            description=description,
                            param_schema=param_schema,
                        )
                    )
                    print(description_observation_prompt)
                    print(
                        f"Observing operation: {operation} - part: {part} - parameter: {parameter_name}"
                    )
                    # description_observation_response = GPTChatCompletion(description_observation_prompt,model = "gpt-4-turbo")
                    # print(description_observation_response)
                    # constraint_confirmation_prompt = CONSTRAINT_CONFIRMATION.format(
                    #     attribute = parameter_name,
                    #     data_type = data_type,
                    #     description_observation = description_observation_response,
                    #     description = description,
                    #     param_schema = param_schema
                    # )

                    # constraint_confirmation_response = GPTChatCompletion(constraint_confirmation_prompt, model = "gpt-4-turbo")
                    # print("---\n", constraint_confirmation_prompt)
                    # confirmation = extract_answer(constraint_confirmation_response) # 'yes' or 'no'
                    # print (f"Operation: {operation} - part: {part} - parameter: {parameter_name} - Confirmation: {confirmation}")

                    confirmation = "yes"
                    if confirmation == "yes":
                        if (
                            parameter_name
                            not in self.input_parameter_constraints[operation][part]
                        ):
                            self.input_parameter_constraints[operation][part][
                                parameter_name
                            ] = specification[parameter_name]

                    self.input_parameters_checked.append(
                        [checking_parameter, confirmation]
                    )

                    # update checked mappings to file
                    if self.save_and_load:
                        with open(self.input_parameters_checked_save_path, "w") as file:
                            json.dump(self.input_parameters_checked, file)

                    if outfile is not None:
                        with open(outfile, "w") as file:
                            json.dump(self.input_parameter_constraints, file, indent=2)

    def get_inside_response_body_constraints_naive(
        self, selected_schemas=None, outfile=None
    ):
        print("Inferring constraints inside response body...")
        self.inside_response_body_constraints = {}

        # simplified all schemas (including attribute name and its description)
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)

        # this is use for extracting all schemas specified in response body
        response_body_specified_schemas = []
        operations = extract_operations(self.openapi_spec)
        for operation in operations:
            _, relevant_schemas_in_response = (
                get_relevent_response_schemas_of_operation(self.openapi_spec, operation)
            )
            response_body_specified_schemas.extend(relevant_schemas_in_response)
        response_body_specified_schemas = list(set(response_body_specified_schemas))

        self.found_responsebody_constraints = []
        print(f"Schemas: {response_body_specified_schemas}")
        if selected_schemas is not None:
            response_body_specified_schemas = selected_schemas
        for schema in response_body_specified_schemas:
            self.inside_response_body_constraints[schema] = {}

            attributes = self.simplified_schemas.get(schema, {})
            if not attributes:
                continue

            for parameter_name in attributes:
                if (
                    "(description:"
                    not in self.simplified_schemas[schema][parameter_name]
                ):
                    continue

                data_type = (
                    self.simplified_schemas[schema][parameter_name]
                    .split("(description: ")[0]
                    .strip()
                )

                description = (
                    self.simplified_schemas[schema][parameter_name]
                    .split("(description: ")[-1][:-1]
                    .strip()
                )
                if not description:
                    continue

                checking_attribute = [
                    parameter_name,
                    self.simplified_schemas[schema][parameter_name],
                ]

                checked_attribute = self.foundConstraintResponseBody(checking_attribute)
                if checked_attribute:
                    confirmation_status = checked_attribute[1]
                    if confirmation_status == "yes":
                        if (
                            parameter_name
                            not in self.inside_response_body_constraints[schema]
                        ):
                            self.inside_response_body_constraints[schema][
                                parameter_name
                            ] = description
                    continue

                constraint_confirmation_prompt = (
                    NAIVE_CONSTRAINT_DETECTION_PROMPT.format(
                        attribute=parameter_name,
                        data_type=data_type,
                        description=description,
                    )
                )

                constraint_confirmation_response = GPTChatCompletion(
                    constraint_confirmation_prompt, model="gpt-4-turbo"
                )
                confirmation = extract_answer(
                    constraint_confirmation_response
                )  # 'yes' or 'no'

                if confirmation == "yes":
                    if (
                        parameter_name
                        not in self.inside_response_body_constraints[schema]
                    ):
                        self.inside_response_body_constraints[schema][
                            parameter_name
                        ] = description
                print(
                    f"Schema: {schema} - attribute: {parameter_name} - Confirmation: {confirmation}"
                )
                self.found_responsebody_constraints.append(
                    [checking_attribute, confirmation]
                )

                if outfile is not None:
                    with open(outfile, "w") as file:
                        json.dump(self.inside_response_body_constraints, file, indent=2)

    def get_inside_response_body_constraints(self, selected_schemas=None, outfile=None):
        print("Inferring constraints inside response body...")
        self.inside_response_body_constraints = {}
        if os.path.exists(outfile):
            self.inside_response_body_constraints = json.load(open(outfile, "r"))

        # simplified all schemas (including attribute name and its description)
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)

        # this is use for extracting all schemas specified in response body
        response_body_specified_schemas = []
        operations = extract_operations(self.openapi_spec)
        for operation in operations:
            _, relevant_schemas_in_response = (
                get_relevent_response_schemas_of_operation(self.openapi_spec, operation)
            )
            response_body_specified_schemas.extend(relevant_schemas_in_response)
        response_body_specified_schemas = list(set(response_body_specified_schemas))

        self.found_responsebody_constraints = []
        print(f"Schemas: {response_body_specified_schemas}")
        if selected_schemas is not None:
            response_body_specified_schemas = selected_schemas
        for schema in response_body_specified_schemas:
            if schema in self.inside_response_body_constraints:
                if schema != "ContentRating":
                    continue
            else:
                self.inside_response_body_constraints[schema] = {}

            attributes = self.simplified_schemas.get(schema, {})
            if not attributes:
                continue

            for parameter_name in attributes:
                if schema == "ContentRating":
                    if parameter_name in self.inside_response_body_constraints[schema]:
                        continue
                if (
                    "(description:"
                    not in self.simplified_schemas[schema][parameter_name]
                ):
                    continue

                data_type = (
                    self.simplified_schemas[schema][parameter_name]
                    .split("(description: ")[0]
                    .strip()
                )

                description = (
                    self.simplified_schemas[schema][parameter_name]
                    .split("(description: ")[-1][:-1]
                    .strip()
                )
                if not description:
                    continue

                checking_attribute = [
                    parameter_name,
                    self.simplified_schemas[schema][parameter_name],
                ]

                checked_attribute = self.foundConstraintResponseBody(checking_attribute)
                if checked_attribute:
                    confirmation_status = checked_attribute[1]
                    if confirmation_status == "yes":
                        if (
                            parameter_name
                            not in self.inside_response_body_constraints[schema]
                        ):
                            self.inside_response_body_constraints[schema][
                                parameter_name
                            ] = description
                    continue

                description_observation_prompt = DESCRIPTION_OBSERVATION_PROMPT.format(
                    attribute=parameter_name,
                    data_type=data_type,
                    description=description,
                    param_schema="",
                )
                print(f"Observing schema: {schema} - attribute: {parameter_name}")

                description_observation_response = GPTChatCompletion(
                    description_observation_prompt, model="gpt-4-turbo"
                )
                with open("prompt.txt", "w", encoding="utf-16") as file:
                    file.write(f"PROMPT: {description_observation_prompt}\n")
                    file.write(f"---\n")
                    file.write(f"RESPONSE: {description_observation_response}\n")

                constraint_confirmation_prompt = CONSTRAINT_CONFIRMATION.format(
                    attribute=parameter_name,
                    data_type=data_type,
                    description_observation=description_observation_response,
                    description=description,
                    param_schema="",
                )

                print(f"Confirming schema: {schema} - attribute: {parameter_name}")
                constraint_confirmation_response = GPTChatCompletion(
                    constraint_confirmation_prompt, model="gpt-4-turbo"
                )
                confirmation = extract_answer(
                    constraint_confirmation_response
                )  # 'yes' or 'no'
                with open("prompt.txt", "a", encoding="utf-16") as file:
                    file.write(f"PROMPT: {constraint_confirmation_prompt}\n")
                    file.write(f"---\n")
                    file.write(f"RESPONSE: {constraint_confirmation_response}\n")

                if confirmation == "yes":
                    if (
                        parameter_name
                        not in self.inside_response_body_constraints[schema]
                    ):
                        self.inside_response_body_constraints[schema][
                            parameter_name
                        ] = description
                print(
                    f"Schema: {schema} - attribute: {parameter_name} - Confirmation: {confirmation}"
                )
                self.found_responsebody_constraints.append(
                    [checking_attribute, confirmation]
                )

                if outfile is not None:
                    with open(outfile, "w", encoding="utf-16") as file:
                        json.dump(self.inside_response_body_constraints, file, indent=2)


def main():
    pass


if __name__ == "__main__":
    main()
