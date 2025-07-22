import json
try:
    import yaml
except ImportError:
    yaml = None

def convert_metadata_format(metadata, fmt):
    if fmt == 'json':
        return json.dumps(metadata, indent=2)
    elif fmt == 'yaml' and yaml:
        return yaml.dump(metadata, sort_keys=False)
    elif fmt == 'txt':
        return str(metadata)
    else:
        return json.dumps(metadata, indent=2) 