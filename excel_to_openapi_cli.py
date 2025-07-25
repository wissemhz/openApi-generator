
import pandas as pd
import yaml
import argparse

def convert_type(t):
    mapping = {
        "string": "string",
        "integer": "integer",
        "int": "integer",
        "boolean": "boolean",
        "bool": "boolean",
        "decimal": "number",
        "float": "number",
        "double": "number",
        "object": "object",
        "array": "array"
    }
    return mapping.get(t.lower(), "string")

def try_cast_example(val, typ):
    try:
        if typ == "integer":
            return int(val)
        if typ == "number":
            return float(val)
        if typ == "boolean":
            return str(val).lower() == "true"
        return str(val)
    except:
        return str(val)

def build_schema_from_sheet(df):
    properties = {}
    required = []
    example_object = {}

    for _, row in df.iterrows():
        name = str(row["Field name"]).strip()
        description = str(row.get("Description", "")).strip()
        typ = str(row["Type"]).strip()
        card = str(row["Cardinality"]).strip()
        example = row.get("Example", "")
        example_response = row.get("Example Response", "")

        field_schema = {
            "type": convert_type(typ),
            "description": description
        }

        if pd.notnull(example) and str(example).strip() != "":
            field_schema["example"] = try_cast_example(example, field_schema["type"])

        if pd.notnull(example_response) and str(example_response).strip() != "":
            example_object[name] = try_cast_example(example_response, field_schema["type"])

        properties[name] = field_schema

        if card == "1":
            required.append(name)

    schema = {
        "type": "object",
        "properties": properties
    }

    if required:
        schema["required"] = required

    if example_object:
        schema["example"] = example_object

    return schema

def generate_openapi_from_excel(excel_path: str, output_yaml_path: str):
    xl = pd.ExcelFile(excel_path)
    endpoints_df = xl.parse("endpoints")
    schemas = {}

    for _, row in endpoints_df.iterrows():
        request_dto = str(row["Request DTO"]).strip()
        response_dto = str(row["Response DTO"]).strip()

        if request_dto and request_dto in xl.sheet_names:
            schemas[request_dto] = build_schema_from_sheet(xl.parse(request_dto))
        if response_dto and response_dto in xl.sheet_names:
            schemas[response_dto] = build_schema_from_sheet(xl.parse(response_dto))

    if "ErrorResponse" in xl.sheet_names:
        schemas["ErrorDto"] = build_schema_from_sheet(xl.parse("ErrorResponse"))

    paths = {}

    for _, row in endpoints_df.iterrows():
        endpoint_path = row["Endpoint"]
        http_method = str(row["HTTP Method"]).lower()
        request_dto = str(row["Request DTO"]).strip()
        response_dto = str(row["Response DTO"]).strip()

        responses = {
            "200": {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": f"#/components/schemas/{response_dto}"
                        }
                    }
                }
            },
            "400": {
                "description": "Client Error",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/ErrorDto"
                        }
                    }
                }
            },
            "500": {
                "description": "Server Error",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/ErrorDto"
                        }
                    }
                }
            }
        }

        paths[endpoint_path] = {
            http_method: {
                "summary": f"{http_method.upper()} {endpoint_path}",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{request_dto}"
                            }
                        }
                    }
                },
                "responses": responses
            }
        }

    openapi = {
        "openapi": "3.0.0",
        "info": {
            "title": "Generated API",
            "version": "1.0.0"
        },
        "paths": paths,
        "components": {
            "schemas": schemas
        }
    }

    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi, f, sort_keys=False, allow_unicode=True)

    print(f"✅ OpenAPI YAML generated at: {output_yaml_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Excel OpenAPI template to YAML")
    parser.add_argument("input", help="Path to the Excel spec file (e.g. openapi_spec_template.xlsx)")
    parser.add_argument("output", help="Path to the output YAML file (e.g. openapi.yaml)")
    args = parser.parse_args()

    generate_openapi_from_excel(args.input, args.output)
