import cv2
import numpy
import time
import logging

logc = logging.getLogger('capture')
logw = logging.getLogger('window')

class CaptureManager( object ):
    

    def __init__( self, capture, previewWindowManager, 
                  shouldMirrorPreview, resolution):

  
        self._capture = capture

        self._previewWindowManager = previewWindowManager
        self._shouldMirrorPreview = shouldMirrorPreview
        
         
        ### RESOLUTION
        self.desiredCols = resolution[0]
        self.desiredRows = resolution[1]

        self._channel = 0
        self._enteredFrame = False
        self._frame = None
        self._imageFilename = None
        self._videoFilename = None
        self._videoEncoding = None
        self._videoWriter = None
        self.gotFrame = True
        self._startTime = None
        self._framesElapsed = long(0)
        self._fpsEstimate = None
        
    def setResolution( self, resolution):
        rows = resolution[1]
        cols = resolution[0]
        try:
            self.setProp( 'height', rows )
            self.setProp( 'width', cols )
        except Exception as e:
            logc.exception(e)

    def getResolution( self ):
        h = self.getProp( 'height')
        w = self.getProp( 'width')
        print w
        print h
        return w, h
   
    def getProp( self, prop ):
        props = {
                 'mode': cv2.CAP_PROP_MODE,
                 'brightness': cv2.CAP_PROP_BRIGHTNESS,
                 'contrast': cv2.CAP_PROP_CONTRAST,
                 'saturation': cv2.CAP_PROP_SATURATION,
                 'hue':cv2.CAP_PROP_HUE,
                 'gain': cv2.CAP_PROP_GAIN,
                 'exposure': cv2.CAP_PROP_EXPOSURE,
                 'height': cv2.CAP_PROP_FRAME_HEIGHT,
                 'width': cv2.CAP_PROP_FRAME_WIDTH
                 }

        newval = self._capture.get(props[prop])
        if newval == 0:
            logc.warn('- get prop %s\tnot available' % prop)
        else:
            logc.warn('- get prop: %s\t%s' % (prop, newval) )
        return newval

    def setProp( self, prop, value):
        props = {
                 'mode': cv2.CAP_PROP_MODE,
                 'brightness': cv2.CAP_PROP_BRIGHTNESS,
                 'contrast': cv2.CAP_PROP_CONTRAST,
                 'saturation': cv2.CAP_PROP_SATURATION,
                 'hue':cv2.CAP_PROP_HUE,
                 'gain': cv2.CAP_PROP_GAIN,
                 'exposure': cv2.CAP_PROP_EXPOSURE,
                 'height': cv2.CAP_PROP_FRAME_HEIGHT,
                 'width': cv2.CAP_PROP_FRAME_WIDTH
                 }
    
        self._capture.set(props[prop], value)
        logc.warn('- set prop: %s\t%s' % ( prop, str(value) ))
        newval = self._capture.get(props[prop])
        if newval == 0:
            logc.warn('- get prop %s\tnot available' % prop)
        else:
            logc.warn('- get prop: %s\t%s' % (prop, newval) )
         
     
    def debugProps( self ):
        for prop, name in [(cv2.CAP_PROP_MODE, "Mode"),
                           (cv2.CAP_PROP_BRIGHTNESS, "Brightness"),
                           (cv2.CAP_PROP_CONTRAST, "Contrast"),
                           (cv2.CAP_PROP_SATURATION, "Saturation"),
                           (cv2.CAP_PROP_HUE, "Hue"),
                           (cv2.CAP_PROP_GAIN, "Gain"),
                           (cv2.CAP_PROP_EXPOSURE, "Exposure")]:
            value = self._capture.get(prop)
            if value == 0:
                logc.warn(" - %s not available" % name)
            else:
                logc.warn(" - %s = %r" % (name, value))

    @property
    def channel( self ):
        return self._channel


    @channel.setter
    def channel( self, value ):
        if self.channel != value:
            self._channel = value
            self._frame = None


    @property
    def frame( self ): 
        if self._enteredFrame and self._frame is None:
            ###_, self._frame = self._capture.retrieve( channel = self.channel )
            self.gotFrame, self._frame = self._capture.retrieve()
           
        return self._frame


    @property
    def isWritingImage( self ):
        return self._imageFilename is not None

    @property
    def isWritingVideo( self ):
        return self._videoFilename is not None



    def enterFrame( self ):
        #Capture the next frame, if any
        #Check that previous frame is exited
        assert not self._enteredFrame, \
            'previous enterFrame() has no matching exitFrame()'
        
        if self._capture is not None:
            self._enteredFrame = self._capture.grab()


    def exitFrame( self ):
        #Draw to window
        #Write to files
        #Release the frame

        #Check whether grabbed frame is retrievable
        # The getter may retrieve and cache the frame

        if self.frame is None: ####IS THIS OK? _FRAME INST
            self._enteredFrame = False
            return

        #Update FPS estimate and related
        if self._framesElapsed == 0:
            self._startTime = time.time()
        else: 
            timeElapsed = time.time() - self._startTime
            self._fpsEstimate = self._framesElapsed / timeElapsed
            logc.info('fps estimate: %d' % self._fpsEstimate )
        self._framesElapsed += 1


        #Draw to the window
        #if self._previewWindowManager is not None: 
        #    if self._shouldMirrorPreview:
        #        mirroredFrame = numpy.fliplr(self._frame).copy()
        #        self._previewWindowManager.show(mirroredFrame)
        #    else: 
        #        self._previewWindowManager.show(self._frame)


        #Write image file
        if self.isWritingImage: 
            cv2.imwrite(self._imageFilename, self._frame)
            self._imageFilename = None


        #Write to video 
        self._writeVideoFrame()
            
        #Release
        self._frame = None
        self._enteredFrame = False

    def writeImage( self, filename ):
        self._imageFilename = filename


    def startWritingVideo( self, filename, encoding ):
        self._videoFilename = filename
        self._videoEncoding = encoding
        logc.warning( 'Start Writing Video: %s' % filename )

    def stopWritingVideo ( self ):
        self._videoFilename = None
        self._videoEncoding = None
        self._videoWriter = None
        logc.warning( 'Stop Writing Video' )
        

    def _writeVideoFrame( self ):
        if not self.isWritingVideo:
            return
        
        if self._videoWriter is None:
            fps = self._capture.get( cv2.CAP_PROP_FPS ) 
            logc.warning("fps: %d" % fps)
            if fps <= 0.0:
                if self._framesElapsed < 20: 
                    # wait for more frames to get good estimate
                    return
                else: 
                    logc.warning('fps estimate used: %d' % self._fpsEstimate )
                    fps = self._fpsEstimate            

            size = ( int (self._capture.get( cv2.CAP_PROP_FRAME_WIDTH )), 
                     int( self._capture.get( cv2.CAP_PROP_FRAME_HEIGHT) ))
            logc.warning('size used: %d x %d' % (size[0], size[1]) )

            self._videoWriter = cv2.VideoWriter( self._videoFilename, 
                                                 self._videoEncoding, fps, size, False )
        self._videoWriter.write(self._frame)
        #print 'Write this frame'

    def isDebug ( self ):
        return logc.getEffectiveLevel() <= logging.INFO




    
class WindowManager ( object ):
    
    def __init__( self, windowName, keypressCallback = None):
        #logw.debug('initializing window manager')
        self.keypressCallback = keypressCallback
        #logw.debug('set keypresscallback')
        self._windowName = windowName
        self._isWindowCreated = False
        #logw.debug('done initializing window manager')


    @property
    def isWindowCreated ( self ):
        return self._isWindowCreated

    def createWindow ( self ):
        cv2.namedWindow( self._windowName)#, cv2.WINDOW_NORMAL)
        self._isWindowCreated = True 

    def show ( self, frame ):
        try:
            cv2.imshow( self._windowName, frame )
        except RuntimeError as e:
            logc.exception(str(e))
            
    
        
    def destroyWindow ( self ):
        cv2.destroyWindow( self._windowName ) 
        self._isWindowCreated = False


    def processEvents ( self ):
        keycode = cv2.waitKey( 1 )
        
        if self.keypressCallback is not None and keycode != -1:
            #Discard non-ASCII info encoded by GTK
            keycode &= 0xFF
            self.keypressCallback(keycode)

        

        
