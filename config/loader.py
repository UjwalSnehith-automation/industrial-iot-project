from pathlib import Path
import yaml

CONFIG_FILe = Path(__file__).parent / "plants.yaml"

def load_config(path=CONFIG_FILe):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def all_paths(cfg):
    paths=[]
    for plant in cfg["plants"]:
        for area in plant["areas"]:
            for line in area["lines"]:
                for cell in line["cells"]:
                    for metric in cfg["metrics"]:
                        paths.append( [cfg["enterprise"], plant["id"], area["id"], line["id"], cell, metric])
    return paths

if __name__ == "__main__":
    cfg= load_config()
    paths = all_paths(cfg)
    for p in paths:
        print("/".join(p))
    print(len(paths), "paths")