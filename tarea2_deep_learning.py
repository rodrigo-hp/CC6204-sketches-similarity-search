# -*- coding: utf-8 -*-
"""Tarea2_Deep_Learning.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/13puoC_ms51RUdx-Yz9fIj2guJ_5NOqjT

# Tarea 2: Clasificación y búsqueda por similitud de sketches usando redes convolucionales

### Autor: Rodrigo Hernández

## Parte 0: Importar librerías y preparar la descarga de datasets

Se importan las librerías que serán utilizadas en la tarea:
"""

import numpy as np
import os
from skimage import io
from sklearn import preprocessing
import scipy.misc
import json
import random
import sys
import tensorflow as tf
import cv2

"""Se crean directorios que serán utilizados para guardar los archivos generados:"""

!mkdir /content/t2
!mkdir /content/t2/raw_data
!mkdir /content/t2/tfrecords
!mkdir /content/t2/model

"""Entramos a la carpeta en donde guardaremos todos los archivos .ndjson:"""

cd /content/t2/raw_data

"""Descargamos todo el dataset simplificado:"""

!gsutil -m cp gs://quickdraw_dataset/full/simplified/* /content/t2/raw_data

"""## Parte 1: Preprocesamiento de los datos y generación de las imágenes

La siguiente función genera los strokes sobre una imagen:
"""

def parse_line(ndjson_line):
  # get the JSON
  sample = json.loads(ndjson_line)
  # get the label of the example
  class_name = sample["word"]
  if not class_name:
    print ("Empty classname")
    return None, None
  # get the strokes of the example
  drawing_array = sample["drawing"]
  # create the canvas
  img = np.zeros((256, 256), dtype=np.uint8)
  img[:,:] = 255
  # make the drawing
  for stroke in drawing_array:
    xa = -1
    ya = -1 
    for p in zip(stroke[0], stroke[1]):
      x = p[0]
      y = p[1]
      if xa >= 0 and ya >= 0:
        cv2.line(img, (xa,ya), (x,y), 0, 3)
      xa = x
      ya = y
  
  return img, class_name

"""La siguiente función se encarga de tomar 100 archivos .ndjson al azar y tomar 1000 ejemplos para entrenamiento y 50 para prueba. Retorna un arreglo con todos los ejemplos de training y otro con todos los ejemplos de testing:"""

def extract_ndjson_files(path):
  # list all files in dir
  files = [f for f in os.listdir(path) if os.path.isfile(f)]

  # select 100 files randomly 
  samples = np.random.choice(files, 100, replace=False)
  training_examples = []
  test_examples = []
  # open each one of the ndjson files
  for file in samples:
    with open(file) as f:
      # get all of the examples of the file
      content = []
      for line in f:
        content.append(line.rstrip('\n'))
    random.shuffle(content)
    # add new examples to lists
    training_examples.extend(content[:1000])
    test_examples.extend(content[1000:1050])
    del content[:]
      
  return training_examples, test_examples

"""La siguiente función se encarga de recorrer cada ejemplo en los arreglos y generar los strokes:"""

def drawings_parser(training_examples, test_examples):
  training_drawings = []
  training_labels = []
  test_drawings = []
  test_labels = []
  
  # parse every example
  for ex in training_examples:
    # first the training set
    single_drawing, single_label = parse_line(ex)
    training_drawings.append(single_drawing)
    training_labels.append(single_label)
  del training_examples[:]
  for ex in test_examples:
    # then the test set
    single_drawing, single_label = parse_line(ex)
    test_drawings.append(single_drawing)
    test_labels.append(single_label)
  del test_examples[:]
  # create the label encoder to transform the classes to numbers
  encoder = preprocessing.LabelEncoder()
  encoder.fit(test_labels)
  training_classes = list(encoder.transform(training_labels))
  test_classes = list(encoder.transform(test_labels))
  
  return training_drawings, training_classes, test_drawings, test_classes, encoder

"""Se crea un método para reducir el tamaño de todas las imagenes:"""

def resize_images(images):
  for i in range(0,len(images)):
    images[i] = cv2.resize(images[i], (128, 128), interpolation = cv2.INTER_AREA)
  
  return images

