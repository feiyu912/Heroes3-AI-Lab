"""Import the pybind class only, never instantiate/start VCMI."""
import json
from pathlib import Path
from vcmi_gym.connectors.rel import connector_v15

methods=[n for n in dir(connector_v15.ThreadConnector) if not n.startswith('_')]
result=dict(inspected_without_game=True,public_bound_methods=methods,
            clone_exposed='clone' in methods,snapshot_exposed='snapshot' in methods,
            save_exposed='save' in methods,load_exposed='load' in methods)
Path(__file__).with_name('COMPILED_SEARCH_BINDING.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
