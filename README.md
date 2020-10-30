# CC6204-sketches-similarity-search  
![alt text](https://github.com/rodrigo-hp/CC6204-sketches-similarity-search/blob/master/sketches-examples.jpg)  

La idea principal de este proyecto es la implementación de un sistema de clasificación y búsqueda por similitud de sketches usando redes convolucionales.  
Para esto se entrena una red neuronal convolucional clásica (skNet) y otra red ResNet (skResNet) para clasificar dibujos hechos a mano (**sketches**). Luego se evalúan ambas redes entrenadas como sistemas de recuperación por similitud usando las características aprendidas por cada modelo.  

Se utiliza como conjunto de datos de entrenamiento y de test el conjunto de datos público [*QuickDraw*](https://github.com/googlecreativelab/quickdraw-dataset), el que contiene aproximadamente 50 millones de dibujos repartidos en 345 categorías. En este proyecto solo se utilizan 100 categorías seleccionadas de forma aleatoria.  

1. **Conjunto de Entrenamiento**: Para cada una de las 100 categorías definidas se selecciona aleatoriamente 1000 dibujos, que generan un conjunto de datos con 100.000 imágenes.  
2. **Conjunto de Prueba**: Para cada una de las 100 categorías definidas se selecciona aleatoriamente 50 dibujos, que generan un conjunto de datos con 5.000 imágenes.  

## Resumen  
Primero se realiza un preprocesamiento de los datos de origen, donde se generan las imágenes a partir de esos datos para después transformar las imágenes en el formato *TFRecords* que la interfaz *Estimators* de **Tensorflow** utiliza.  

Luego, se configuran las capas y arquitecturas de las dos redes convolucionales mencionadas. Se construyen los modelos para luego ser entrenados y evaluados.  

Finalmente, usando la interfaz de **Tensorflow**, se extraen vectores de características de una imagen de prueba, los que luego son utilizados para realizar una búsqueda por similitud de una nueva imagen para recuperar aquellas similares.  

Se puede observar el desarrollo en el archivo **"Tarea2_Deep_Learning.ipynb"** en este repo.

Ejemplo de sketch perteneciente a la clase "Bus":  
![alt text](https://github.com/rodrigo-hp/CC6204-sketches-similarity-search/blob/master/bus-class.jpg)  

## Resultados skNet  
| **Configuración**                                 | **Tiempo de Entrenamiento** | **Loss** | **Accuracy en Training Set** | **Accuracy en Test Set** | **mAP** |
|:---------------------------------------------------:|:-----------------------------:|:----------:|:------------------------------:|:--------------------------:|:---------:|
| Iteraciones = 20.000, Batch Size = 100, Épocas = 10 |        6 hr y 32 min        |  1,214%  |            91,31%            |           73,3%          |   11%   |
| Iteraciones = 10.259, Batch Size = 200, Épocas = 10 |        3 hr y 45 min        |   1,27%  |             87,4%            |           74,5%          |   7,2%  |
|  Iteraciones = 7.000, Batch Size = 200, Épocas = 10 |        2 hr y 42 min        |   1,34%  |             74,3%            |           58,7%          |   4,1%  |

## Resultados skResNet  
| **Configuración**                                 | **Tiempo de Entrenamiento** | **Loss** | **Accuracy en Training Set** | **Accuracy en Test Set** | **mAP** |
|:---------------------------------------------------:|:-----------------------------:|:----------:|:------------------------------:|:--------------------------:|:---------:|
| Iteraciones = 14.000, Batch Size = 50, Épocas = 10 |        3 hr y 22 min        |  1,214%  |            81,6%            |           70,2%          |   7,5%   |
| Iteraciones = 7.000, Batch Size = 50, Épocas = 10 |        2 hr y 35 min        |   1,87%  |             67,4%            |           51,8%          |   6,9%  |  

