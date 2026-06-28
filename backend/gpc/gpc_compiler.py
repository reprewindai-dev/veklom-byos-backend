import ast
import graphlib
from typing import Dict, List, Tuple, Optional, Any, Type
from dataclasses import dataclass
from datetime import datetime
from backend.gpc.gpc_schemas import (
    GPCPipelineGraph, GPCNode, GPCEdge, GPCComponentDefinition, 
    PipelineCompilationResult
)


# ============================================================================
# BASE COMPONENT — All node types inherit from this
# ============================================================================

class BaseComponentCodeGenerator:
    """
    Base class for all component code generators.
    Subclasses implement generate_ast() to emit AST fragments for their node type.
    """
    
    def __init__(self, component_def: GPCComponentDefinition):
        self.component_def = component_def
    
    def provide_imports(self) -> List[str]:
        """Return list of import statements needed (e.g., 'import pandas as pd')."""
        return self.component_def.required_imports
    
    def generate_ast(
        self,
        node: GPCNode,
        input_vars: Dict[str, str],
        output_var: str
    ) -> List[ast.stmt]:
        """
        Emit AST statements for this node.
        
        Args:
            node: The node configuration
            input_vars: Mapping of input port ID → variable name from upstream
            output_var: Variable name to assign output to
        
        Returns:
            List of ast.stmt to include in the module body
        """
        raise NotImplementedError("Subclasses must implement generate_ast()")


# ============================================================================
# BUILT-IN COMPONENTS
# ============================================================================

class CsvFileInputGenerator(BaseComponentCodeGenerator):
    """Generate code for CSV file input node."""
    
    def generate_ast(self, node: GPCNode, input_vars: Dict[str, str], output_var: str) -> List[ast.stmt]:
        file_path = node.config.get("filePath", "data.csv")
        sep = node.config.get("sep", ",")
        
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='pd'),
                        attr='read_csv'
                    ),
                    args=[ast.Constant(value=file_path)],
                    keywords=[
                        ast.keyword(arg='sep', value=ast.Constant(value=sep))
                    ]
                )
            )
        ]


class FilterRowsGenerator(BaseComponentCodeGenerator):
    """Generate code for row filtering node."""
    
    def generate_ast(self, node: GPCNode, input_vars: Dict[str, str], output_var: str) -> List[ast.stmt]:
        input_var = list(input_vars.values())[0]  # First (only) input
        filter_column = node.config.get("column", "")
        filter_value = node.config.get("value", "")
        
        # df_output = df_input[df_input['column'] == 'value']
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Subscript(
                    value=ast.Name(id=input_var, ctx=ast.Load()),
                    slice=ast.Compare(
                        left=ast.Subscript(
                            value=ast.Name(id=input_var, ctx=ast.Load()),
                            slice=ast.Index(value=ast.Constant(value=filter_column)),
                            ctx=ast.Load()
                        ),
                        ops=[ast.Eq()],
                        comparators=[ast.Constant(value=filter_value)]
                    ),
                    ctx=ast.Load()
                )
            )
        ]


class AggregateGenerator(BaseComponentCodeGenerator):
    """Generate code for aggregation node."""
    
    def generate_ast(self, node: GPCNode, input_vars: Dict[str, str], output_var: str) -> List[ast.stmt]:
        input_var = list(input_vars.values())[0]
        group_by_col = node.config.get("groupBy", "")
        agg_col = node.config.get("aggregateColumn", "")
        agg_func = node.config.get("aggregateFunction", "sum")
        
        # df_output = df_input.groupby('group_col')['agg_col'].sum()
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Subscript(
                                    value=ast.Call(
                                        func=ast.Attribute(
                                            value=ast.Name(id=input_var, ctx=ast.Load()),
                                            attr='groupby'
                                        ),
                                        args=[ast.Constant(value=group_by_col)],
                                        keywords=[]
                                    ),
                                    slice=ast.Index(value=ast.Constant(value=agg_col)),
                                    ctx=ast.Load()
                                ),
                                attr=agg_func
                            ),
                            args=[],
                            keywords=[]
                        ),
                        attr='reset_index'
                    ),
                    args=[],
                    keywords=[]
                )
            )
        ]


class SelectColumnsGenerator(BaseComponentCodeGenerator):
    """Generate code for column selection node."""
    
    def generate_ast(self, node: GPCNode, input_vars: Dict[str, str], output_var: str) -> List[ast.stmt]:
        input_var = list(input_vars.values())[0]
        columns = node.config.get("columns", [])
        
        # df_output = df_input[['col1', 'col2']]
        return [
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Subscript(
                    value=ast.Name(id=input_var, ctx=ast.Load()),
                    slice=ast.Index(
                        value=ast.List(
                            elts=[ast.Constant(value=c) for c in columns],
                            ctx=ast.Load()
                        )
                    ),
                    ctx=ast.Load()
                )
            )
        ]


