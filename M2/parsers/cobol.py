import re
from collections import defaultdict

def normalize_cobol_code(code):
    """
    Remove comments and blank lines from COBOL code.
    Handles *, *> at any position, and inline comments (if any).
    """
    lines = code.splitlines()
    cleaned = []
    for line in lines:
        lstr = line.strip()
        if lstr.startswith('*') or lstr.startswith('*>'):
            continue
        # Remove inline comments (e.g., after *> or * in the line)
        if '*> ' in line:
            line = line.split('*>', 1)[0]
        cleaned.append(line)
    return '\n'.join(cleaned)

def extract_variables(normalized):
    """
    Extract variables from all data sections (WORKING-STORAGE, LOCAL-STORAGE, FILE SECTION, etc.).
    """
    variables = []
    # Find all DATA DIVISION sections
    data_sections = re.split(r'^(WORKING-STORAGE|LOCAL-STORAGE|FILE SECTION|LINKAGE SECTION) SECTION\.', normalized, flags=re.MULTILINE | re.IGNORECASE)
    for i in range(1, len(data_sections), 2):
        section_name = data_sections[i].strip().upper()
        section_body = data_sections[i+1]
        var_match = re.findall(r'^(\d{2})\s+([\w-]+)(?:\s+PIC\s+([^\.]+))?', section_body, re.MULTILINE)
        for level, var, vtype in var_match:
            variables.append({'level': level, 'name': var, 'type': vtype.strip() if vtype else None, 'section': section_name})
    return variables

def generate_ir_from_cobol(code):
    """
    Generate an intermediate representation (IR) from COBOL code.
    IR includes program_id, sections (with statements), and variables.
    """
    normalized = normalize_cobol_code(code)
    # Program ID
    entry_match = re.findall(r'PROGRAM-ID\.\s*([\w-]+)', normalized, re.IGNORECASE)
    program_id = entry_match[0] if entry_match else None
    # Variables
    variables = extract_variables(normalized)
    # Find PROCEDURE DIVISION start
    proc_div_match = re.search(r'PROCEDURE DIVISION\s*\.', normalized, re.IGNORECASE)
    proc_start = proc_div_match.end() if proc_div_match else 0
    code_after_proc = normalized[proc_start:]
    # Find all paragraphs/sections (labels at column 8 or after, ending with a period)
    section_matches = list(re.finditer(r'^(\s{0,7})([\w-]+)\s*\.\s*$', code_after_proc, re.MULTILINE))
    section_bounds = []
    if section_matches:
        for i, m in enumerate(section_matches):
            start = m.end()
            end = section_matches[i+1].start() if i+1 < len(section_matches) else len(code_after_proc)
            section_bounds.append({'name': m.group(2), 'start': start, 'end': end})
    else:
        # No labeled sections: treat all code after PROCEDURE DIVISION as 'main'
        section_bounds = [{'name': 'main', 'start': 0, 'end': len(code_after_proc)}]
    # Parse statements in each section
    sections = []
    for sec in section_bounds:
        sec_code = code_after_proc[sec['start']:sec['end']]
        statements = []
        # Simple statement extraction (PERFORM, CALL, IF, etc.)
        for line in sec_code.splitlines():
            line = line.strip()
            if not line:
                continue
            # PERFORM
            m = re.match(r'PERFORM\s+([\w-]+)', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'PERFORM', 'target': m.group(1)})
                continue
            # CALL
            m = re.match(r'CALL\s+\'?([\w-]+)\'?', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'CALL', 'target': m.group(1)})
                continue
            # IF
            m = re.match(r'IF\s+(.+)', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'IF', 'condition': m.group(1)})
                continue
            # READ
            m = re.match(r'READ\s+([\w-]+)', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'READ', 'file': m.group(1)})
                continue
            # WRITE
            m = re.match(r'WRITE\s+([\w-]+)', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'WRITE', 'file': m.group(1)})
                continue
            # OPEN
            m = re.match(r'OPEN\s+(INPUT|OUTPUT)?\s*([\w-]+)?', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'OPEN', 'mode': m.group(1), 'file': m.group(2)})
                continue
            # CLOSE
            m = re.match(r'CLOSE\s+([\w-]+)', line, re.IGNORECASE)
            if m:
                statements.append({'type': 'CLOSE', 'file': m.group(1)})
                continue
            # STOP RUN
            if re.match(r'STOP RUN', line, re.IGNORECASE):
                statements.append({'type': 'STOP RUN'})
                continue
            # Other
            statements.append({'type': 'RAW', 'text': line})
        sections.append({'name': sec['name'], 'statements': statements})
    ir = {
        'program_id': program_id,
        'sections': sections,
        'variables': variables
    }
    return ir

def parse_cobol(code):
    """
    Parse COBOL code and extract robust metadata for any code style.
    Now uses IR for metadata extraction and includes the IR in the output.
    """
    ir = generate_ir_from_cobol(code)
    # --- Metadata extraction from IR ---
    metadata = {
        'entry_points': [ir['program_id']] if ir['program_id'] else [],
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
        calls = [stmt['target'] for stmt in section['statements'] if stmt['type'] == 'PERFORM']
        ext_calls = [stmt['target'] for stmt in section['statements'] if stmt['type'] == 'CALL']
        controls = [stmt['type'] for stmt in section['statements'] if stmt['type'] in ['IF', 'PERFORM', 'GO TO', 'EVALUATE', 'WHEN', 'END-IF', 'END-PERFORM', 'STOP RUN', 'READ', 'WRITE', 'OPEN', 'CLOSE']]
        used_vars = set()
        for stmt in section['statements']:
            for var in ir['variables']:
                if var['name'] in str(stmt):
                    used_vars.add(var['name'])
        function_details.append({
            'name': section['name'],
            'calls': list(set(calls)),
            'external_calls': list(set(ext_calls)),
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
            if stmt['type'] in ['IF', 'PERFORM', 'GO TO', 'EVALUATE', 'WHEN', 'END-IF', 'END-PERFORM', 'STOP RUN']:
                all_controls.append(stmt['type'])
            if stmt['type'] in ['OPEN', 'CLOSE', 'READ', 'WRITE', 'CALL']:
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
        calls = [stmt['target'] for stmt in section['statements'] if stmt['type'] == 'PERFORM']
        ext_calls = [stmt['target'] for stmt in section['statements'] if stmt['type'] == 'CALL']
        paragraphs.append({
            "paragraph": section['name'],
            "statements": section['statements'],
            "variables_used": list(used_vars),
            "calls": calls,
            "external_calls": ext_calls
        })
    return paragraphs 