"""Se crea un método para aleatorizar los arreglos de imagenes y de clases:"""

def shuffle_images(images, labels):
  images = np.array(images)
  labels = np.array(labels)
  inds = list(range(len(labels)))
  np.random.shuffle(inds)
  images = images[inds]
  labels = labels[inds]
  return images, labels

"""Se generan los ejemplos de training y los de prueba:"""

training_examples, test_examples = extract_ndjson_files('/content/t2/raw_data')

"""Se generan las imagenes en conjunto con sus clases:"""

training_drawings, training_classes, test_drawings, test_classes, encoder = drawings_parser(training_examples, test_examples)

"""Se reduce el tamaño de todas las imagenes a 128x128:"""

#del training_examples[:]
#del test_examples[:]
training_drawings = resize_images(training_drawings)
test_drawings = resize_images(test_drawings)

"""Se plotea una imagen al azar y la clase a la que corresponde:"""

ex = 4500
import matplotlib.pyplot as plt
print(encoder.inverse_transform(test_classes[ex]))
imgplot = plt.imshow(test_drawings[ex])

"""Se ordenan los arreglos al azar:"""

# shuffle both arrays
training_drawings, training_classes = shuffle_images(training_drawings, training_classes)
test_drawings, test_classes = shuffle_images(test_drawings, test_classes)

"""## Parte 2: Transformación de las imágenes a TFRecords

Se definen funciones para generar los TFRercords a partir de las imagenes y clases:
"""

# %% int64 should be used for integer numeric values
def _int64_feature(value):
  return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))
# %% byte should be used for string  | char data
def _bytes_feature(value):
  return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))
# %% float should be used for floating point data
def _float_feature(value):    
  return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))

def createTFRecord(images, labels, image_shape, tfr_filename):
    h = image_shape[0]
    w = image_shape[1]    
    writer = tf.python_io.TFRecordWriter(tfr_filename)    
    assert len(images) == len(labels)
    mean_image = np.zeros([h,w], dtype=np.float32)
    for i in range(len(images)):        
        image = images[i,:,:]
        #print("{}label: {}".format(label[i]))
        #create a feature
        feature = {'train/label': _int64_feature(labels[i]), 
                   'train/image': _bytes_feature(tf.compat.as_bytes(image.tostring()))}
        #crate an example protocol buffer
        example = tf.train.Example(features = tf.train.Features(feature=feature))        
        #serialize to string an write on the file
        writer.write(example.SerializeToString())
        mean_image = mean_image + images[i, :, :] / len(images)

    mean_image = mean_image         
    #serialize mean_image
    writer.close()
    sys.stdout.flush()
    return mean_image

def createSketchTFRecord(str_path, id_type, im_size, images, labels):    
    image_shape = np.array([im_size, im_size])
    number_of_classes = 0 # deprecated, this variable is kept por compatibility    
    if ( id_type + 1 ) & 1 : # train
        tfr_filename = os.path.join(str_path, "train.tfrecords") 
        mean_image = createTFRecord(images, labels, image_shape, tfr_filename)
        #saving mean image        
        print("train_record saved at {}.".format(tfr_filename))        
        mean_file = os.path.join(str_path, "mean.dat")
        print("mean_file {}".format(mean_image.shape))
        mean_image.tofile(mean_file)
        print("mean_file saved at {}.".format(mean_file))                          
    elif ( id_type + 1 ) & 2 : # test
        tfr_filename = os.path.join(str_path, "test.tfrecords")
        createTFRecord(images, labels, image_shape, tfr_filename)
        print("test_record saved at {}.".format(tfr_filename))
    #saving metadata file    
    metadata_array = np.append(image_shape, [number_of_classes])                        
    metadata_file = os.path.join(str_path, "metadata.dat")
    metadata_array.tofile(metadata_file)
    print("metadata_file saved at {}.".format(metadata_file))

"""Se generan los TFRecords de las imagenes de entrenamiento y sus clases:"""

createSketchTFRecord('/content/t2/tfrecords', 0, 128, training_drawings, training_classes)

"""Se generan los TFRecords de las imagenes de prueba y sus clases:"""

createSketchTFRecord('/content/t2/tfrecords', 1, 128, test_drawings, test_classes)

