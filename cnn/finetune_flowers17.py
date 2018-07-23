from sklearn.preprocessing import LabelBinarizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from cnn.preprocessing.imagetoarraypreprocessor import ImageToArrayPreprocessor
from cnn.preprocessing.aspectawarepreprocessor import AspectAwarePreprocessor
from cnn.datasets.dataset_loader import SimpleDatasetLoader
from cnn.nn.conv.fcheadnet import FCHeadNet
from keras.preprocessing.image import ImageDataGenerator
from keras.optimizers import RMSprop
from keras.optimizers import SGD
from keras.applications import VGG16
from keras.layers import Input
from keras.models import Model
from imutils import paths
import numpy as np
import argparse
import os

ap = argparse.ArgumentParser()
ap.add_argument("-d", "--dataset", required=True, help="path to input dataset")
ap.add_argument("-m", "--lpr_model", required=True, help="path to output lpr_model")
args = vars(ap.parse_args())

# construct the image generator for data augmentation
aug = ImageDataGenerator(rotation_range=30,
                         width_shift_range=0.1,
                         height_shift_range=0.1,
                         shear_range=0.2,
                         zoom_range=0.2,
                         horizontal_flip=True,
                         fill_mode="nearest")

# grab the list of images that we’ll be describing, then extract
# the class label names from the image paths
print("[INFO] loading images...")
imagePaths = list(paths.list_images(args["dataset"]))
classNames = [pt.split(os.path.sep)[-2] for pt in imagePaths]
classNames = [str(x) for x in np.unique(classNames)]

# initialize the image preprocessors
aap = AspectAwarePreprocessor(224, 224)
iap = ImageToArrayPreprocessor()

# load the dataset from disk then scale the raw pixel intensities to
# the range [0, 1]
sdl = SimpleDatasetLoader(preprocessor=[aap, iap])
data, labels = sdl.load(imagePaths, verbose=500)
data = data / 255

# partition the data into training and testing splits using 75% of
# the data for training and the remaining 25% for testing
trainX, testX, trainY, testY = train_test_split(data, labels,
                                                test_size=0.25,
                                                stratify=labels,
                                                random_state=42)

# convert the labels from integers to vectors
trainY = LabelBinarizer().fit_transform(trainY)
testY = LabelBinarizer().fit_transform(testY)

# load the VGG16 network, ensuring the head FC layer sets are left
# off
baseModel = VGG16(weights="imagenet", include_top=False,
                  input_tensor=Input(shape=(224, 224, 3)))

# initialize the new head of the network, a set of FC layers
# followed by a softmax classifier
headModel = FCHeadNet.build(baseModel, len(classNames), 256)

# place the head FC lpr_model on top of the base lpr_model -- this will
# become the actual lpr_model we will train
model = Model(inputs=baseModel.input, outputs=headModel)

# loop over all layers in the base lpr_model and freeze them so they
# will *not* be updated during the training process
for layer in baseModel.layers:
    layer.trainable = False

# compile our lpr_model (this needs to be done after our setting our
# layers to being non-trainable
print("[INFO] compiling lpr_model...")
opt = RMSprop(lr=0.001)
model.compile(loss="categorical_crossentropy", optimizer=opt,
              metrics=["accuracy"])

# train the head of the network for a few epochs (all other
# layers are frozen) -- this will allow the new FC layers to
# start to become initialized with actual "learned" values
# versus pure random
print("[INFO] training head...")
model.fit_generator(aug.flow(trainX, trainY, batch_size=2),
                    validation_data=(testX, testY), epochs=25,
                    steps_per_epoch=len(trainX) // 2, verbose=1)

# now that the head FC layers have been trained/initialized, lets
# unfreeze the final set of CONV layers and make them trainable
for layer in baseModel.layers[15:]:
    layer.trainable = True

# for the changes to the lpr_model to take affect we need to recompile
# the lpr_model, this time using SGD with a *very* small learning rate
print("[INFO] re-compiling lpr_model...")
opt = SGD(lr=0.001)
model.compile(loss="categorical_crossentropy", optimizer=opt,
              metrics=["accuracy"])

# train the lpr_model again, this time fine-tuning *both* the final set
# of CONV layers along with our set of FC layers
print("[INFO] fine-tuning lpr_model...")
model.fit_generator(aug.flow(trainX, trainY, batch_size=2), validation_data=(testX, testY),
                    epochs=100, steps_per_epoch=len(trainX) // 2, verbose=1)

# evaluate the network on the fine-tuned lpr_model
print("[INFO] evaluating after fine-tuning...")
predictions = model.predict(testX, batch_size=2)
print(classification_report(testY.argmax(axis=1),
                            predictions.argmax(axis=1),
                            target_names=classNames))

# save the lpr_model to disk
print("[INFO] serializing lpr_model...")
model.save(args["lpr_model"])