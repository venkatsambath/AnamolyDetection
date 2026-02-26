"""
LSTM Autoencoder model definition and sequence creation utilities.
Both functions are preserved verbatim from the Kaggle notebook.
"""
import numpy as np
import pandas as pd

from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Input, LSTM, RepeatVector, TimeDistributed, Dense
)


def create_sequences(data: pd.DataFrame, seq_length: int) -> np.ndarray:
    """
    Creates sequences from time series data for an RNN.
    Each sequence will have 'seq_length' time steps.
    Preserved verbatim from the Kaggle notebook.
    """
    xs = []
    if len(data) < seq_length:
        return np.array([])
    for i in range(len(data) - seq_length + 1):
        x = data.iloc[i:(i + seq_length)].values
        xs.append(x)
    return np.array(xs)


def build_lstm_autoencoder(input_shape: tuple, latent_dim: int) -> Model:
    """
    Builds an LSTM Autoencoder model.
    input_shape: (time_steps, features)
    Preserved verbatim from the Kaggle notebook.
    """
    n_features = input_shape[1]
    n_timesteps = input_shape[0]

    # Encoder
    encoder_inputs = Input(shape=(n_timesteps, n_features))
    encoder_lstm = LSTM(latent_dim, activation='relu', return_sequences=False)(encoder_inputs)

    # Repeat vector to match decoder input
    repeat_vector = RepeatVector(n_timesteps)(encoder_lstm)

    # Decoder
    decoder_lstm = LSTM(latent_dim, activation='relu', return_sequences=True)(repeat_vector)
    decoder_outputs = TimeDistributed(Dense(n_features))(decoder_lstm)

    model = Model(inputs=encoder_inputs, outputs=decoder_outputs)
    model.compile(optimizer='adam', loss='mse')
    return model
