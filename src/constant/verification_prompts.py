"""
Verification-related prompt constants used for generating verification scripts.
"""

GROOVY_SCRIPT_VERIFICATION_GENERATION_PROMPT = """Given a description implying constraints, rules, or limitations of an attribute in a REST API, your responsibility is to generate a corresponding Python script to check whether these constraints are satisfied through the API response.

Below is the attribute's description:
- "{attribute}": "{description}"

{attribute_observation}

Below is the API response's schema:
"{schema}": "{specification}"

The correspond attribute of "{attribute}" in the API response's schema is: "{corresponding_attribute}"

Below is the request information to the API: 
{request_information}

Rules: 
- Ensure that the generated Python code can verify fully these identified constraints.
- The generated Python code does not include any example of usages.
- The Python script should be generalized, without specific example values embedded in the code.
- The generated script should include segments of code to assert the satisfaction of constraints using a try-catch block.
- You'll generate a Python script using the response body variable named 'latest_response' (already defined) to verify the given constraint in the triple backticks as below: 
```python
def verify_latest_response(latest_response):
    // deploy verification flow...
    // return True if the constraint is satisfied and False otherwise.
```
- No explanation is needed."""

IDL_TRANSFORMATION_PROMPT = """You will be provided with a description specifying the constraint/rule/limitation of an attribute in natural language and a Python script to verify whether the attribute satisfies that constraint or not. Your responsibility is to specify that constraint using IDL. Follow these steps below to complete your task:

STEP 1: You will be guided to understand IDL keywords.

Below is the catalog of Inter/Inner-Parameter Dependency Language (IDL for short):

1. Conditional Dependency: This type of dependency is expressed as "IF <predicate> THEN <predicate>;", where the first predicate is the condition and the second is the consequence.
Syntax: IF <predicate> THEN <predicate>;
Example: IF custom.label THEN custom.amount; //This specification implies that if a value is provided for 'custom.label' then a value must also be provided for 'custom.amount' (or if custom.label is True, custom.amount must also be True).

2. Or: This type of dependency is expressed using the keyword "Or" followed by a list of two or more predicates placed inside parentheses: "Or(predicate, predicate [, ...]);". The dependency is satisfied if at least one of the predicates evaluates to true.
Syntax/Predicate: Or(<predicate>, <predicate>, ...);
Example: Or(header, upload_type); //This specification implies that the constraint will be satisfied if a value is provided for at least one of 'header' or 'upload_type' (or if at least one of them is True).

3. OnlyOne: These dependencies are specified using the keyword "OnlyOne" followed by a list of two or more predicates placed inside parentheses: "OnlyOne(predicate, predicate [, ...]);". The dependency is satisfied if one, and only one of the predicates evaluates to true.
Syntax/Predicate: OnlyOne(<predicate>, <predicate>, ...);
Example: OnlyOne(amount_off, percent_off); //This specification implies that the constraint will be satisfied if a value is provided for only one of 'header' or 'upload_type' (or if only one of them is set to True)

4. AllOrNone: This type of dependency is specified using the keyword "AllOrNone" followed by a list of two or more predicates placed inside parentheses: "AllOrNone(predicate, predicate [, ...]);". The dependency is satisfied if either all the predicates evaluate to true, or all of them evaluate to false.
Syntax/Predicate: AllOrNone(<predicate>, <predicate>, ...)
Example: AllOrNone(rights, filter=='track'|'album'); //This specification implies that the constraint will be satisfied under two conditions: 1. If a value is provided for 'rights,' then the value of 'filter' must also be provided, and it can only be 'track' or 'album'. 2. Alternatively, the constraint is satisfied if no value is provided for 'rights' and 'filter' (or if the value of 'filter' is not 'track' or 'album').

5. ZeroOrOne: These dependencies are specified using the keyword "ZeroOrOne" followed by a list of two or more predicates placed inside parentheses: "ZeroOrOne(predicate, predicate [, ...]);". The dependency is satisfied if none or at most one of the predicates evaluates to true.
Syntax/Predicate: ZeroOrOne(<predicate>, <predicate>, ...)
Example: ZeroOrOne(type, affiliation); // This specification implies that the constraint will be satisfied under two conditions: 1. If no value is provided for 'type' and 'affiliation' (or both are False). 2. If only one of 'type' and 'affiliation' is provided a value (or if only one of them is set to True).

6. Arithmetic/Relational: Relational dependencies are specified as pairs of parameters joined by any of the following relational operators: ==, !=, <=, <, >= or >. Arithmetic dependencies relate two or more parameters using the operators +, - , *, / followed by a final comparison using a relational operator.
Syntax: ==, !=, <=, <, >=, >, +, - , *, /
Example: created_at_min <= created_at_max; // the created_at_min is less than or equal to created_at_max

7. Boolean operators: 'AND', 'OR', 'NOT'

STEP 2: You will be provided with the attribute's description specifying a constraint in natural language and the corresponding generated Python script to verify the attribute's satisfaction for that constraint.

Below is the attribute's description:
- "{attribute}": "{description}"

Below is the specification for the {part}, where the attribute is specified:
{specification}

Below is the generated Python script to verify that constraint:
{generated_python_script}

Now, help to specify the constraint/limitation of the attribute using IDL by considering both the constraint in natural language and its verification script in Python, follow these rules below: 
- If the provided constraint description does not mention any types mentioned above, you do not need to respond with any IDL specification.
- You do not need to generate any data samples in the IDL specification sentence; instead, mention the related variables and data in the constraint description only.
- Only respond the IDL sentence and only use IDL keywords (already defined above).
- Only respond coresponding your IDL specification. 
- Respond IDL specification in the format below:
```IDL
IDL specification...
```
- No explanation is needed."""