"""Se define una función para interpretar los TFRecords:"""

def parser_tfrecord_sk(serialized_example, im_size, mean_img, number_of_classes):    
    features = tf.parse_example([serialized_example],
                                features={
                                        'train/image': tf.FixedLenFeature([], tf.string),
                                        'train/label': tf.FixedLenFeature([], tf.int64),
                                        })
    image = tf.decode_raw(features['train/image'], tf.uint8)    
    image = tf.reshape(image, [im_size, im_size])
    image = tf.cast(image, tf.float32) - tf.cast(tf.constant(mean_img), tf.float32)
    #image = image * 1.0 / 255.0    
    #one-hot 
    label = tf.one_hot(tf.cast(features['train/label'], tf.int32), number_of_classes)
    label = tf.reshape(label, [number_of_classes])
    label = tf.cast(label, tf.float32)
    return image, label

"""## Parte 3:	Diseño de la arquitectura de las redes convolucionales

Se definen las capas que se utilizarán en los modelos:
"""

#gaussian weights 
def gaussian_weights(shape,  mean, stddev):
    return tf.truncated_normal(shape, 
                               mean = mean, 
                               stddev = stddev)

#fully-connected layer fc
def fc_layer(input, size, name, use_relu=True): 
    layer_shape_in =  input.get_shape()
    # shape is a 1D tensor with 4 values
    num_features_in = layer_shape_in[1:4].num_elements()
    #reshape to  1D vector
    input_reshaped = tf.reshape(input, [-1, num_features_in])
    shape = [num_features_in, size]
    W = tf.Variable(gaussian_weights(shape, 0.0, 0.02), name=name)     
    b = tf.Variable(tf.zeros(size))
    #
    layer = tf.add( tf.matmul(input_reshaped, W) ,  b)    
    
    if use_relu:
        layer=tf.nn.relu(layer)
    return  layer
  
#convolution layer using stride = 1, is_training is added to set BN approproiately    
def conv_layer(input, shape, name, stride = 1, is_training = False):    
    #weights are initialized according to a gaussian distribution
    W =  tf.Variable(gaussian_weights(shape, 0.0, 0.01), name=name)     
    #weights for bias ares fixed as constants 0
    b = tf.Variable(tf.zeros(shape[3]), name='bias_'+name)
    return tf.nn.relu(
            tf.layers.batch_normalization(
                tf.add(tf.nn.conv2d(
                        input, 
                        W, 
                        strides=[1, stride, stride, 1], 
                        padding='SAME'), b), scale = True, training = is_training))

#pooling layer that uses max_pool
def max_pool_layer(input, kernel, stride):
    return tf.nn.max_pool(input,  
                          [1, kernel, kernel, 1], 
                          [1, stride, stride, 1], 
                          padding = 'SAME' )
#dropout
def dropout_layer(input, prob):
    """prob is a float representing the probability that each element is kept"""
    return tf.nn.dropout(input, prob)

"""# Es importante que desde ahora en adelante se ejecuten las celdas que corresponden a una red en particular, no mezclar las celdas de cada red

## Definimos la arquitectura de la red skNet

## Importante: solo ejecutar las celdas que correspondan a skNet desde aquí en adelante para no perjudicar la ejecución completa del notebook
"""

learning_rate = 0.001
num_steps = 200
batch_size = 200
dropout = 0.75

