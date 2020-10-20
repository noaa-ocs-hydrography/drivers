import pytest
# from pytest import approx  #  approx wasn't working on numpy arrays, use the builtin numpy testing functions
from HSTPBin import PyPeekXTF
from HSTB.drivers import HDCSio
from HSTB.drivers import hipsio
import numpy
import matplotlib.pyplot as plt
import cv2

# import matplotlib
# matplotlib.use('tkagg', warn=False)
# print(matplotlib.get_backend())

#sss_path = r"N:\CSDL\HSTP\Test Data\MISC\Testing_Evaluation\Side_Scan_Data\H12866_SSS\TJ_3101_Klein5KLT_Hull_100_2016\2016-099\105_160408124500"
sss_path = r"C:\Caris\side_scan\H12905\20160826122637"
#numpy.set_printoptions(formatter={'float': '{: 0.7f}'.format})

#h = hipsio.HDCSAttitude('SSSSideScan')
#h = hipsio.HDCSAttitude('SSSCableOut')
#h = hipsio.HDCSAttitude('SideScan')

def test():
    print(sss_path)
    h = hipsio.HDCSSideScan('SSSProc')
    h.ReadContacts(sss_path)
    img, t, res = h.ReadProfiles(sss_path)
    print(img.shape)
    print(img)
    #gray_img = cv2.imread(r'R:\Projects\DeepLearning\ppt\online_wreck_1.png', cv2.IMREAD_GRAYSCALE)
    #cv2.imshow('SideScan',gray_img)
    cv2.imshow('SideScan', img[:500, :500])
    #cv2.imshow('SideScan', img)
    #plt.subplot(111)
    #plt.imshow(img)
    #plt.title('Original Image'), plt.xticks([]), plt.yticks([])
    #plt.show()
    
    #o = h.ReadTimeSeries(sss_path, bVerbose=True)
    #numpy.set_printoptions(precision=3, suppress=True, threshold=20, formatter={'float': lambda x: '%.3f' % x})
    #print o[0]
    #print o[1]
    
    #h = HDCSio.HDCSAttitude('Gyro')
    # h = HDCSio.HDCSNav('SSSNavigation')
    # 
    # o = h.ReadTimeSeries(sss_path, bVerbose=True)
    # numpy.set_printoptions(precision=3, suppress=True, threshold=20, formatter={'float': lambda x: '%.3f' % x})
    # print o[0]
    # print o[1]
    cv2.waitKey(0)
#     while True:
#         k = cv2.waitKey(0) & 0xFF     
#         if k == 27:
#             break # ESC key to exit 
#     cv2.destroyAllWindows()

#         d = contacts[0]['date']
#         import datetime
#         t = datetime.datetime.strptime(d, '%Y-%j').strftime('%Y%m%d')
#         print(p, t)

test()
print('Done')
