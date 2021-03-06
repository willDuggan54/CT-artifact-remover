# -*- coding: utf-8 -*-
"""pix2pix.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1SIT4LW6H6Xuz0tGgXjTqJfN9iyFwOCrz
"""

#!/usr/bin/env python
# coding: utf-8

# # Implementing the necessary libraries



import tensorflow as tf
import numpy as np
import time
#from google.colab import drive
from keras.preprocessing.image import ImageDataGenerator
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import glob
from PIL import Image
#tf.compat.v1.config.experimental.set_lms_enabled(True)
from random import randint
# Data Gathering and Preprocessing


print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))
#tf.config.threading.set_inter_op_parallelism_threads(num_threads)


path = '/content/drive/MyDrive/GAN_Data/trainingDataNC/truth_small'
path2 = '/content/drive/MyDrive/GAN_Data/trainingDataNC/artifact_10x_small'
BATCH_SIZE = 1
COUNT = 0

#####Preprocessing#####
def load_image(image):
  image = tf.io.read_file(image)
  image = tf.image.decode_png(image)
  image = tf.cast(image, tf.float32)
  return image

def normalize(image):
  image = (image/127.5)-1
  return image

def preprocess(image):
  image = load_image(image)
  image = normalize(image)
  return image

def crop(image_a, image_t):
  combined_image = tf.concat([image_a, image_t], axis=0)
  cropped = tf.image.random_crop(combined_image, size=[2, 512, 512, 1])
  return cropped[0], cropped[1]