def skNet(features, n_classes=100, is_training=True):
  with tf.variable_scope("model_scope"):
    x_tensor = tf.reshape(features, shape=[-1, 128, 128, 1])

    # First block of conv layers
    conv1_1 = conv_layer(x_tensor, shape = [3, 3, 1, 64], name='conv1_1', is_training = is_training)
    conv1_2 = conv_layer(conv1_1, shape = [3, 3, 64, 64], name='conv1_2', is_training = is_training)
    conv1 = max_pool_layer(conv1_2, 3, 2)
    
    # Second block of conv layers
    conv2_1 = conv_layer(conv1, shape = [3, 3, 64, 128], name='conv2_1', is_training = is_training)
    conv2_2 = conv_layer(conv2_1, shape = [3, 3, 128, 128], name='conv2_2', is_training = is_training)
    conv2 = max_pool_layer(conv2_2, 3, 2)
    
    # Third block of conv layers
    conv3_1 = conv_layer(conv2, shape = [3, 3, 128, 128], name='conv3_1', is_training = is_training)
    conv3_2 = conv_layer(conv3_1, shape = [3, 3, 128, 128], name='conv3_2', is_training = is_training)
    conv3 = max_pool_layer(conv3_2, 3, 2)
    
    # Fourth block of conv layers
    conv4_1 = conv_layer(conv3, shape = [3, 3, 128, 256], name='conv4_1', is_training = is_training)
    conv4_2 = conv_layer(conv4_1, shape = [3, 3, 256, 256], name='conv4_2', is_training = is_training)
    conv4 = max_pool_layer(conv4_2, 3, 2)

    # First fully connected
    fc_1 = fc_layer(conv4, 1024, name='fc_1')

    # Apply Dropout
    drop = dropout_layer(fc_1, dropout)

    # Second fully connected
    fc_2 = fc_layer(drop, 100, name='fc_2', use_relu = False)
  
  return {"output": fc_2, "deep_feature": fc_1}

"""## Definimos la arquitectura del modelo skResNet

## Importante: solo ejecutar las celdas que correspondan a skResNet desde aquí en adelante para no perjudicar la ejecución completa del notebook
"""

learning_rate = 0.001
num_steps = 200
batch_size = 50
dropout = 0.75

def skResNet(features, n_classes=100, is_training=True):
  with tf.variable_scope("model_scope"):
    x_tensor = tf.reshape(features, shape=[-1, 128, 128, 1])
    
    # First block of conv layers
    conv1_1 = conv_layer(x_tensor, shape = [3, 3, 1, 64], name='conv1_1', is_training = is_training)
    conv1_2 = conv_layer(conv1_1, shape = [3, 3, 64, 64], name='conv1_2', is_training = is_training)
    maxpool_1 = max_pool_layer(conv1_2, 3, 2)
    
    # Second block of conv layers
    conv2_1 = conv_layer(maxpool_1, shape = [3, 3, 64, 64], name='conv2_1', is_training = is_training)
    conv2_2 = conv_layer(conv2_1, shape = [3, 3, 64, 64], name='conv2_2', is_training = is_training)
    residual_1 = tf.add(conv2_2, maxpool_1, name='residual_1')
    
    # Third block of conv layers
    conv3_1 = conv_layer(residual_1, shape = [3, 3, 64, 64], name='conv3_1', is_training = is_training)
    conv3_2 = conv_layer(conv3_1, shape = [3, 3, 64, 64], name='conv3_2', is_training = is_training)
    residual_2 = tf.add(conv3_2, residual_1, name='residual_2')
    
    # Fourth block of conv layers
    conv4_1 = conv_layer(residual_2, shape = [3, 3, 64, 128], name='conv4_1', is_training = is_training)
    maxpool_2 = max_pool_layer(conv4_1, 3, 2)
    
    # Fifth block of conv layers
    conv5_1 = conv_layer(maxpool_2, shape = [3, 3, 128, 128], name='conv5_1', is_training = is_training)
    conv5_2 = conv_layer(conv5_1, shape = [3, 3, 128, 128], name='conv5_2', is_training = is_training)
    residual_3 = tf.add(conv5_2, maxpool_2, name='residual_3')
    
    # Sixth block of conv layers
    conv6_1 = conv_layer(residual_3, shape = [3, 3, 128, 128], name='conv6_1', is_training = is_training)
    conv6_2 = conv_layer(conv6_1, shape = [3, 3, 128, 128], name='conv6_2', is_training = is_training)
    residual_4 = tf.add(conv6_2, residual_3, name='residual_4')
    
    # Seventh block of conv layers
    conv7_1 = conv_layer(residual_4, shape = [3, 3, 128, 256], name='conv7_1', is_training = is_training)
    maxpool_3 = max_pool_layer(conv7_1, 3, 2)
    
    # Eight block of conv layers
    conv8_1 = conv_layer(maxpool_3, shape = [3, 3, 256, 256], name='conv8_1', is_training = is_training)
    conv8_2 = conv_layer(conv8_1, shape = [3, 3, 256, 256], name='conv8_2', is_training = is_training)
    residual_5 = tf.add(conv8_2, maxpool_3, name='residual_5')
    
    # Ninth block of conv layers
    conv9_1 = conv_layer(residual_5, shape = [3, 3, 256, 256], name='conv9_1', is_training = is_training)
    conv9_2 = conv_layer(conv9_1, shape = [3, 3, 256, 256], name='conv9_2', is_training = is_training)
    residual_6 = tf.add(conv9_2, residual_5, name='residual_6')
    
    # Tenth block of conv layers
    conv10_1 = conv_layer(residual_6, shape = [3, 3, 256, 256], name='conv10_1', is_training = is_training)
    maxpool_4 = max_pool_layer(conv10_1, 3, 2)
    
    # First fully connected
    fc_1 = fc_layer(maxpool_4, 1024, name='fc_1')

    # Apply Dropout
    drop = dropout_layer(fc_1, dropout)

    # Second fully connected
    fc_2 = fc_layer(drop, 100, name='fc_2', use_relu = False)
  
  return {"output": fc_2, "deep_feature": fc_1}

