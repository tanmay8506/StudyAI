async def run(upc: str, paper: dict, cost) -> tuple:
    syllabus_json = {
        "units": [
            {
                "unit_number": 1,
                "unit_name": "Introduction",
                "topics": [
                    "Basic Concepts"
                ]
            }
        ]
    }
    return syllabus_json, []
