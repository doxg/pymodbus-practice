from configs.config import Arguments
import yaml

config = Arguments()

with open('./configs.yaml', 'w') as f:
    yaml.dump(config, f, sort_keys=False)