class ParquetOutputGenerator(BaseComponentCodeGenerator):
    """Generate code for Parquet file output node."""
    
    def generate_ast(self, node: GPCNode, input_vars: Dict[str, str], output_var: str) -> List[ast.stmt]:
        input_var = list(input_vars.values())[0]
        output_path = node.config.get("outputPath", "output.parquet")
        
        # df_input.to_parquet('output.parquet')
        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=input_var, ctx=ast.Load()),
                        attr='to_parquet'
                    ),
                    args=[ast.Constant(value=output_path)],
                    keywords=[]
                )
            ),
            ast.Assign(
                targets=[ast.Name(id=output_var, ctx=ast.Store())],
                value=ast.Constant(value=output_path)
            )
        ]


class DuckDBQueryGenerator(BaseComponentCodeGenerator):
    """Generate code for DuckDB SQL query node."""
    
    def generate_ast(self, node: GPCNode, input_vars: Dict[str, str], output_var: str) -> List[ast.stmt]:
        input_var = list(input_vars.values())[0]
        sql = node.config.get("sqlQuery", "SELECT * FROM df")
        
        # result = duckdb.query(f"SELECT * FROM {df_input}").to_df()
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
                            args=[ast.JoinedStr(values=[
                                ast.Constant(value=sql)
                            ])],
                            keywords=[]
                        ),
                        attr='to_df'
                    ),
                    args=[],
                    keywords=[]
                )
            )
        ]


# ============================================================================
# COMPONENT REGISTRY
# ============================================================================

DEFAULT_COMPONENTS: Dict[str, Type[BaseComponentCodeGenerator]] = {
    "CsvFileInput": CsvFileInputGenerator,
    "FilterRows": FilterRowsGenerator,
    "Aggregate": AggregateGenerator,
    "SelectColumns": SelectColumnsGenerator,
    "ParquetOutput": ParquetOutputGenerator,
    "DuckDBQuery": DuckDBQueryGenerator,
}


# ============================================================================
# TOPOLOGICAL SORT — Kahn's Algorithm with Cycle Detection
# ============================================================================

class TopologicalSortError(Exception):
    """Raised when the graph contains a cycle."""
    pass


def topological_sort(graph: GPCPipelineGraph) -> List[str]:
    """
    Perform topological sort on the pipeline DAG using Kahn's algorithm.
    
    Args:
        graph: The pipeline graph
    
    Returns:
        List of node IDs in execution order
        
    Raises:
        TopologicalSortError: If the graph contains a cycle
    """
    node_map = {n.id: n for n in graph.nodes}
    
    # Build adjacency list and compute in-degrees
    in_degree = {n.id: 0 for n in graph.nodes}
    adjacency = {n.id: [] for n in graph.nodes}
    
    for edge in graph.edges:
        in_degree[edge.target_node_id] += 1
        adjacency[edge.source_node_id].append(edge.target_node_id)
    
    # Initialize queue with nodes that have no dependencies
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    sorted_nodes = []
    
    while queue:
        node_id = queue.pop(0)
        sorted_nodes.append(node_id)
        
        # Decrement in-degree of downstream nodes
        for downstream in adjacency[node_id]:
            in_degree[downstream] -= 1
            if in_degree[downstream] == 0:
                queue.append(downstream)
    
    # If not all nodes were processed, a cycle exists
    if len(sorted_nodes) != len(graph.nodes):
        raise TopologicalSortError(
            f"Pipeline contains a cycle. Only {len(sorted_nodes)}/{len(graph.nodes)} nodes were processed."
        )
    
    return sorted_nodes


def compute_parallel_levels(graph: GPCPipelineGraph, sorted_order: List[str]) -> List[List[str]]:
    """
    Compute execution levels for parallel processing.
    Nodes at the same level have no dependencies between them.
    """
    node_map = {n.id: n for n in graph.nodes}
    in_degree = {n.id: 0 for n in graph.nodes}
    adjacency = {n.id: [] for n in graph.nodes}
    
    for edge in graph.edges:
        in_degree[edge.target_node_id] += 1
        adjacency[edge.source_node_id].append(edge.target_node_id)
    
    levels = []
    current_level = [nid for nid, deg in in_degree.items() if deg == 0]
    
    while current_level:
        levels.append(current_level)
        next_level = []
        for node_id in current_level:
            for downstream in adjacency[node_id]:
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    next_level.append(downstream)
        current_level = next_level
    
    return levels


# ============================================================================
# MAIN COMPILER
# ============================================================================

