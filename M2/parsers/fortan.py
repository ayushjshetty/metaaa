import re
from collections import defaultdict

def normalize_fortran_code(code):
    """
    Remove comments and blank lines from Fortran code.
    Fortran comments start with 'C', 'c', '*' in column 1, or '!'.
    """
    lines = code.splitlines()
    cleaned = []
    for line in lines:
        lstr = line.strip()
        if lstr.startswith('C') or lstr.startswith('c') or lstr.startswith('*') or lstr.startswith('!'):
            continue
        # Remove inline comments (after '!')
        if '!' in line:
            line = line.split('!', 1)[0]
        if line.strip():
            cleaned.append(line)
    return '\n'.join(cleaned)

def extract_variables(normalized):
    """
    Extract variable declarations from Fortran code (simple types: INTEGER, REAL, CHARACTER, LOGICAL, DOUBLE PRECISION).
    """
    variables = []
    var_match = re.findall(r'^(INTEGER|REAL|CHARACTER|LOGICAL|DOUBLE PRECISION)\s*(\*\d+)?\s*::?\s*([\w, ]+)', normalized, re.MULTILINE | re.IGNORECASE)
    for vtype, vlen, vnames in var_match:
        for v in vnames.split(','):
            v = v.strip()
            if v:
                variables.append({'type': vtype.upper(), 'name': v, 'len': vlen.strip() if vlen else None})
    return variables

def generate_ir_from_fortran(code):
    """
    Generate an intermediate representation (IR) from Fortran code.
    IR includes program_name, subroutines/functions (with statements), and variables.
    """
    normalized = normalize_fortran_code(code)
    # Program name
    prog_match = re.search(r'PROGRAM\s+([\w_]+)', normalized, re.IGNORECASE)
    program_name = prog_match.group(1) if prog_match else None
    # Variables
    variables = extract_variables(normalized)
    # Find subroutines and functions
    section_matches = list(re.finditer(r'^(SUBROUTINE|FUNCTION)\s+([\w_]+)', normalized, re.MULTILINE | re.IGNORECASE))
    section_bounds = []
    if section_matches:
        for i, m in enumerate(section_matches):
            start = m.start()
            end = section_matches[i+1].start() if i+1 < len(section_matches) else len(normalized)
            section_bounds.append({'type': m.group(1).upper(), 'name': m.group(2), 'start': start, 'end': end})
    else:
        # No subroutines/functions: treat all code as 'main'
        section_bounds = [{'type': 'PROGRAM', 'name': program_name or 'main', 'start': 0, 'end': len(normalized)}]
    # Parse statements in each section
    sections = []
    for sec in section_bounds:
        sec_code = normalized[sec['start']:sec['end']]
        statements = []
        for line in sec_code.splitlines():
            line = line.strip()
            if not line:
                continue
            # CALL
            m = re.match(r'CALL\s+([\w_]+)', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'CALL', 'target': m.group(1)})
                continue
            # IF
            m = re.match(r'IF\s*\((.+)\)\s*THEN', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'IF', 'condition': m.group(1)})
                continue
            # DO loop
            m = re.match(r'DO\s+(\w+)\s*=\s*([^,]+),\s*([^,]+)(?:,\s*([^,]+))?', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'DO', 'var': m.group(1), 'start': m.group(2), 'end': m.group(3), 'step': m.group(4)})
                continue
            # GOTO
            m = re.match(r'GOTO\s+(\d+)', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'GOTO', 'target': m.group(1)})
                continue
            # RETURN
            if re.match(r'RETURN', line, re.IGNORECASE):
                statements.append({'type': 'RETURN'})
                continue
            # END
            if re.match(r'END', line, re.IGNORECASE):
                statements.append({'type': 'END'})
                continue
            # Other
            statements.append({'type': 'RAW', 'text': line})
        sections.append({'type': sec['type'], 'name': sec['name'], 'statements': statements})
    ir = {
        'program_name': program_name,
        'sections': sections,
        'variables': variables
    }
    return ir

def parse_fortran(code):
    """
    Parse Fortran code and extract robust metadata for any code style.
    Uses IR for metadata extraction and includes the IR in the output.
    """
    ir = generate_ir_from_fortran(code)
    metadata = {
        'entry_points': [ir['program_name']] if ir['program_name'] else [],
        'variables': ir['variables'],
        'functions': [],
        'call_graph': {},
        'external_interfaces': [],
        'control_structures': [],
        'ir': ir
    }
    call_graph = defaultdict(list)
    function_details = []
    for section in ir['sections']:
        calls = [stmt['target'] for stmt in section['statements'] if stmt['type'] == 'CALL']
        controls = [stmt['type'] for stmt in section['statements'] if stmt['type'] in ['IF', 'DO', 'GOTO', 'RETURN', 'END']]
        used_vars = set()
        for stmt in section['statements']:
            for var in ir['variables']:
                if var['name'] in str(stmt):
                    used_vars.add(var['name'])
        function_details.append({
            'name': section['name'],
            'calls': list(set(calls)),
            'external_calls': [],
            'control_structures': list(set(controls)),
            'variables_used': list(used_vars),
        })
        call_graph[section['name']].extend(list(set(calls)))
    metadata['functions'] = function_details
    metadata['call_graph'] = dict(call_graph)
    # Top-level control structures and external interfaces
    all_controls = []
    all_ext = []
    for section in ir['sections']:
        for stmt in section['statements']:
            if stmt['type'] in ['IF', 'DO', 'GOTO', 'RETURN', 'END']:
                all_controls.append(stmt['type'])
            if stmt['type'] in ['CALL']:
                all_ext.append(stmt['type'])
    metadata['control_structures'] = list(set(all_controls))
    metadata['external_interfaces'] = list(set(all_ext))
    return metadata

def ir_to_paragraph_json(ir):
    """
    Convert IR to a paragraph-based JSON format for code migration.
    Each paragraph/section is a dict with name, statements, variables_used, calls, and external_calls.
    """
    paragraphs = []
    for section in ir['sections']:
        used_vars = set()
        for stmt in section['statements']:
            for var in ir['variables']:
                if var['name'] in str(stmt):
                    used_vars.add(var['name'])
        calls = [stmt['target'] for stmt in section['statements'] if stmt['type'] == 'CALL']
        ext_calls = []  # For Fortran, external calls are just CALLs
        paragraphs.append({
            "paragraph": section['name'],
            "statements": section['statements'],
            "variables_used": list(used_vars),
            "calls": calls,
            "external_calls": ext_calls
        })
    return paragraphs