# Add the test generation prompts
CONST_INSIDE_RESPONSEBODY_SCRIPT_GEN_PROMPT = """Given a description implying constraints, rules, or limitations of an attribute in a REST API's response, your responsibility is to generate a corresponding Python script to check whether these constraints are satisfied through the API response.

Below is the attribute's description:
- "{attribute}": "{description}"

Below is the API response's schema:
{response_schema_specification}

Now, help to generate a Python script to verify the attribute "{attribute}" in the API response. Follow these rules below:

Rules:
- Ensure that the generated Python code can verify fully these identified constraints of the provided attribute.
- Note that all values in the description are examples.
- The generated Python code does not include any example of usages.
- The generated script should include segments of code to assert the satisfaction of constraints using a try-catch block.
- You will generate a Python script using the response body variable named 'latest_response' (already defined as a JSON object) to verify the given constraint. 
- Format your answer as shown in the backtick block below.
```python
def verify_latest_response(latest_response):
    // deploy verification flow...
    // return 1 if the constraint is satisfied, -1 otherwise, and 0 if the response lacks sufficient information to verify the constraint (e.g., the attribute does not exist).
```
- No explanation is needed.
"""

CONST_INSIDE_RESPONSEBODY_SCRIPT_CONFIRM_PROMPT = """Given a description implying constraints, rules, or limitations of an attribute in a REST API's response, your responsibility is to confirm whether the provided Python script can verify these constraints through the API response. 
This is the attribute's description:
- "{attribute}": "{description}"

This is the API response's schema:
{response_schema_specification}

This is the generated Python script to verify the attribute "{attribute}" in the API response:
```python
{generated_verification_script}
```

Task 1: Confirm whether the provided Python script can verify the constraints of the attribute "{attribute}" in the API response.
If the script is correct, please type "yes". Incorrect, please type "no".


Task 2: If the script is incorrect, please provide a revised Python script to verify the constraints of the attribute "{attribute}" in the API response.
In your code, no need to fix the latest_response variable, just focus on the verification flow.
Do not repeat the old script.
Format your answer as shown in the backtick block below.
```python
// import section

def verify_latest_response(latest_response):
    // deploy verification flow...
    // return 1 if the constraint is satisfied, -1 otherwise, and 0 if the response lacks sufficient information to verify the constraint (e.g., the attribute does not exist).
```
"""

