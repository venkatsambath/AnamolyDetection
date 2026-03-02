# Copyright 2025 VenkatSambath
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
