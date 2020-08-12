import sys
sys.path.append("/home/jsaavedr/Research/git/tensorflow-2/")
import tensorflow as tf
from models import resnet
import datasets.data as data
import utils.configuration as conf
import utils.losses as losses
import numpy as np
import argparse
import os

if __name__ == '__main__' :        
    parser = argparse.ArgumentParser(description = "Train a simple mnist model")
    parser.add_argument("-config", type = str, help = "<str> configuration file", required = True)
    parser.add_argument("-name", type=str, help=" name of section in the configuration file", required = True)
    parser.add_argument("-gpu", type=str, help=" choose gpu device", required = False)
    pargs = parser.parse_args() 
    id_gpu = '0'
    if  pargs.gpu is not None :
        id_gpu = pargs.gpu
    os.environ["CUDA_VISIBLE_DEVICES"]=id_gpu    
    configuration_file = pargs.config
    configuration = conf.ConfigurationFile(configuration_file, pargs.name)               
    #parser_tf_record
    #/home/vision/smb-datasets/MNIST-5000/ConvNet2.0/
    tfr_train_file = os.path.join(configuration.get_data_dir(), "train.tfrecords")
    tfr_test_file = os.path.join(configuration.get_data_dir(), "test.tfrecords")
    if configuration.use_multithreads() :
        tfr_train_file=[os.path.join(configuration.get_data_dir(), "train_{}.tfrecords".format(idx)) for idx in range(configuration.get_num_threads())]
        tfr_test_file=[os.path.join(configuration.get_data_dir(), "test_{}.tfrecords".format(idx)) for idx in range(configuration.get_num_threads())]
    print(tfr_train_file)
    sys.stdout.flush()
    
    mean_file = os.path.join(configuration.get_data_dir(), "mean.dat")
    shape_file = os.path.join(configuration.get_data_dir(),"shape.dat")
    #
    input_shape =  np.fromfile(shape_file, dtype=np.int32)
    mean_image = np.fromfile(mean_file, dtype=np.float32)
    mean_image = np.reshape(mean_image, input_shape)
    
    number_of_classes = configuration.get_number_of_classes()
     
    tr_dataset = tf.data.TFRecordDataset(tfr_train_file)
    tr_dataset = tr_dataset.map(lambda x : data.parser_tfrecord(x, input_shape, mean_image, number_of_classes, 'train'));    
    tr_dataset = tr_dataset.shuffle(configuration.get_shuffle_size())        
    tr_dataset = tr_dataset.batch(batch_size = configuration.get_batch_size())    
    #tr_dataset = tr_dataset.repeat()

    
    val_dataset = tf.data.TFRecordDataset(tfr_test_file)
    val_dataset = val_dataset.map(lambda x : data.parser_tfrecord(x, input_shape, mean_image, number_of_classes, 'test'));    
    val_dataset = val_dataset.batch(batch_size = configuration.get_batch_size())
                
    
    #Defining callback for saving checkpoints
    model_checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=configuration.get_snapshot_dir() + '{epoch:03d}.h5',
        save_weights_only=True,
        monitor='val_accuracy',
        mode='max',
        save_best_only=False)
        #save_freq = configuration.get_snapshot_steps())
    #DigitModel is instantiated
    #model = DigitModel()
    #resnet 34
    model = resnet.ResNet([3,4,6,3],[64,128,256,512], configuration.get_number_of_classes(), se_factor = 0)
    #resnet_50
    #model = resnet.ResNet([3,4,6,3],[64,128,256,512], configuration.get_number_of_classes(), use_bottleneck = True)
    #build the model indicating the input shape
    model.build((1, input_shape[0], input_shape[1], input_shape[2]))
    model.summary()
    
    #model.save_weights(os.path.join(configuration.get_snapshot_dir(),'chk_sample'), save_format='h5')
    if configuration.use_checkpoint() :
        #model.load_weights(tf.train.latest_checkpoint(configuration.get_checkpoint_file()))        
        model.load_weights(configuration.get_checkpoint_file(), by_name = True, skip_mismatch = True)
    #define the training parameters
    #Here, you can test SGD vs Adam
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate = configuration.get_learning_rate()), # 'adam'     
              #loss=tf.keras.losses.CategoricalCrossentropy(from_logits=True),
              #loss= lambda y_true, y_pred : losses.crossentropy_l2_loss(y_true, y_pred, model, configuration.get_weight_decay()),
              loss= lambda y_true, y_pred : losses.crossentropy_loss(y_true, y_pred),
              metrics=['accuracy'])
     
         
    history = model.fit(tr_dataset, 
                        epochs = configuration.get_number_of_epochs(),                        
                        validation_data=val_dataset,
                        validation_steps = configuration.get_validation_steps(),
                        callbacks=[model_checkpoint_callback])
         
                         
    #save the model              
    model.save(os.path.join(configuration.get_data_dir(),"saved-model"))
