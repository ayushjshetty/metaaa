import os
import zipfile
from parsers.cobol import parse_cobol, ir_to_paragraph_json as cobol_ir_to_paragraph_json
from parsers.fortan import parse_fortran, ir_to_paragraph_json as fortran_ir_to_paragraph_json
# from parsers.pascal import parse_pascal
# from parsers.fortran import parse_fortran
# from parsers.assembly import parse_assembly
# from parsers.ada import parse_ada
# from parsers.pli import parse_pli
# from parsers.rpg import parse_rpg
# from parsers.basic import parse_basic
# from parsers.jcl import parse_jcl

LANGUAGE_EXTENSIONS = {
    'cobol': ['cob', 'cbl', 'cpy'],
    'fortran': ['for', 'f', 'f77', 'f90', 'f95'],
    'pascal': ['pas', 'p'],
    'assembly': ['asm', 's', 'a'],
    'ada': ['ada', 'adb', 'ads'],
    'pli': ['pli', 'pl1', 'pl/i'],
    'rpg': ['rpg', 'rpgle'],
    'basic': ['bas', 'basic'],
    'jcl': ['jcl'],
}

def get_language_from_extension(ext):
    for lang, exts in LANGUAGE_EXTENSIONS.items():
        if ext in exts:
            return lang
    return ext  # fallback

def process_uploaded_files(files, language):
    all_metadata = []
    for file in files:
        filename = file.filename
        ext = filename.rsplit('.', 1)[-1].lower()
        lang = language or get_language_from_extension(ext)
        if ext == 'zip':
            import zipfile
            with zipfile.ZipFile(file) as z:
                for name in z.namelist():
                    file_ext = name.rsplit('.', 1)[-1].lower()
                    file_lang = language or get_language_from_extension(file_ext)
                    if file_ext in sum(LANGUAGE_EXTENSIONS.values(), []):
                        with z.open(name) as f:
                            code = f.read().decode('utf-8', errors='ignore')
                            meta = parse_by_language(code, file_lang)
                            all_metadata.append({'file': name, 'metadata': meta})
        else:
            code = file.read().decode('utf-8', errors='ignore')
            meta = parse_by_language(code, lang)
            all_metadata.append({'file': filename, 'metadata': meta})
    return all_metadata

def process_pasted_code(code, language):
    meta = parse_by_language(code, language)
    return [{'file': 'pasted_code', 'metadata': meta}]

def parse_by_language(code, language):
    lang = (language or '').lower()
    if lang in ['cobol', 'cob', 'cbl', 'cpy']:
        return parse_cobol(code)
    elif lang in ['fortran', 'for', 'f', 'f77', 'f90', 'f95']:
        return parse_fortran(code)
    # elif lang in ['pascal', 'pas', 'p']:
    #     return parse_pascal(code)
    # elif lang in ['assembly', 'asm', 's', 'a']:
    #     return parse_assembly(code)
    # elif lang in ['ada', 'adb', 'ads']:
    #     return parse_ada(code)
    # elif lang in ['pli', 'pl1', 'pl/i']:
    #     return parse_pli(code)
    # elif lang in ['rpg', 'rpgle']:
    #     return parse_rpg(code)
    # elif lang in ['basic', 'bas', 'basic']:
    #     return parse_basic(code)
    # elif lang in ['jcl']:
    #     return parse_jcl(code)
    else:
        return {'error': f'No parser for language: {language}'}

def get_paragraph_json(metadata, language):
    lang = (language or '').lower()
    if lang in ['cobol', 'cob', 'cbl', 'cpy'] and 'ir' in metadata:
        return cobol_ir_to_paragraph_json(metadata['ir'])
    elif lang in ['fortran', 'for', 'f', 'f77', 'f90', 'f95'] and 'ir' in metadata:
        return fortran_ir_to_paragraph_json(metadata['ir'])
    else:
        return [] 