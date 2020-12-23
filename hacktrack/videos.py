
import pandas, numpy
import scipy.stats
import cv2
import ipywidgets as widgets
from IPython.display import display
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()


#
# Find camera matrix and distortion from a set of videos containing chessboards
#
def cameramatrixfromchessboards(cap, sframes, squaresX, squaresY, chesssquareLength):
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    imageSize = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    print("nframes", nframes, "w,h =", imageSize)

    chesspatternSize = (squaresX-1, squaresY-1)
    winSize, zeroZone, criteria = (5, 5), (-1, -1), (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)
    chesspatternPoints = numpy.zeros((numpy.prod(chesspatternSize), 3), numpy.float32)
    chesspatternPoints[:,:2] = numpy.indices(chesspatternSize).T.reshape(-1, 2)
    chesspatternPoints *= chesssquareLength

    imagePoints, objectPoints = [ ], [ ]
    for iframe in range(10, nframes, nframes//44):
        cap.set(cv2.CAP_PROP_POS_FRAMES, iframe)
        flag, frame = cap.retrieve()

        found, corners = cv2.findChessboardCorners(frame, chesspatternSize)
        if found:
            frameg = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners = cv2.cornerSubPix(frameg, corners, winSize, zeroZone, criteria)
            imagePoints.append(corners.reshape(-1, 2))
            objectPoints.append(chesspatternPoints)
            #cv2.drawChessboardCorners(frame, chesspatternSize, corners, found) 

    # Long calculation that gets the rvec and tvec of the chessboard in each frame
    print("calculating camera coeffs for %d chessboards" % len(imagePoints))
    retval, cameraMatrix, distCoeffs, rvecs, tvecs = cv2.calibrateCamera(objectPoints, imagePoints, imageSize, None, None)
    return cameraMatrix, distCoeffs
    



# the aruco dictionary we will used
aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
parameters =  cv2.aruco.DetectorParameters_create()

#
# Framed flashing LED interaction selection
#
WframenumberR = widgets.IntRangeSlider(description="frame", value=(50, 100), min=0, max=200, continuous_update=False)
WframenumberR.layout.width = "600px"
Wledxselrange = widgets.IntRangeSlider(value=(100, 200), min=0, max=300, continuous_update=False)
Wledyselrange = widgets.IntRangeSlider(value=(200, 300), min=0, max=300, continuous_update=False)
uiledrg = widgets.HBox([Wledxselrange, Wledyselrange])
ui = widgets.VBox([WframenumberR, uiledrg])

def plotframewindow(cap, framenumberR, ledxselrange, ledyselrange, cameraMatrix, distCoeffs):
    plt.figure(figsize=(17,6))
    framenumber = framenumberR[0]
    cap.set(cv2.CAP_PROP_POS_FRAMES, framenumber)
    flag, frame = cap.retrieve()
    
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    corners, ids, rejectedImgPoints = cv2.aruco.detectMarkers(frame, aruco_dict, parameters=parameters, cameraMatrix=cameraMatrix, distCoeff=distCoeffs)
    frame = cv2.aruco.drawDetectedMarkers(frame, corners, ids)

    plt.imshow(frame)
    plt.gca().add_patch(Rectangle((ledxselrange[0], ledyselrange[0]), ledxselrange[1]-ledxselrange[0], ledyselrange[1]-ledyselrange[0], linewidth=1, edgecolor='b', facecolor='none'))
    print("Meanred", frame[ledyselrange[0]:ledyselrange[1], ledxselrange[0]:ledxselrange[1], 0].mean())

# entry function
def frameselectinteractive(cap, cameraMatrix, distCoeffs):
    frameheight, framewidth = cap.get(cv2.CAP_PROP_FRAME_HEIGHT), cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    framecount = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    
    WframenumberR.min, WframenumberR.max = 1, framecount
    WframenumberR.value = (framecount//2, framecount)
    Wledxselrange.min, Wledxselrange.max = 0, framewidth
    Wledxselrange.value = (framewidth//3, 2*framewidth//3)
    Wledyselrange.min, Wledyselrange.max = 0, frameheight
    Wledyselrange.value = (2*frameheight//3, frameheight)
    
    params = {'framenumberR':WframenumberR, 'ledxselrange':Wledxselrange, 'ledyselrange':Wledyselrange, 
              'cap':widgets.fixed(cap), "cameraMatrix":widgets.fixed(cameraMatrix), "distCoeffs":widgets.fixed(distCoeffs) }
    outputfigure = widgets.interactive_output(plotframewindow, params)
    outputfigure.layout.height = '400px'
    display(ui, outputfigure);

# Function to call when we have selected the region by Wledxselrange, Wledyselrange
def extractledflashframes(cap):
    framenumberR = WframenumberR.value
    print("scanning between frames", framenumberR)
    ledxselrange, ledyselrange = Wledxselrange.value, Wledyselrange.value
    
    vals = [ ]
    cap.set(cv2.CAP_PROP_POS_FRAMES, framenumberR[0]-1)
    while True:
        flag, frame = cap.read()   # advances then retrieves
        if not flag:                      break
        framenum = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        if framenum > framenumberR[1]:   break
        if (framenum%1000) == 0:
            print(framenum)
        x = frame[ledyselrange[0]:ledyselrange[1], ledxselrange[0]:ledxselrange[1]]
        val = { "framenum":framenum, "b":x[:,:,0].mean(), "g":x[:,:,1].mean(), "r":x[:,:,2].mean() }   # BGR
        vals.append(val)
    ledbrights = pandas.DataFrame.from_dict(vals)
    ledbrights.set_index("framenum", inplace=True)
    ledbrights.index.name = None
    return ledbrights
    
    
#cap = cv2.VideoCapture(vidfile)
#frameselectinteractive(cap)
# Then
#ledbrights = extractledflashframes(cap)

# correspondence function between dust/flash info in logfile and flashes in video
def framestotime(videoledonvalues, ledswitchtimes):
    # find ratios of subsequent on moments
    videoledonframes = videoledonvalues&(True^videoledonvalues.shift())
    videoledonframesI = videoledonvalues.index.to_series()[videoledonframes]
    videoledonframedurations = videoledonframesI.diff().iloc[1:]
    vr = (videoledonframedurations/videoledonframedurations.shift(1)).iloc[1:]

    ledontimes = ledswitchtimes.index.to_series()[ledswitchtimes]
    ledondurations = ledontimes.diff().iloc[1:]/pandas.Timedelta(seconds=1)
    lr = (ledondurations/ledondurations.shift(1)).iloc[1:]

    lrV = lr.values
    vrV = vr.values

    # overlap and find differences
    k = [ ] 
    for i in range(-(len(lrV)-1), len(vrV)):
        llrV = lrV[max(-i,0):len(lrV)-max(0,i+len(lrV)-len(vrV))]
        lvrV = vrV[max(0,i):len(lrV)+i-max(0,i+len(lrV)-len(vrV))]
        assert len(llrV) == len(lvrV)
        s = sum(abs(llrV - lvrV))
        if len(llrV) >= 2:
            k.append((s/len(llrV), i, len(llrV)))

    s = min(k)
    i = s[1]

    # interpolate and re-align
    ledalignment = pandas.DataFrame(lr.iloc[max(-i,0):len(lrV)-max(0,i+len(lrV)-len(vrV))], columns=["ledondurationratios"])
    ledalignment["videoledondurationratiosV"] = vrV[max(0,i):len(lrV)+i-max(0,i+len(lrV)-len(vrV))]
    ledalignment["videoledondurationratiosI"] = vr.index[max(0,i):len(lrV)+i-max(0,i+len(lrV)-len(vrV))]

    #ledalignment.videoledondurationratiosI.values
    #plt.plot(ledalignment.videoledondurationratiosI.values)
    k = scipy.stats.linregress(ledalignment.videoledondurationratiosI.values, 
                               (ledalignment.index - ledalignment.index[0])/pandas.Timedelta(seconds=1))
    print("Framerate", 1/k.slope, "rvalue", k.rvalue, "overlap", s[2])
    return videoledonvalues.index.to_series()*pandas.Timedelta(seconds=k.slope) + pandas.Timedelta(seconds=k.intercept) + ledalignment.index[0]



#
# interactive preview of undistorted frames with charboard detection
#
Wframenumber = widgets.IntSlider(description="frame", value=50, min=1, max=100, continuous_update=False)
Wframenumber.layout.width = "600px"
uiframeundistortpreview = widgets.VBox([Wframenumber])

def plotframewindowundistort(cap, framenumber, cameraMatrix, distCoeffs, newcameraMatrix, charboard):
    plt.figure(figsize=(17,6))
    cap.set(cv2.CAP_PROP_POS_FRAMES, framenumber)
    flag, frame = cap.retrieve()
    
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frameUndistorted = cv2.undistort(frame, cameraMatrix, distCoeffs, newCameraMatrix=newcameraMatrix)
    squaresX, squaresY = charboard.getChessboardSize()
    chesssquareLength = charboard.getSquareLength()

    markerCorners, markerIds, rejectedMarkers = cv2.aruco.detectMarkers(frame, aruco_dict, parameters=parameters, cameraMatrix=cameraMatrix, distCoeff=distCoeffs)
    if markerIds is not None:
        markerCorners, markerIds, rejectedMarkers, recoveredIdxs = cv2.aruco.refineDetectedMarkers(frame, charboard, markerCorners, markerIds, rejectedMarkers, cameraMatrix, distCoeffs)
        retval, charucoCorners, charucoIds = cv2.aruco.interpolateCornersCharuco(markerCorners, markerIds, frame, charboard, cameraMatrix=cameraMatrix, distCoeffs=distCoeffs)
        if retval is not None:
            cv2.aruco.drawDetectedCornersCharuco(frame, charucoCorners, charucoIds)
            retval, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(charucoCorners, charucoIds, charboard, cameraMatrix, distCoeffs)
            if retval:
                tvec, rvec = tvec.T[0], rvec.T[0] # 3-vectors
                rotmat = cv2.Rodrigues(rvec)[0].T
                tvec = tvec + rotmat[0]*(squaresX*chesssquareLength/2) + rotmat[1]*(squaresY*chesssquareLength/2)  # displace to centre of board

                cv2.aruco.drawAxis(frame, cameraMatrix, distCoeffs, rvec, tvec, 0.1)
                cv2.aruco.drawAxis(frameUndistorted, newcameraMatrix, None, rvec, tvec, 0.1) 
    plt.subplot(1, 2, 1)
    plt.imshow(frame)
    plt.gca().axes.get_xaxis().set_visible(False)
    plt.gca().axes.get_yaxis().set_visible(False)
    
    plt.subplot(1, 2, 2)
    plt.imshow(frameUndistorted)
    plt.gca().axes.get_xaxis().set_visible(False)
    plt.gca().axes.get_yaxis().set_visible(False)
    
    plt.subplots_adjust(0,0,1,1,0.05,0.05)

# entry function
def frameundistortdetectinteractive(cap, cameraMatrix, distCoeffs, squaresX, squaresY, markersquareratio, chesssquareLength):
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    imageSize = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    Wframenumber.min, Wframenumber.max = 1, nframes
    Wframenumber.value = nframes//2

    charboard = cv2.aruco.CharucoBoard_create(squaresX, squaresY, chesssquareLength, chesssquareLength*markersquareratio, aruco_dict)
    newcameraMatrix, validPixROI = cv2.getOptimalNewCameraMatrix(cameraMatrix, distCoeffs, imageSize, 0)


    params = {'framenumber':Wframenumber, 
              'cap':widgets.fixed(cap), "cameraMatrix":widgets.fixed(cameraMatrix), "distCoeffs":widgets.fixed(distCoeffs), 
              "newcameraMatrix":widgets.fixed(newcameraMatrix), "charboard":widgets.fixed(charboard) }
    outputfigure = widgets.interactive_output(plotframewindowundistort, params)
    outputfigure.layout.height = '400px'
    display(uiframeundistortpreview, outputfigure);


#
# Find the orientation and distance array from each frame of a charboard
#
def findtiltfromvideoframes(cap, cameraMatrix, distCoeffs, squaresX, squaresY, chesssquareLength, markersquareratio):
    charboard = cv2.aruco.CharucoBoard_create(squaresX, squaresY, chesssquareLength, chesssquareLength*markersquareratio, aruco_dict)
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    imageSize = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    print("nframes", nframes, "w,h =", imageSize)

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    vals = [ ]
    for i in range(nframes):
        flag, frame = cap.read()  # advances by 1 (initializes at 0, then reads the frame)
        if not flag:
            break
        framenum = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        if (framenum%500) == 0:
            print(framenum)
        markerCorners, markerIds, rejectedMarkers = cv2.aruco.detectMarkers(frame, aruco_dict, parameters=parameters, cameraMatrix=cameraMatrix, distCoeff=distCoeffs)
        if markerIds is None:   continue
        markerCorners, markerIds, rejectedMarkers, recoveredIdxs = cv2.aruco.refineDetectedMarkers(frame, charboard, markerCorners, markerIds, rejectedMarkers, cameraMatrix, distCoeffs)
        retval, charucoCorners, charucoIds = cv2.aruco.interpolateCornersCharuco(markerCorners, markerIds, frame, charboard, cameraMatrix=cameraMatrix, distCoeffs=distCoeffs)
        if not retval:          continue
        retval, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(charucoCorners, charucoIds, charboard, cameraMatrix, distCoeffs)
        if not retval:          continue
        tvec, rvec = tvec.T[0], rvec.T[0] # 3-vectors

        rotmat = cv2.Rodrigues(rvec)[0].T
        tvec = tvec + rotmat[0]*(squaresX*chesssquareLength/2) + rotmat[1]*(squaresY*chesssquareLength/2)  # displace to centre of board
        zvec = rotmat[2]
        
        val = {"framenum":framenum, "tx":tvec[0], "ty":tvec[1], "tz":tvec[2], 
                                    "rx":rvec[0], "ry":rvec[1], "rz":rvec[2], 
                                    "nx":zvec[0], "ny":zvec[1], "nz":zvec[2]}
        vals.append(val)

    # These orientations are relative to the orientation of the charuco board, which is fixed relative to North
    tiltv = pandas.DataFrame.from_dict(vals)
    tiltv.set_index("framenum", inplace=True)
    tiltv.index.name = None
    return tiltv

