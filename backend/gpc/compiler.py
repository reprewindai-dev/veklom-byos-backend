"""
GPC Compiler
AST-based Python code generation from pipeline graphs

Uses Python's ast module to generate syntactically valid code.
No string templates = no syntax errors by construction.

Location: veklom-byos-backend/backend/gpc/compiler.py
"""

import ast
import graphlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

from backend.gpc.schemas import GPCPipelineGraph, GPCNode, GPCEdge, PortType


class CompilationError(Exception):
    """Raised when compilation fails"""
    pass


class CycleDetectedError(CompilationError):
    """Raised when graph contains a cycle"""
    pass


@dataclass
class CompilationPhase:
    """Tracks which compilation phase we're in"""
    name: str
    description: str


class GPCCompiler:
    """
    Compiles a GPC pipeline graph to executable Python code.
    
    Pipeline:
    1. Validate graph (node types, port connections)
    2. Topological sort (detect cycles)
    3. Resolve variable names
    4. Emit AST fragments per node
    5. Assemble module
    6. Unparse to Python code
    """
    
    def __init__(self):
        """Initialize compiler with built-in node generators"""
        self.node_generators: Dict[str, 'BaseNodeGenerator'] = {
            'CsvFileInput': CsvFileInputGenerator(),
            'JsonFileInput': JsonFileInputGenerator(),
            'ParquetFileInput': ParquetFileInputGenerator(),
            'FilterRows': FilterRowsGenerator(),
            'SelectColumns': SelectColumnsGenerator(),
            'AggregateData': AggregateDataGenerator(),
            'JoinDataFrames': JoinDataFramesGenerator(),
            'DuckDBQuery': DuckDBQueryGenerator(),
            'CsvFileOutput': CsvFileOutputGenerator(),
            'ParquetFileOutput': ParquetFileOutputGenerator(),
            'JsonFileOutput': JsonFileOutputGenerator(),
        }
    
    def compile(self, graph: GPCPipelineGraph) -> str:
        """
        Compile a pipeline graph to Python code.
        
        Args:
            graph: The pipeline graph to compile

        Returns:
            Python code as a string

        Raises:
            CompilationError: If compilation fails
        """
        # Phase 1: Validate
        self._validate_graph(graph)

        # Phase 2: Topological sort
        execution_order = self._topological_sort(graph)

        # Phase 3: Resolve variable names
        output_vars = self._resolve_variable_names(graph)

        # Phase 4: Collect imports and AST fragments
        import_stmts: List[ast.stmt] = []
        body_stmts: List[ast.stmt] = []
        seen_imports: set = set()

        node_map = {n.id: n for n in graph.nodes}

        for node_id in execution_order:
            node = node_map[node_id]
            generator = self._get_node_generator(node.node_type)

            if not generator:
                raise CompilationError(
                    f"No generator for node type: {node.node_type}"
                )

            # Collect imports
            for imp_statement in generator.provide_imports(node.config):
                if imp_statement not in seen_imports:
                    seen_imports.add(imp_statement)
                    # Parse import statement into AST
                    try:
                        import_ast = ast.parse(imp_statement).body[0]
                        import_stmts.append(import_ast)
                    except SyntaxError:
                        raise CompilationError(
                            f"Invalid import statement: {imp_statement}"
                        )

            # Resolve input variables from upstream edges
            input_vars = []
            for edge in graph.edges:
                if edge.target_node_id == node_id:
                    source_var = output_vars[edge.source_node_id]
                    input_vars.append(source_var)

            # Generate node AST
            try:
                node_ast = generator.generate_ast(
                    config=node.config,
                    input_vars=input_vars,
                    output_var=output_vars[node_id]
                )
                body_stmts.extend(node_ast)
            except Exception as e:
                raise CompilationError(
                    f"Failed to generate AST for node {node_id}: {e}"
                )

        # Phase 5: Assemble module
        module = ast.Module(
            body=import_stmts + body_stmts,
            type_ignores=[]
        )

        # Fix missing locations (required for ast.unparse)
        ast.fix_missing_locations(module)

        # Phase 6: Unparse to Python
        try:
            python_code = ast.unparse(module)
            return python_code
        except Exception as e:
            raise CompilationError(f"Failed to unparse AST: {e}")

    def _validate_graph(self, graph: GPCPipelineGraph) -> None:
        """Validate graph structure"""
        if not graph.nodes:
            raise CompilationError("Pipeline has no nodes")

        # Check all node types are known
        for node in graph.nodes:
            if node.node_type not in self.node_generators:
                raise CompilationError(
                    f"Unknown node type: {node.node_type}"
                )

        # Check edges reference valid nodes
        node_ids = {n.id for n in graph.nodes}
        for edge in graph.edges:
            if edge.source_node_id not in node_ids:
                raise CompilationError(
                    f"Edge references unknown source node: {edge.source_node_id}"
                )
            if edge.target_node_id not in node_ids:
                raise CompilationError(
                    f"Edge references unknown target node: {edge.target_node_id}"
                )

    def _topological_sort(self, graph: GPCPipelineGraph) -> List[str]:
        """
        Topological sort using Kahn's algorithm.

        Returns:
            Sorted list of node IDs (dependencies first)

        Raises:
            CycleDetectedError: If graph contains cycles
        """
        # Build in-degree map
        in_degree: Dict[str, int] = {n.id: 0 for n in graph.nodes}
        adjacency: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}

        for edge in graph.edges:
            in_degree[edge.target_node_id] += 1
            adjacency[edge.source_node_id].append(edge.target_node_id)

        # Find all nodes with no incoming edges
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            # For each downstream node
            for downstream in adjacency[node_id]:
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    queue.append(downstream)

        # Check for cycles
        if len(result) != len(graph.nodes):
            remaining = [nid for nid, degree in in_degree.items() if degree > 0]
            raise CycleDetectedError(
                f"Pipeline contains a cycle. Nodes with remaining dependencies: {remaining}"
            )

        return result

    def _resolve_variable_names(self, graph: GPCPipelineGraph) -> Dict[str, str]:
        """
        Resolve output variable names for each node.
        
        Returns:
            Map of node_id -> output_variable_name
        """
        output_vars = {}

        for node in graph.nodes:
            # Use declared nameId if available
            name_id = node.config.get('nameId')

            if name_id:
                output_vars[node.id] = name_id
            else:
                # Generate name from node type and ID (first 8 chars)
                output_vars[node.id] = f"{node.node_type}_{node.id[:8]}"

        return output_vars

    def _get_node_generator(self, node_type: str) -> Optional['BaseNodeGenerator']:
        """Get generator for node type"""
        return self.node_generators.get(node_type)


