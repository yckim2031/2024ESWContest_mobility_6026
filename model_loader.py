from tensorflow.keras import layers, Model, models
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Bidirectional, Dense, BatchNormalization, Activation
from tensorflow.keras.optimizers import Adam
import argparse

def build_bi_lstm(input_shape, lstm_units):
    inputs = tf.keras.Input(shape=input_shape)
    lstm_output = layers.Bidirectional(layers.LSTM(lstm_units, return_sequences=True))(inputs)
    model = Model(inputs, lstm_output)
    return model

       
def build_siamese_encoder_lstm(input_shape, lstm_units, dense_units):
    base_network = build_bi_lstm(input_shape, lstm_units)
    input_a = tf.keras.Input(shape=input_shape) # Template
    input_b = tf.keras.Input(shape=input_shape) # Target ECG

    processed_a = base_network(input_a)
    processed_b = base_network(input_b)

    distance = layers.Lambda(lambda tensors: tf.abs(tensors[0] - tensors[1]))([processed_a, processed_b])
    x = layers.Flatten()(distance)
    x = layers.Dense(dense_units)(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Dropout(0.5)(x)

    outputs = layers.Dense(1, activation='sigmoid')(x)
    model = Model([input_a, input_b], outputs)
    return model

    

def compile_model(args):
    """
    Compile the given model with specified optimizer, loss, and metrics.
    """
    input_shape = args.input_shape
    lstm_units = args.lstm_units
    dense_units = args.dense_units
    model = build_siamese_encoder_lstm(input_shape, 25, dense_units)

    # 옵티마이저 설정
    optimizer = Adam(
        learning_rate=0.001,
    )

    metrics_list = ['accuracy', 'auc']
    mets = []
    if "accuracy" in metrics_list:
        mets.append('accuracy')
    if "auc" in metrics_list:
        mets.append(tf.keras.metrics.AUC())
    if "mean_absolute_error" in metrics_list:
        mets.append(tf.keras.metrics.MeanAbsoluteError())

    model.compile(
        loss=tf.keras.losses.BinaryCrossentropy(),
        optimizer=optimizer,
        metrics=mets
    )

    model.summary()

    return model

def str_to_tuple(arg):
    return tuple(map(int, arg.strip("()").split(',')))

def load_custom_model(model_path):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_shape', type=str_to_tuple, default="(200, 1)",
                        help='Input shape')
    parser.add_argument('--lstm_units', type=int, default=25,
                        help='Set lstm units')
    parser.add_argument('--dense_units', type=int, default=32,
                        help='Set filter numbers')
    parser.add_argument('--min_data_cnt', type=int, default=50,
                        help='Set minimum data number to include')
    args = parser.parse_args(args=[])

    model = compile_model(args)

    model.load_weights(model_path)

    return model