"""## Parte 4:	Definición de modelos

## Definimos el modelo para la red skNet
"""

def model_fn(features, labels, mode, params):
    if mode == tf.estimator.ModeKeys.TRAIN:
        is_training = True
    else:
        is_training = False
        
    net = skNet(features, params['number_of_classes'], is_training=is_training)
    train_net = net["output"]
    
    idx_predicted_class = tf.argmax(train_net, 1)
    # If prediction mode, 
    predictions = { "idx_predicted_class": idx_predicted_class,
                    "predicted_probabilities": tf.nn.softmax(train_net, name="pred_probs"),
                    "deep_feature" : net["deep_feature"]
                   }
    if mode == tf.estimator.ModeKeys.PREDICT:
        estim_specs = tf.estimator.EstimatorSpec(mode, predictions=predictions)
    else : # TRAIN or EVAL
        idx_true_class = tf.argmax(labels, 1)            
        # Evaluate the accuracy of the model
        acc_op = tf.metrics.accuracy(labels=idx_true_class, predictions=idx_predicted_class)    
        # Define loss - e.g. cross_entropy -> mean(cross_entropy x batch)
        #onehot_labels = tf.one_hot(tf.cast(labels, tf.int32), 100)
        cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(logits = train_net, labels = labels)
        loss = tf.reduce_mean(cross_entropy)   
        update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS) # in order to allow updating in batch_normalization
        with tf.control_dependencies(update_ops) :
            optimizer = tf.train.AdamOptimizer(learning_rate= learning_rate)
            train_op = optimizer.minimize(loss, global_step=tf.train.get_global_step())        
        #EstimatorSpec 
        estim_specs = tf.estimator.EstimatorSpec(
            mode=mode,
            predictions=idx_predicted_class,
            loss=loss,
            train_op=train_op,
            eval_metric_ops={'accuracy': acc_op})    
    
    return  estim_specs

"""## Definimos el modelo para la red skResNet"""

def model_fn(features, labels, mode, params):
    if mode == tf.estimator.ModeKeys.TRAIN:
        is_training = True
    else:
        is_training = False
        
    net = skResNet(features, params['number_of_classes'], is_training=is_training)
    train_net = net["output"]
    
    idx_predicted_class = tf.argmax(train_net, 1)
    # If prediction mode, 
    predictions = { "idx_predicted_class": idx_predicted_class,
                    "predicted_probabilities": tf.nn.softmax(train_net, name="pred_probs"),
                    "deep_feature" : net["deep_feature"]
                   }
    if mode == tf.estimator.ModeKeys.PREDICT:
        estim_specs = tf.estimator.EstimatorSpec(mode, predictions=predictions)
    else : # TRAIN or EVAL
        idx_true_class = tf.argmax(labels, 1)            
        # Evaluate the accuracy of the model
        acc_op = tf.metrics.accuracy(labels=idx_true_class, predictions=idx_predicted_class)    
        # Define loss - e.g. cross_entropy -> mean(cross_entropy x batch)
        #onehot_labels = tf.one_hot(tf.cast(labels, tf.int32), 100)
        cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(logits = train_net, labels = labels)
        loss = tf.reduce_mean(cross_entropy)   
        update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS) # in order to allow updating in batch_normalization
        with tf.control_dependencies(update_ops) :
            optimizer = tf.train.AdamOptimizer(learning_rate= learning_rate)
            train_op = optimizer.minimize(loss, global_step=tf.train.get_global_step())        
        #EstimatorSpec 
        estim_specs = tf.estimator.EstimatorSpec(
            mode=mode,
            predictions=idx_predicted_class,
            loss=loss,
            train_op=train_op,
            eval_metric_ops={'accuracy': acc_op})    
    
    return  estim_specs