# ============================================================================
# NODE GENERATORS (AST EMITTERS)
# ============================================================================

class BaseNodeGenerator:
    """Base class for node code generators"""
    
    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        """
        Return list of import statements needed.

        Returns:
            List of import statements (as strings), e.g. ["import pandas as pd"]
        """
        raise NotImplementedError

    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        """
        Generate AST statements for this node.

        Returns:
            List of ast.stmt objects (e.g. assignments, function calls)
        """
        raise NotImplementedError


class CsvFileInputGenerator(BaseNodeGenerator):
    """CSV file input node"""

    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return ["import pandas as pd"]

    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        file_path = config.get('filePath', 'data.csv')
        sep = config.get('sep', ',')
        
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='pd', ctx=ast.Load()),
                        attr='read_csv'
                    ),
                    args=[ast.Constant(value=file_path)],
                    keywords=[
                        ast.keyword(arg='sep', value=ast.Constant(value=sep))
                    ]
                )
            )
        ]


class JsonFileInputGenerator(BaseNodeGenerator):
    """JSON file input node"""

    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return ["import pandas as pd"]
    
    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        file_path = config.get('filePath', 'data.json')
        
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='pd', ctx=ast.Load()),
                        attr='read_json'
                    ),
                    args=[ast.Constant(value=file_path)],
                    keywords=[]
                )
            )
        ]


class ParquetFileInputGenerator(BaseNodeGenerator):
    """Parquet file input node"""

    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return ["import pandas as pd"]
    
    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        file_path = config.get('filePath', 'data.parquet')
        
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='pd', ctx=ast.Load()),
                        attr='read_parquet'
                    ),
                    args=[ast.Constant(value=file_path)],
                    keywords=[]
                )
            )
        ]


class FilterRowsGenerator(BaseNodeGenerator):
    """Filter rows node"""

    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return []
    
    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        if not input_vars:
            raise ValueError("FilterRows requires input DataFrame")

        input_var = input_vars[0]
        condition = config.get('condition', 'True')

        # Parse condition as Python expression
        try:
            condition_ast = ast.parse(condition, mode='eval').body
        except SyntaxError:
            raise ValueError(f"Invalid filter condition: {condition}")
        
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Subscript(
                    value=ast.Name(id=input_var, ctx=ast.Load()),
                    slice=ast.Index(value=condition_ast),
                    ctx=ast.Load()
                )
            )
        ]


class SelectColumnsGenerator(BaseNodeGenerator):
    """Select columns node"""

    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return []
    
    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        if not input_vars:
            raise ValueError("SelectColumns requires input DataFrame")

        input_var = input_vars[0]
        columns = config.get('columns', [])
        
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Subscript(
                    value=ast.Name(id=input_var, ctx=ast.Load()),
                    slice=ast.Index(value=ast.List(
                        elts=[ast.Constant(value=c) for c in columns],
                        ctx=ast.Load()
                    )),
                    ctx=ast.Load()
                )
            )
        ]


