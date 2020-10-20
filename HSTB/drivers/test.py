if 0:
    import HSTB.drivers.hipsio
    HSTB.drivers.hipsio.test()
if 0:
    import HSTB.drivers.generictext
    dpath = r"E:\Data\6barry.txt"
    tpath = r"C:\PydroTrunk\Python27_x64\Lib\site-packages\HSTP\Pydro\test.afp"
    r = HSTB.drivers.generictext.GenericTextReader();r.OpenTemplate(tpath)
    print r.ConvertTXT(dpath, dpath, False, False, None)