def resize(image_a, image_t):
  image_a = tf.image.resize(images=image_a, size=[542,542], method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
  image_t = tf.image.resize(images=image_t, size=[542,542], method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
  return image_a, image_t

def random_jittering(image_a, image_t):
  image_a, image_t = resize(image_a, image_t)
  image_a, image_t = crop(image_a, image_t)
  if (tf.random.uniform(shape=[1]) >= 0.5):
    image_a = tf.image.flip_left_right(image_a)
    image_t = tf.image.flip_left_right(image_t)
  return image_a, image_t

truth_dataset = tf.data.Dataset.list_files(path + '/*.png', shuffle=False)
truth_dataset = truth_dataset.map(preprocess, num_parallel_calls=tf.data.AUTOTUNE)
truth_dataset = truth_dataset.batch(BATCH_SIZE)

artifact_dataset = tf.data.Dataset.list_files(path2 + '/*.png', shuffle=False)
artifact_dataset = artifact_dataset.map(preprocess, num_parallel_calls=tf.data.AUTOTUNE)
artifact_dataset = artifact_dataset.batch(BATCH_SIZE)

def transform_dataset(truth_dataset, artifact_dataset):
  temp_truth = []
  temp_art = []
  for t_images, a_images in zip(truth_dataset, artifact_dataset):
    a_images, t_images = random_jittering(a_images, t_images)
    temp_truth.append(t_images)
    temp_art.append(a_images)
  truth_dataset = tf.data.Dataset.from_tensor_slices(temp_truth)
  artifact_dataset = tf.data.Dataset.from_tensor_slices(temp_art)
  return truth_dataset, artifact_dataset


# Creating the Discriminator Model

def create_discriminator_model():
  initializer = tf.random_normal_initializer(0.0, 0.02)
  input_target = tf.keras.layers.Input(shape= (512, 512, 1))
  input_source = tf.keras.layers.Input(shape= (512, 512, 1))
  merged = tf.keras.layers.Concatenate()([input_target, input_source])
  x = tf.keras.layers.Conv2D(64, (4,4), (2,2), padding='valid', kernel_initializer=initializer)(merged)
  #x = tf.keras.layers.BatchNormalization()(x)
  x = tf.keras.layers.LeakyReLU(alpha=0.2)(x) 
  x = tf.keras.layers.Conv2D(128, (4,4), (2,2), padding='valid', kernel_initializer=initializer)(x)
  x = tf.keras.layers.BatchNormalization()(x)
  x = tf.keras.layers.LeakyReLU(alpha=0.2)(x)
  x = tf.keras.layers.Conv2D(256, (4,4), (2,2), padding='same', kernel_initializer=initializer)(x)
  x = tf.keras.layers.BatchNormalization()(x)
  x = tf.keras.layers.LeakyReLU(alpha=0.2)(x)
  x = tf.keras.layers.Conv2D(512, (4,4), (2,2), padding='same', kernel_initializer=initializer)(x)
  x = tf.keras.layers.BatchNormalization()(x)
  x = tf.keras.layers.LeakyReLU(alpha=0.2)(x)
  x = tf.keras.layers.Conv2D(1, (4,4), padding='same', kernel_initializer=initializer)(x)
  output = tf.keras.layers.Activation('sigmoid')(x)

  model = tf.keras.Model(inputs=[input_target, input_source], outputs=output)
  return model


# **Discriminator Loss Function**



def get_discriminator_loss(real_output, fake_output):
  real_loss = cross_entropy(tf.ones_like(real_output), real_output)
  fake_loss = cross_entropy(tf.zeros_like(fake_output), fake_output)
  total_loss = real_loss + fake_loss
  return total_loss/2


# **Creating the Downsampling Layer for the
#  Generator**
# 
# The layer is a sequential model that will be concat. with the rest of the model. Implementing the layers in batches will also help with adding the skip connections later. The layer consists of 2 convolution layers and 1 Max pooling layer.

# 

def encoder(filters, prev, batchnorm=True):
  init = tf.random_normal_initializer(0. , 0.02)
  x= tf.keras.layers.Conv2D(filters, (4,4), strides=(2,2), kernel_initializer=init, padding='same')(prev)
  if batchnorm:
    x = tf.keras.layers.BatchNormalization()(x)
  x = tf.keras.layers.LeakyReLU(alpha=0.2)(x)
  return x

# **Creating the Upsampling Layer for the Generator**
# 
# Layer is also a sequential model that is custom built for easy repeatability. The concat parameter is the name of the layer that will be concatenated with (skip connection).


def decoder(filters, prev, skip, dropout=False):
  init = tf.random_normal_initializer(0. , 0.02)
  x = tf.keras.layers.Conv2DTranspose(filters, (4,4), strides=(2,2), padding='same', kernel_initializer=init)(prev)
  x = tf.keras.layers.BatchNormalization()(x)
  if dropout:
    x = tf.keras.layers.Dropout(0.5)(x)
  x = tf.keras.layers.Concatenate()([x, skip])
  x = tf.keras.layers.Activation('relu')(x)
  return x


# **Building the Generator**


def create_generator_model():
  init = tf.random_normal_initializer(0. , 0.02)
  input = tf.keras.layers.Input(shape=[512, 512, 1])
  enc0 = encoder(64, prev=input, batchnorm=False)
  enc1 = encoder(128, prev=enc0)
  enc2 = encoder(256, prev=enc1)
  enc3 = encoder(512, prev=enc2)
  enc4 = encoder(512, prev=enc3)
  enc5 = encoder(512, prev=enc4)
  enc6 = encoder(512, prev=enc5)
  #down4 = downsample(1024, (3,3), (1,1), (2,2))(down3)

  
  #Middle Block
  mid = tf.keras.layers.Conv2D(512, (4,4), strides=(2,2), padding='same', kernel_initializer=init)(enc6)
  mid = tf.keras.layers.LeakyReLU(alpha=0.2)(mid)

  dec0 = decoder(512, prev=mid, skip=enc6, dropout=True)
  dec1 = decoder(512, prev=dec0, skip=enc5, dropout=True)
  dec2 = decoder(512, prev=dec1, skip=enc4, dropout=True)
  dec3 = decoder(512, prev=dec2, skip=enc3)
  dec4 = decoder(256, prev=dec3, skip=enc2)
  dec5 = decoder(128, prev=dec4, skip=enc1)
  dec6 = decoder(64, prev=dec5, skip=enc0)

  #output layers
  x = tf.keras.layers.Conv2DTranspose(1, (4,4), strides=(2,2), padding='same', kernel_initializer=init)(dec6)
  #x = tf.keras.layers.Add()([input, x])
  output = tf.keras.layers.Activation('tanh')(x)


  model = tf.keras.Model(inputs=[input], outputs=[output])

  return model


# **Generator Loss Function**



def get_generator_loss(fake_output, generated_images, target):
  LAMBDA = 100
  gan_loss = cross_entropy(tf.ones_like(fake_output), fake_output)
  #Mean absolute error from the pix2pix paper
  l1_loss = tf.reduce_mean(tf.abs(target - generated_images))    ###Normalize truth image
  gen_loss = gan_loss + (LAMBDA*l1_loss)
  return gen_loss


###**Generating Figures**###
def plot_images(prediction, input, target):
  plt.figure(figsize=(15,15))
  display_list = [input, target, prediction]
  title = ['Artifacted Image', 'Ground Truth Image', 'Generated Image']

  for i in range(3):
    plt.subplot(1, 3, i+1)
    plt.title(title[i])
    plt.imshow(display_list[i]*0.5 +0.5, cmap='gray')
    plt.axis('off')
  plt.show()



# ## **Training**



def train(truth_dataset, artifact_dataset, epochs):
  for i in range(epochs):
    print('Epoch: ', i)
    if i % 20 == 0:
      saveModel(generator, i)
    show = True
    for t_images, a_images in zip(truth_dataset, artifact_dataset):
      print('.', end='')
      train_step(truth_image=t_images, artifact_image=a_images, show=show)
      show = False




def train_step(artifact_image, truth_image, show):
  with tf.GradientTape() as gen_tape, tf.GradientTape() as discriminator_tape:
    #print(fake_image_noise.shape)
    generated_images = generator(artifact_image, training=True)
    real_output = model_discriminator([artifact_image, truth_image], training=True)
    fake_output = model_discriminator([artifact_image, generated_images], training=True)
    if show:
      generated_images = tf.reshape(generated_images, (512,512))
      artifact_image = tf.reshape(artifact_image, (512,512))
      truth_image = tf.reshape(truth_image, (512,512))
      plot_images(generated_images, artifact_image, truth_image)

    gen_loss = get_generator_loss(fake_output, generated_images, truth_image)
    discriminator_loss = get_discriminator_loss(real_output, fake_output)

    gradients_of_gen = gen_tape.gradient(gen_loss, generator.trainable_variables)
    gradients_of_disc = discriminator_tape.gradient(discriminator_loss, model_discriminator.trainable_variables)

    generator_optimizer.apply_gradients(zip(gradients_of_gen, generator.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(gradients_of_disc, model_discriminator.trainable_variables))

def saveModel(generator, epoch):
  name = 'pix2pix_e' + str(epoch) +'.h5'
  generator.save(name)
  !cp $name "/content/drive/MyDrive/GAN_Data/Models/Pix2pixLessJitter"
# # **Main Section**
truth_dataset, artifact_dataset = transform_dataset(truth_dataset, artifact_dataset)
truth_dataset = truth_dataset.batch(BATCH_SIZE)
artifact_dataset = artifact_dataset.batch(BATCH_SIZE)

model_discriminator = create_discriminator_model()
discriminator_optimizer = tf.optimizers.Adam(learning_rate=2e-4, beta_1=0.5)
tf.keras.utils.plot_model(model_discriminator, show_shapes=True, dpi=64)
#model_discriminator(np.random.randn(512, 512, 1))#passing it random stuff??
print('Created Discriminator!')

generator = create_generator_model()
tf.keras.utils.plot_model(model_discriminator, show_shapes=True, dpi=64)

generator_optimizer = tf.optimizers.Adam(learning_rate=2e-4, beta_1=0.5)
print('Created Generator!')

cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits=True)

tf.keras.utils.plot_model(generator, show_shapes=True, dpi=64)

train(truth_dataset, artifact_dataset, epochs=150)

generator.save('pix2pix.h5')