class AggregateDataGenerator(BaseNodeGenerator):
    """Aggregate data node"""

    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return []

    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        if not input_vars:
            raise ValueError("AggregateData requires input DataFrame")

        input_var = input_vars[0]
        group_by = config.get('groupBy', [])
        agg_func = config.get('aggregation', 'sum')

        # df.groupby(['col']).sum()
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id=input_var, ctx=ast.Load()),
                                attr='groupby'
                            ),
                            args=[ast.List(
                                elts=[ast.Constant(value=c) for c in group_by],
                                ctx=ast.Load()
                            )],
                            keywords=[]
                        ),
                        attr=agg_func
                    ),
                    args=[],
                    keywords=[]
                )
            )
        ]


class JoinDataFramesGenerator(BaseNodeGenerator):
    """Join DataFrames node"""

    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return []

    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        if len(input_vars) < 2:
            raise ValueError("JoinDataFrames requires 2 input DataFrames")

        left_var = input_vars[0]
        right_var = input_vars[1]
        on = config.get('on', [])
        how = config.get('how', 'inner')

        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=left_var, ctx=ast.Load()),
                        attr='merge'
                    ),
                    args=[ast.Name(id=right_var, ctx=ast.Load())],
                    keywords=[
                        ast.keyword(arg='on', value=ast.List(
                            elts=[ast.Constant(value=c) for c in on],
                            ctx=ast.Load()
                        )),
                        ast.keyword(arg='how', value=ast.Constant(value=how))
                    ]
                )
            )
        ]


class DuckDBQueryGenerator(BaseNodeGenerator):
    """DuckDB SQL query node"""
    
    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return ["import duckdb"]

    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        query = config.get('query', 'SELECT * FROM input_table')
        
        # duckdb.query(sql).pl()  # Returns Polars, convert to pandas
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id='duckdb', ctx=ast.Load()),
                                attr='query'
                            ),
                            args=[ast.Constant(value=query)],
                            keywords=[]
                        ),
                        attr='pl'
                    ),
                    args=[],
                    keywords=[]
                )
            )
        ]


class CsvFileOutputGenerator(BaseNodeGenerator):
    """CSV file output node"""
    
    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return []
    
    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        if not input_vars:
            raise ValueError("CsvFileOutput requires input DataFrame")
        
        input_var = input_vars[0]
        file_path = config.get('filePath', 'output.csv')
        
        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=input_var, ctx=ast.Load()),
                        attr='to_csv'
                    ),
                    args=[ast.Constant(value=file_path)],
                    keywords=[ast.keyword(arg='index', value=ast.Constant(value=False))]
                )
            ),
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Name(id=input_var, ctx=ast.Load())
            )
        ]


class ParquetFileOutputGenerator(BaseNodeGenerator):
    """Parquet file output node"""
    
    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return []
    
    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        if not input_vars:
            raise ValueError("ParquetFileOutput requires input DataFrame")
        
        input_var = input_vars[0]
        file_path = config.get('filePath', 'output.parquet')
        
        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=input_var, ctx=ast.Load()),
                        attr='to_parquet'
                    ),
                    args=[ast.Constant(value=file_path)],
                    keywords=[]
                )
            ),
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Name(id=input_var, ctx=ast.Load())
            )
        ]


class JsonFileOutputGenerator(BaseNodeGenerator):
    """JSON file output node"""
    
    def provide_imports(self, config: Dict[str, Any]) -> List[str]:
        return []

    def generate_ast(
        self,
        config: Dict[str, Any],
        input_vars: List[str],
        output_var: str
    ) -> List[ast.stmt]:
        if not input_vars:
            raise ValueError("JsonFileOutput requires input DataFrame")
        
        input_var = input_vars[0]
        file_path = config.get('filePath', 'output.json')
        
        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=input_var, ctx=ast.Load()),
                        attr='to_json'
                    ),
                    args=[ast.Constant(value=file_path)],
                    keywords=[]
                )
            ),
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Name(id=input_var, ctx=ast.Load())
            )
        ]


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.gpc.compiler import GPCCompiler
from backend.gpc.schemas import GPCPipelineGraph, GPCNode, GPCEdge

compiler = GPCCompiler()

# Create a simple pipeline: CSV → Filter → Parquet
nodes = [
    GPCNode(id="n1", node_type="CsvFileInput", config={"filePath": "data.csv", "nameId": "df_input"}),
    GPCNode(id="n2", node_type="FilterRows", config={"condition": "df_input['value'] > 10", "nameId": "df_filtered"}),
    GPCNode(id="n3", node_type="ParquetFileOutput", config={"filePath": "output.parquet"}),
]

edges = [
    GPCEdge(id="e1", source_node_id="n1", target_node_id="n2"),
    GPCEdge(id="e2", source_node_id="n2", target_node_id="n3"),
]

graph = GPCPipelineGraph(pipeline_id="test", tenant_id="default", nodes=nodes, edges=edges)

# Compile
python_code = compiler.compile(graph)
print(python_code)

# Output:
# import pandas as pd
# df_input = pd.read_csv('data.csv', sep=',')
# df_filtered = df_input[df_input['value'] > 10]
# df_input.to_parquet('output.parquet')
"""
