'''
Notes :
    - This bot is targeted at automated trading on binomo.com & can have it's scope expanded to other binary options broking websites with ease
    - Use non-chromium/non-firefox browsers to obtain a video feed (e.g.; Pale Moon)
    - Red HSV limits : hMin, sMin, vMin, hMax, sMax, vMax =  170 , 121 , 255 , 179 , 170 , 255
    - Green HSV limits : hMin, sMin, vMin, hMax, sMax, vMax =  60 , 190 , 180 , 90 , 255 , 255
    - Finish flag HSV limits : hMin, sMin, vMin, hMax, sMax, vMax =  172 , 32 , 130 , 179 , 153 , 225
    - Bounding boxes : green bars, red bars = yellow, blue
    - Up button coordinates : (1178, 511)
    - Down button coordinates : (1178, 575)
    - Idle location coordinates : (1244, 371)
    - Refresh button coordinates : (496, 77)
'''

import os
import mouse
import cv2 as cv
import numpy as np
from time import time
from time import sleep
import win32gui, win32ui, win32con

'''
def stackImages(scale,imgArray): # image stacking function (for testing purposes)
    rows = len(imgArray)
    cols = len(imgArray[0])
    rowsAvailable = isinstance(imgArray[0], list)
    width = imgArray[0][0].shape[1]
    height = imgArray[0][0].shape[0]
    if rowsAvailable:
        for x in range ( 0, rows):
            for y in range(0, cols):
                if imgArray[x][y].shape[:2] == imgArray[0][0].shape [:2]:
                    imgArray[x][y] = cv.resize(imgArray[x][y], (0, 0), None, scale, scale)
                else:
                    imgArray[x][y] = cv.resize(imgArray[x][y], (imgArray[0][0].shape[1], imgArray[0][0].shape[0]), None, scale, scale)
                if len(imgArray[x][y].shape) == 2: imgArray[x][y]= cv.cvtColor(imgArray[x][y], cv.COLOR_GRAY2BGR)
        imageBlank = np.zeros((height, width, 3), np.uint8)
        hor = [imageBlank]*rows
        hor_con = [imageBlank]*rows
        for x in range(0, rows):
            hor[x] = np.hstack(imgArray[x])
        ver = np.vstack(hor)
    else:
        for x in range(0, rows):
            if imgArray[x].shape[:2] == imgArray[0].shape[:2]:
                imgArray[x] = cv.resize(imgArray[x], (0, 0), None, scale, scale)
            else:
                imgArray[x] = cv.resize(imgArray[x], (imgArray[0].shape[1], imgArray[0].shape[0]), None,scale, scale)
            if len(imgArray[x].shape) == 2: imgArray[x] = cv.cvtColor(imgArray[x], cv.COLOR_GRAY2BGR)
        hor= np.hstack(imgArray)
        ver = hor
    return ver
'''

