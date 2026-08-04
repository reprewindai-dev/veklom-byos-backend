"""
Python Transform Builder
Generates Python transformation functions for data pipelines

Location: veklom-byos-backend/backend/gpc/builders/python_builder.py
"""

from typing import Dict, Optional, Any
from backend.gpc.poltergeist.watcher import CapabilityRequirement
from backend.gpc.builders.base_builder import BaseCapabilityBuilder


class PythonTransformBuilder(BaseCapabilityBuilder):
    """
    Builds Python transformation functions.

    Generates pure functions that:
    - Accept input DataFrame
    - Apply transformation logic
    - Return output DataFrame
    - Include type hints and docstrings
    """

    async def prepare(self, requirement: CapabilityRequirement) -> None:
        """Validate requirement"""
        if not requirement.operations:
            raise ValueError("Transform requires operations specification")

    async def generate(self, requirement: CapabilityRequirement) -> str:
        """Generate Python transform code"""
        operations = requirement.operations or []

        code = f'''"""
Data Transform Function
Auto-generated transformation for {requirement.node_type}
"""

import pandas as pd
from typing import DataFrame, Dict, Any, Optional, List


async def transform(
    input_data: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Transform input DataFrame.

    Operations:
{chr(10).join(f"    - {op}" for op in operations)}

    Args:
        input_data: Input DataFrame
        config: Configuration parameters

    Returns:
        Transformed DataFrame
    """
    df = input_data.copy()
    config = config or {{}}

    # Apply transformations
'''

        for op in operations:
            if op == "filter":
                code += """
    # Filter rows
    if 'filter_condition' in config:
        df = df.query(config['filter_condition'])
"""
            elif op == "select":
                code += """
    # Select columns
    if 'columns' in config:
        df = df[config['columns']]
"""
            elif op == "rename":
                code += """
    # Rename columns
    if 'column_mapping' in config:
        df = df.rename(columns=config['column_mapping'])
"""
            elif op == "aggregate":
                code += """
    # Aggregate
    if 'group_by' in config and 'aggregation' in config:
        df = df.groupby(config['group_by']).agg(config['aggregation'])
"""
            elif op == "join":
                code += """
    # Join (requires second DataFrame in config)
    if 'join_data' in config and 'join_key' in config:
        df = df.merge(config['join_data'], on=config['join_key'], how='left')
"""
            elif op == "sort":
                code += """
    # Sort
    if 'sort_by' in config:
        df = df.sort_values(by=config['sort_by'])
"""
            elif op == "fillna":
                code += """
    # Fill missing values
    if 'fill_value' in config:
        df = df.fillna(config['fill_value'])
"""

        code += """

    return df


# Usage:
# result = await transform(df, config={"filter_condition": "value > 10"})
"""

        return code

    async def compile(
        self,
        source_code: str,
        requirement: CapabilityRequirement,
    ) -> bytes:
        """Compile to wheel"""
        return source_code.encode()