"""## Esta función sirve para ambos modelos sin problema"""

#define the input function
def input_fn(filename, image_shape, mean_img, batch_size, nr_batches, epochs, is_training=True):     
    dataset = tf.data.TFRecordDataset(filename)
    dataset = dataset.map(lambda x: parser_tfrecord_sk(x, image_shape[0], mean_img, 100))
    dataset = dataset.batch(batch_size)   
    if is_training:
        dataset = dataset.shuffle(nr_batches) #1000 for train, 50 for test -> dataset_size/batch_size
        dataset = dataset.repeat(epochs)            
    # for testing shuffle and repeat are not required    
    return dataset

"""## Esta celda sirve para ambos modelos sin problema"""

#metadata
#metadata
filename_mean = '/content/t2/tfrecords/mean.dat'
metadata_file = '/content/t2/tfrecords/metadata.dat'
#reading metadata    
metadata_array = np.fromfile(metadata_file, dtype=np.int)
image_shape = metadata_array[0:2]    
number_of_classes = metadata_array[2]
print(metadata_array)
#load mean
mean_img =np.fromfile(filename_mean, dtype=np.float64)
mean_img = np.reshape(mean_img, image_shape.tolist())    
#defining files for training and test
filename_train = '/content/t2/tfrecords/train.tfrecords'
filename_test = '/content/t2/tfrecords/test.tfrecords'

"""## La siguiente celda corresponde al entrenamiento de la red skNet:"""

with tf.device('/gpu:0'):
  classifier = tf.estimator.Estimator(model_fn = model_fn,
                                      params = {'learning_rate' : learning_rate,
                                                'number_of_classes' : 100,
                                                'image_shape' : image_shape,
                                                }
                                      )
  tf.logging.set_verbosity(tf.logging.INFO)
  train_spec = tf.estimator.TrainSpec(input_fn = lambda: input_fn(filename_train, 
                                                                  image_shape, 
                                                                  mean_img, 
                                                                  batch_size,
                                                                  1000,
                                                                  10,
                                                                  is_training = True),
                                     max_steps = 14000)
  eval_spec = tf.estimator.EvalSpec(input_fn = lambda: input_fn(filename_test, 
                                                                image_shape, 
                                                                mean_img, 
                                                                batch_size,
                                                                1000,
                                                                10,
                                                                is_training = False),
                                    start_delay_secs = 60,
                                    throttle_secs = 120)
  tf.estimator.train_and_evaluate(classifier, train_spec, eval_spec)

"""## La siguiente celda corresponde al entrenamiento de la red skResNet:"""

with tf.device('/gpu:0'):
  classifier = tf.estimator.Estimator(model_fn = model_fn,
                                      params = {'learning_rate' : learning_rate,
                                                'number_of_classes' : 100,
                                                'image_shape' : image_shape,
                                                }
                                      )
  tf.logging.set_verbosity(tf.logging.INFO)
  train_spec = tf.estimator.TrainSpec(input_fn = lambda: input_fn(filename_train, 
                                                                  image_shape, 
                                                                  mean_img, 
                                                                  batch_size,
                                                                  2000,
                                                                  10,
                                                                  is_training = True),
                                     max_steps = 14000)
  eval_spec = tf.estimator.EvalSpec(input_fn = lambda: input_fn(filename_test, 
                                                                image_shape, 
                                                                mean_img, 
                                                                batch_size,
                                                                1000,
                                                                10,
                                                                is_training = False),
                                    start_delay_secs = 60,
                                    throttle_secs = 120)
  tf.estimator.train_and_evaluate(classifier, train_spec, eval_spec)