class WindowCapture:

    # properties
    w = 0
    h = 0
    hwnd = None
    cropped_x = 0
    cropped_y = 0
    # offset_x = 0
    # offset_y = 0

    # constructor
    def __init__(self, window_name):
        # find the handle for the window we want to capture
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception('Window not found: {}'.format(window_name))

        # get the window size
        # window_rect = win32gui.GetWindowRect(self.hwnd)
        self.w = 1920 # window_rect[2] - window_rect[0]
        self.h = 1080 # window_rect[3] - window_rect[1]

        # account for the window border and titlebar and cut them off
        border_pixels = 0
        titlebar_pixels = 0
        self.w = self.w - (border_pixels * 2)
        self.h = self.h - titlebar_pixels - border_pixels
        self.cropped_x = border_pixels
        self.cropped_y = titlebar_pixels

        # set the cropped coordinates offset so we can translate screenshot
        # images into actual screen positions
        #self.offset_x = window_rect[0] + self.cropped_x
        #self.offset_y = window_rect[1] + self.cropped_y

    def get_screenshot(self):

        # get the window image data
        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0, 0), (self.w, self.h), dcObj, (self.cropped_x, self.cropped_y), win32con.SRCCOPY)

        # convert the raw data into a format opencv can read
        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.fromstring(signedIntsArray, dtype='uint8')
        img.shape = (self.h, self.w, 4)

        # free resources
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        # drop the alpha channel, or cv.matchTemplate() will throw an error like:
        #   error: (-215:Assertion failed) (depth == CV_8U || depth == CV_32F) && type == _templ.type()
        #   && _img.dims() <= 2 in function 'cv::matchTemplate'
        img = img[...,:3]

        # make image C_CONTIGUOUS to avoid errors that look like:
        #   File ... in draw_rectangles
        #   TypeError: an integer is required (got type tuple)
        # see the discussion here:
        # https://github.com/opencv/opencv/issues/14866#issuecomment-580207109
        img = np.ascontiguousarray(img)
        return img

    # find the name of the window you're interested in.
    # once you have it, update window_capture()
    # https://stackoverflow.com/questions/55547940/how-to-get-a-list-of-the-name-of-every-open-window
    def list_window_names(self):
        def winEnumHandler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                print(hex(hwnd), win32gui.GetWindowText(hwnd))
        win32gui.EnumWindows(winEnumHandler, None)

    # translate a pixel position on a screenshot image to a pixel position on the screen.
    # pos = (x, y)
    # WARNING: if you move the window being captured after execution is started, this will
    # return incorrect coordinates, because the window position is only calculated in
    # the __init__ constructor.
    def get_screen_position(self, pos):
        return (pos[0] + self.offset_x, pos[1] + self.offset_y)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# click delay (avg fps = 12)
delay = 705
clickTime = 0

# initialize the WindowCapture class
wincap = WindowCapture('Trading - Pale Moon')

loop_time = time()

while(True):

    # raw feed processing
    screenshot = wincap.get_screenshot()
    imS = cv.resize(screenshot, (1920, 1080))  # Resize image
    imS = imS[680:700, 1635:1920]

    imgHSV = cv.cvtColor(imS, cv.COLOR_BGR2HSV)
    redMask = cv.inRange(imgHSV, np.array([170, 121, 255]), np.array([179, 170, 255]))
    greenMask = cv.inRange(imgHSV, np.array([60, 190, 180]), np.array([90, 255, 255]))

    contours, _ = cv.findContours(redMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    clearRed = 0
    for j, contour in enumerate(contours):
        bbox = cv.boundingRect(contour)
        # Create a mask for this contour
        contour_mask = np.zeros_like(redMask)
        cv.drawContours(contour_mask, contours, j, 255, -1)
        top_left, bottom_right = (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3])
        cv.rectangle(imS, top_left, bottom_right, (255, 0, 0), 2)
        # finding the area of this contour
        contourAreaRed = bbox[2] * bbox[3]

    contours, _ = cv.findContours(greenMask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    for j, contour in enumerate(contours):
        bbox = cv.boundingRect(contour)
        # Create a mask for this contour
        contour_mask = np.zeros_like(greenMask)
        cv.drawContours(contour_mask, contours, j, 255, -1)
        top_left, bottom_right = (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3])
        cv.rectangle(imS, top_left, bottom_right, (0, 255, 255), 2)
        # finding the area of this contour
        contourAreaGreen = bbox[2] * bbox[3]

    if (contourAreaRed > contourAreaGreen) and (clickTime > delay): # vote down
        mouse.move(1179, 575)
        mouse.click('left')
        sleep(1)
        mouse.move(1244, 371)
        clickTime = 0

    elif (contourAreaRed < contourAreaGreen) and (clickTime > delay) : # vote up
        mouse.move(1179, 511)
        mouse.click('left')
        sleep(1)
        mouse.move(1244, 371)
        clickTime = 0

    # Summary
    print('FPS : {}'.format(1 / (time() - loop_time)))
    print('Red contour area : ', contourAreaRed)
    print('Green contour area : ', contourAreaGreen)
    print('clickTime : ', clickTime)
    loop_time = time()
    # cv.imshow('ROI', imS)

    clickTime += 1

    # press 'q' with the output window focused to exit
    if cv.waitKey(1) == ord('q'):
        cv.destroyAllWindows()
        break

print('Done')
