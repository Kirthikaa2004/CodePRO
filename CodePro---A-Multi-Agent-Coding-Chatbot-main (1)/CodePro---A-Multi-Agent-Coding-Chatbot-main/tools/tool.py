import ast
import re
from langchain_core.tools import tool

class StructuralReviewer(ast.NodeTransformer):
    def __init__(self, source_code):
        self.issues = []
        self.source_code = source_code
        self.secrets_pattern = re.compile(r'(?i)(api[_-]?key|password|secret|token|credential|creds)')
        
        # Tracking for Unused items
        self.defined_names = {}  # name -> node
        self.used_names = set()
        
        # Tracking for Class structure
        self.has_class = False
        self.top_level_functions = []

    def add_issue(self, node, message):
        self.issues.append(f"[Line {node.lineno}] {message}")

    # --- PASS 1: Analysis (Finding Unused & Structural check) ---
    def analyze(self, tree):
        for node in ast.walk(tree):
            # Track Definitions
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    self.defined_names[alias.asname or alias.name] = node
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                self.defined_names[node.id] = node
            elif isinstance(node, ast.FunctionDef):
                self.defined_names[node.name] = node
                if isinstance(getattr(node, 'parent', None), ast.Module):
                    self.top_level_functions.append(node)
            
            # Track Usage
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                self.used_names.add(node.id)
            elif isinstance(node, ast.ClassDef):
                self.has_class = True

    # --- PASS 2: Transformation (Fixing & Flagging) ---
    def visit_Import(self, node):
        node.names = [n for n in node.names if (n.asname or n.name) in self.used_names]
        return node if node.names else None

    def visit_ImportFrom(self, node):
        node.names = [n for n in node.names if (n.asname or n.name) in self.used_names]
        return node if node.names else None

    def visit_FunctionDef(self, node):
        # 1. Flag Unused Functions
        if node.name not in self.used_names and not node.name.startswith('provide_'):
            self.add_issue(node, f"UNUSED: Function '{node.name}' is never called.")
            return None # Delete from AST
        
        # 2. Fix Mutable Defaults
        for i, default in enumerate(node.args.defaults):
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.add_issue(node, f"BUG: Mutable default in '{node.name}'. Fixed to None.")
                node.args.defaults[i] = ast.Constant(value=None)
        
        return self.generic_visit(node)

    def visit_Call(self, node):
        # Security: eval/exec
        if isinstance(node.func, ast.Name) and node.func.id in ['eval', 'exec']:
            self.add_issue(node, f"CRITICAL: Found '{node.func.id}()'.")
        
        # Practice: print to logging
        if isinstance(node.func, ast.Name) and node.func.id == 'print':
            self.add_issue(node, "PRACTICE: Replacing 'print()' with 'logging.info()'.")
            node.func = ast.Attribute(value=ast.Name(id='logging', ctx=ast.Load()), attr='info', ctx=ast.Load())
        return self.generic_visit(node)

    def visit_Assign(self, node):
        # Security: Secrets and Unused Variables
        for target in node.targets:
            if isinstance(target, ast.Name):
                if self.secrets_pattern.search(target.id) and isinstance(node.value, ast.Constant):
                    self.add_issue(node, f"SECURITY: Hardcoded secret in '{target.id}'.")
                if target.id not in self.used_names:
                    self.add_issue(node, f"UNUSED: Variable '{target.id}' is never used.")
                    return None # Delete assignment
        return self.generic_visit(node)

@tool
def detailed_code_review(code: str) -> str:
    """
    Analyzes Python code for security (RCE, secrets), unused imports/variables/functions, 
    and enforces class-based structure. Returns a report and a fixed version of the code.
    """
    try:
        tree = ast.parse(code)
        # Add parent links for structural analysis
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

        reviewer = StructuralReviewer(code)
        reviewer.analyze(tree)
        
        # Structural Check: Classes
        if not reviewer.has_class:
            # Check if functions aren't just DI providers (starting with 'provide_')
            non_di_funcs = [f for f in reviewer.top_level_functions if not f.name.startswith('provide_')]
            if non_di_funcs:
                reviewer.issues.append("[Structure] Logic found outside of classes. Wrap functions in a class.")

        # Flag unused imports that the transformer will delete
        for name, node in reviewer.defined_names.items():
            if name not in reviewer.used_names and not name.startswith('provide_'):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    reviewer.add_issue(node, f"UNUSED: Import '{name}' is not used.")

        fixed_tree = reviewer.visit(tree)
        ast.fix_missing_locations(fixed_tree)

        report = "--- CODE REVIEW REPORT ---\n"
        report += "\n".join(reviewer.issues) if reviewer.issues else "No major issues found."
        report += f"\n\n--- FIXED CODE ---\n{ast.unparse(fixed_tree)}"
        
        return report
    except Exception as e:
        return f"Error analyzing code: {str(e)}"