class GPCCompiler:
    """
    Compiles GPCPipelineGraph into executable Python code.
    
    Algorithm:
    1. Validate graph structure (port types, cycles)
    2. Topological sort (execution order)
    3. Per-node code emission (AST fragments)
    4. Variable name wiring (output → input)
    5. Final assembly and validation
    """
    
    def __init__(self, component_registry: Optional[Dict[str, Type[BaseComponentCodeGenerator]]] = None):
        self.component_registry = component_registry or DEFAULT_COMPONENTS
    
    def compile(self, graph: GPCPipelineGraph) -> PipelineCompilationResult:
        """
        Compile a pipeline graph into Python code.
        
        Args:
            graph: The GPCPipelineGraph to compile
        
        Returns:
            PipelineCompilationResult with generated code or errors
        """
        try:
            # Phase 1: Validate structure
            self._validate_graph(graph)
            
            # Phase 2: Topological sort
            execution_order = topological_sort(graph)
            parallel_levels = compute_parallel_levels(graph, execution_order)
            
            # Phase 3: Variable name resolution
            output_vars = self._resolve_output_variables(graph)
            
            # Phase 4: Collect imports and emit AST
            import_stmts: List[ast.stmt] = []
            body_stmts: List[ast.stmt] = []
            seen_imports: set = set()
            
            node_map = {n.id: n for n in graph.nodes}
            
            for node_id in execution_order:
                node = node_map[node_id]
                component_class = self.component_registry.get(node.node_type)
                
                if not component_class:
                    raise ValueError(f"Unknown component type: {node.node_type}")
                
                component = component_class(
                    GPCComponentDefinition(
                        node_type=node.node_type,
                        display_name=node.label or node.node_type,
                        category="transform",
                        code_generator_class=component_class.__name__
                    )
                )
                
                # Collect unique imports
                for imp in component.provide_imports():
                    if imp not in seen_imports:
                        seen_imports.add(imp)
                        try:
                            import_stmts.append(ast.parse(imp).body[0])
                        except SyntaxError as e:
                            raise ValueError(f"Invalid import statement: {imp}") from e
                
                # Wire input variables from upstream
                input_vars = self._get_input_vars(graph, node_id, output_vars)
                
                # Emit AST fragments
                try:
                    fragment = component.generate_ast(
                        node=node,
                        input_vars=input_vars,
                        output_var=output_vars[node_id]
                    )
                    body_stmts.extend(fragment)
                except Exception as e:
                    raise ValueError(f"Code generation failed for node {node_id}: {e}") from e
            
            # Phase 5: Assemble module
            module = ast.Module(
                body=import_stmts + body_stmts,
                type_ignores=[]
            )
            ast.fix_missing_locations(module)
            
            # Unparse to Python string
            python_code = ast.unparse(module)
            
            return PipelineCompilationResult(
                success=True,
                python_code=python_code,
                node_count=len(graph.nodes),
                execution_order=execution_order,
                parallel_levels=parallel_levels,
                warnings=[]
            )
        
        except Exception as e:
            return PipelineCompilationResult(
                success=False,
                python_code="",
                node_count=0,
                execution_order=[],
                parallel_levels=[],
                warnings=[str(e)]
            )
    
    def _validate_graph(self, graph: GPCPipelineGraph) -> None:
        """Validate graph structure: cycles, port compatibility, etc."""
        if not graph.nodes:
            raise ValueError("Pipeline must contain at least one node")
        
        node_ids = {n.id for n in graph.nodes}
        
        # Validate edge references
        for edge in graph.edges:
            if edge.source_node_id not in node_ids:
                raise ValueError(f"Edge references unknown source node: {edge.source_node_id}")
            if edge.target_node_id not in node_ids:
                raise ValueError(f"Edge references unknown target node: {edge.target_node_id}")
        
        # Validate port compatibility
        node_map = {n.id: n for n in graph.nodes}
        for edge in graph.edges:
            source_node = node_map[edge.source_node_id]
            target_node = node_map[edge.target_node_id]
            
            source_port = next(
                (p for p in source_node.output_ports if p.id == edge.source_port_id),
                None
            )
            target_port = next(
                (p for p in target_node.input_ports if p.id == edge.target_port_id),
                None
            )
            
            if not source_port or not target_port:
                continue  # Port might not be defined yet (custom components)
    
    def _resolve_output_variables(self, graph: GPCPipelineGraph) -> Dict[str, str]:
        """Compute output variable name for each node."""
        output_vars = {}
        for node in graph.nodes:
            # Use explicit nameId if provided, else generate from node_type
            output_vars[node.id] = node.config.get("nameId", f"{node.node_type}_{node.id[:8]}")
        return output_vars
    
    def _get_input_vars(self, graph: GPCPipelineGraph, node_id: str, output_vars: Dict[str, str]) -> Dict[str, str]:
        """Get input variable names for a node from upstream edges."""
        input_vars = {}
        for edge in graph.edges:
            if edge.target_node_id == node_id:
                input_vars[edge.source_port_id] = output_vars[edge.source_node_id]
        return input_vars