"""## La siguiente celda ejecuta el test de cualquiera de las dos redes, se puede usar sin problemas:"""

with tf.device('/gpu:0'):
  result = classifier.evaluate(input_fn=lambda: input_fn(filename_test, 
                                                       image_shape, 
                                                       mean_img, 
                                                       batch_size,
                                                       50,
                                                       1,
                                                       is_training = False),
                             )
  print(result)

"""## La siguiente celda imprime el Testing Accuracy:"""

print("Testing Accuracy:", result['accuracy'])

"""## Parte 5:	Obtención de features y cálculo de mAP (Mean Average Precision)

## Obtenemos los vectores de features para las 5000 imagenes de test con el modelo skNet

Es importante tener la ruta en donde se tiene guardado el modelo y sus checkpoints, en este caso tiene una ruta en duro debido a que se estaba probando, pero para obtener los vectores se debe ingresar a mano la ruta donde se tenga el modelo entrenado en la variable "model_dir" en la función tf.estimator.Estimator
"""

with tf.device('/gpu:0'):
  classifier = tf.estimator.Estimator(model_fn = model_fn,
                                      model_dir = '/tmp/tmp8u5rcn0t/model.ckpt-10259',
                                      params = {'learning_rate' : 0,
                                                'number_of_classes' : 100,
                                                'image_shape' : image_shape
                                                })
  tf.logging.set_verbosity(tf.logging.INFO)
  
  predicted_result = list(classifier.predict(input_fn=lambda: input_fn(filename_test, 
                                                       image_shape, 
                                                       mean_img, 
                                                       batch_size,
                                                       50,
                                                       1,
                                                       is_training = False)))
  features = []
  for prediction in predicted_result:
    deep_features = prediction["deep_feature"]
    features.append(deep_features)

"""## Obtenemos los vectores de features para las 5000 imagenes de test con el modelo skResNet

Es importante tener la ruta en donde se tiene guardado el modelo y sus checkpoints, en este caso tiene una ruta en duro debido a que se estaba probando, pero para obtener los vectores se debe ingresar a mano la ruta donde se tenga el modelo entrenado en la variable "model_dir" en la función tf.estimator.Estimator
"""

with tf.device('/gpu:0'):
  classifier = tf.estimator.Estimator(model_fn = model_fn,
                                      model_dir = '/tmp/tmpu6lii0fg/model.ckpt-14000',
                                      params = {'learning_rate' : 0,
                                                'number_of_classes' : 100,
                                                'image_shape' : image_shape
                                                })
  tf.logging.set_verbosity(tf.logging.INFO)
  
  predicted_result = list(classifier.predict(input_fn=lambda: input_fn(filename_test, 
                                                       image_shape, 
                                                       mean_img, 
                                                       batch_size,
                                                       50,
                                                       1,
                                                       is_training = False)))
  features = []
  for prediction in predicted_result:
    deep_features = prediction["deep_feature"]
    features.append(deep_features)

"""La siguiente celda se encarga de calcular el mAP del modelo que se esté probando en estos momentos. Es importante que para calcular el mAP, antes se haya ejecutado todas las celdas hacia arriba debido a que se usa el vector con las clases reales antes de que se transforme en TFRecord"""

from scipy.spatial import distance
import itertools
l1 = features
l2 = test_classes
p = zip(l1, l2)
i = 0
mAP = 0
aux = []
for x, y in itertools.permutations(p, 2):
  if (i % (len(l1) - 1) == 0) and (i != 0):
    aux.sort()
    true = 0
    count = 0
    ap = 0
    for elem in aux:
      count += 1
      if var[1] == elem[1]:
        true += 1
        ap += float(true)/float(count)
    if true > 0:
      mAP += float(ap)/float(true)
    del aux[:]
  dist = distance.euclidean(x[0], y[0])
  aux.append([dist, y[1]])
  var = x
  i += 1
mAP = float(mAP)/float(len(l1))
print('El mAP obtenido es: ')
print(mAP)