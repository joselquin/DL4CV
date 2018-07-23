import time


def SpeedTest(image_path):
    grr = cv2.imread(image_path)
    model = pr.LPR("lpr_model/cascade.xml", "lpr_model/model12.h5", "lpr_model/ocr_plate_all_gru.h5")
    model.SimpleRecognizePlateByE2E(grr)
    t0 = time.time()
    for x in range(20):
        model.SimpleRecognizePlateByE2E(grr)
    t = (time.time() - t0) / 20.0
    print("Image size :" + str(grr.shape[1]) + "x" + str(grr.shape[0]) + " need " + str(round(t * 1000, 2)) + "ms")


from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw

fontC = ImageFont.truetype("./Font/platech.ttf", 14, 0)


def drawRectBox(image, rect, addText):
    cv2.rectangle(image, (int(rect[0]), int(rect[1])), (int(rect[0] + rect[2]), int(rect[1] + rect[3])), (0, 0, 255), 2,
                  cv2.LINE_AA)
    cv2.rectangle(image, (int(rect[0] - 1), int(rect[1]) - 16), (int(rect[0] + 115), int(rect[1])), (0, 0, 255), -1,
                  cv2.LINE_AA)
    img = Image.fromarray(image)
    draw = ImageDraw.Draw(img)
    draw.text((int(rect[0] + 1), int(rect[1] - 16)), addText, (255, 255, 255), font=fontC)
    imagex = np.array(img)
    return imagex


import field_test.smart_test.license_plate_recognition.hyperLPR_lite as pr
import cv2
import numpy as np

grr = cv2.imread("example_img/2_.jpg")
model = pr.LPR("lpr_model/cascade.xml", "lpr_model/model12.h5", "lpr_model/ocr_plate_all_gru.h5")
for pstr, confidence, rect in model.SimpleRecognizePlateByE2E(grr):
    if confidence > 0.7:
        image = drawRectBox(grr, rect, pstr + " " + str(round(confidence, 3)))
        print("plate_str:")
        print(pstr)
        print("plate_confidence")
        print(confidence)

image = cv2.resize(image, (600, 600))
cv2.imshow("image", image)
cv2.waitKey(0)

SpeedTest("example_img/2_.jpg")
