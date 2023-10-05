import yaml

class Arguments(object):
    def __init__(self):
        pass

    def update(self, dct :dict):
        for atr in list(dct.keys()):
            self[atr] = dct[atr]

    def __getitem__(self, item):
        return self.__getattribute__(item)

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __eq__(self, other):
        if isinstance(other, Arguments):
            eq = dir(self) == dir(other)
            for atr in dir(self):
                if '__' in atr:
                    continue
                if self[atr] != other[atr]:
                    eq = False

            return eq




# configs = Arguments()
#
# with open('./configs.yaml', 'w') as f:
#     yaml.dump(configs, f, sort_keys=False)