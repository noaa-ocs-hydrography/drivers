class hyd93:
    VALUE_CODES = {0: "Known depth (or elevation)",
                   1: "Submerged (below water level)",
                   2: "Awash (about water level)",
                   3: "Visible (above water level)"}
    def __init__(self, line):
        self.identifier = line[:8].strip()
        self.latitude = int(line[8:17]) / 1000000.0
        self.longitude = int(line[17:27]) / 1000000.0
        self.depth = int(line[27:33]) / 10.0
        self.value_code = int(line[33])
        self.carto_code = int(line[34:37])

    @property
    def value_code_str(self):
        return self.VALUE_CODES[self.value_code]


def test_hyd93():
    line = "H10738   58201421-134257651   1490711"
    v = hyd93(line)
    assert v.latitude == 58.201421
    assert v.longitude == -134.257651
    assert v.depth == 14.9
    assert v.value_code == 0
    assert v.carto_code == 711
    assert v.identifier == 'H10738'
    assert v.value_code_str == 'Known depth (or elevation)'


if __name__ == '__main__':
    test_hyd93()