CONST_RESPONSEBODY_PARAM_SCRIPT_GEN_PROMPT = """Given a description implying constraints, rules, or limitations of an input parameter in a REST API, your responsibility is to generate a corresponding Python script to check whether these constraints are satisfied through the REST API's response.

Below is the input parameter's description:
- "{parameter}": "{parameter_description}"


Below is the API response's schema:
{response_schema_specification}

Below is the corresponding attribute of the provided input parameter in the API response:
{attribute_information}

Now, based on the provided request information, input parameter, and the corresponding attribute in the API response,
help generate a Python script to verify the '{attribute}' attribute in the API response against the constraints of the input parameter '{parameter}'. 
Follow the rules below:

Rules:
- The input parameter can be null or not exist in the request_info dictionary.
- The attribute in the latest_response may not exist or be null.
- Ensure that the generated Python code can verify fully these identified constraints of the provided attribute {parameter}.
- Note that all values in the description are examples.
- The generated Python code does not include any example of usages.
- The generated script should include segments of code to assert the satisfaction of constraints using a try-catch block.
- 'request_info' is a dictionary containing the information of the request to the API. for example {{"created[gt]": "1715605373"}}
- You will generate a Python script using the response body variable named 'latest_response' (already defined as a JSON object) to verify the given constraint. The script should be formatted within triple backticks as shown below: 
```python
def verify_latest_response(latest_response, request_info):
    // deploy verification flow...
    // return 1 if the constraint is satisfied, -1 otherwise, and 0 if the response lacks sufficient information to verify the constraint (e.g., the attribute does not exist).
```
- No explanation is needed."""

CONST_RESPONSEBODY_PARAM_SCRIPT_CONFIRM_PROMPT = """Given a description implying constraints, rules, or limitations of an input parameter in a REST API, your responsibility is to confirm whether the provided Python script can verify these constraints through the REST API's response.

Below is the input parameter's description:
- "{parameter}": "{parameter_description}"

Below is the API response's schema:
{response_schema_specification}

Below is the corresponding attribute of the provided input parameter in the API response:
{attribute_information}

This is the generated Python script to verify the '{attribute}' attribute in the API response against the constraints of the input parameter '{parameter}':

```python
{generated_verification_script}
```

Task 1: Confirm whether the provided Python script can verify the constraints of the attribute "{attribute}" in the API response.
If the script is correct, please type "yes". Incorrect, please type "no".

Task 2: If the script is incorrect, please provide a revised Python script to verify the constraints of the attribute "{attribute}" in the API response.
In your code, no need to fix the latest_response variable, just focus on the verification flow.
Do not repeat the old script.
Check those rules below:
- Ensure that the generated Python code can verify fully these identified constraints of the provided attribute.
- Note that all values in the description are examples.
- The generated Python code does not include any example of usages.
- The generated script should include segments of code to assert the satisfaction of constraints using a try-catch block.
- 'request_info' is a dictionary containing the information of the request to the API. for example {{"created[gt]": "1715605373"}}
- Remember to cast the request_info values to the appropriate data type before comparing them with the response attribute.
- You will generate a Python script using the response body variable named 'latest_response' (already defined as a JSON object) to verify the given constraint. The script should be formatted within triple backticks as shown below: 

Format your answer as shown in the backtick block below.
```python
// import section

def verify_latest_response(latest_response, request_info):
    // deploy verification flow...
    // return 1 if the constraint is satisfied, -1 otherwise, and 0 if the response lacks sufficient information to verify the constraint (e.g., the attribute does not exist).

```
"""
