asSignedInt = lambda s: -int(0x7fffffff&int(s)) if bool(0x80000000&int(s)) else int(0x7fffffff&int(s)) # TODO: swig'ged HIPS I/O unsigned int -> PyInt_AsLong vice PyLong_AsInt; OverflowError: long int too large to convert to int
ZERO_STATUS = 0x00000000

def SeparatePathFromPVDL(pathToPVDL,normalizeStrs=False):
    # normalize --> '/' delimiter and all lowercase letters
    if pathToPVDL.find('\\')!=-1:   # get path delimiter
        dsep='\\'
        pathToPVDL=pathToPVDL.replace('\\','/') #in the off chance there are mixed delimiters - standardize on '/' for the split
    else:
        dsep='/'
    pathToPVDLlist=pathToPVDL.split('/')
    if len(pathToPVDLlist) > 4:    # check for at least a <prefix>/p/v/d/l
        if normalizeStrs:   # [pathTo,p,v,d,l] (pathTo w/fwd-slashes & all lower case)
            pathToAndPVDL=map(lambda dirStr: dirStr.lower(), pathToPVDLlist[-4:])
            pathToAndPVDL.insert(0,'/'.join(pathToPVDLlist[:-4]).lower())
        else:
            pathToAndPVDL=pathToPVDLlist[-4:]   # [pathTo,p,v,d,l] (pathTo w/no change in slash type & mixed case)
            pathToAndPVDL.insert(0,dsep.join(pathToPVDLlist[:-4]))
    else:   # no container directory for p/v/d/l directory; invalid HDCS_DATA_PATH
        pathToAndPVDL=None
    return pathToAndPVDL
